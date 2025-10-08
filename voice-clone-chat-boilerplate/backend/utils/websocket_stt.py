"""
WebSocket-based real-time Speech-to-Text.
Processes audio chunks as they arrive in real-time.
"""

import asyncio
import logging
import numpy as np
from typing import Optional
import io
import threading

logger = logging.getLogger(__name__)

# Global Whisper model
whisper_model = None
# Thread lock for Whisper model (NOT thread-safe!)
whisper_lock = threading.Lock()


def initialize_websocket_stt(model):
    """Initialize WebSocket STT with Whisper model."""
    global whisper_model
    whisper_model = model
    if whisper_model:
        logger.info("WebSocket real-time STT initialized")
    else:
        logger.warning("WebSocket STT initialized but model is None")


class RealtimeTranscriber:
    """
    Real-time transcriber that processes audio chunks as they arrive.
    Uses a buffer to accumulate chunks and transcribes in parallel.
    """
    
    def __init__(self, sample_rate: int = 16000, chunk_duration: float = 1.0):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_samples = int(sample_rate * chunk_duration)
        self.audio_buffer = bytearray()
        self.full_transcription = []
        self.is_processing = False
        self.pending_tasks = []
        
    async def add_audio_chunk(self, audio_bytes: bytes) -> Optional[str]:
        """
        Add audio chunk and return transcription if ready.
        Processes chunks in parallel for faster results.
        
        Args:
            audio_bytes: Raw PCM audio data (int16)
            
        Returns:
            Partial transcription if chunk is ready, None otherwise
        """
        global whisper_model
        
        if whisper_model is None:
            raise RuntimeError("Whisper model not initialized")
        
        # Add to buffer
        self.audio_buffer.extend(audio_bytes)
        
        # Process if we have enough audio
        if len(self.audio_buffer) >= self.chunk_samples * 2:  # 2 bytes per sample
            # Extract chunk
            chunk_data = bytes(self.audio_buffer[:self.chunk_samples * 2])
            self.audio_buffer = self.audio_buffer[self.chunk_samples * 2:]
            
            # Process chunk in parallel (don't wait)
            task = asyncio.create_task(self._transcribe_chunk(chunk_data))
            self.pending_tasks.append(task)
            
            # Clean up completed tasks
            self.pending_tasks = [t for t in self.pending_tasks if not t.done()]
            
            # Return latest result if any task completed
            for task in self.pending_tasks:
                if task.done():
                    try:
                        result = task.result()
                        if result:
                            return result
                    except Exception as e:
                        logger.error(f"Task error: {e}")
            
        return None
    
    async def _transcribe_chunk(self, chunk_data: bytes) -> Optional[str]:
        """
        Transcribe a single chunk in parallel.
        
        Args:
            chunk_data: Raw PCM audio (int16)
            
        Returns:
            Transcribed text or None
        """
        global whisper_model
        
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(chunk_data, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            # Transcribe in executor (non-blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: whisper_model.transcribe(
                    audio_float,
                    language='en',
                    fp16=False,
                    verbose=False,
                    beam_size=1,  # Faster, less accurate
                    best_of=1,     # Faster
                    temperature=0.0  # Deterministic
                )
            )
            
            text = result["text"].strip()
            if text:
                self.full_transcription.append(text)
                logger.info(f"Chunk transcribed: '{text}'")
                return " ".join(self.full_transcription)
            
        except Exception as e:
            logger.error(f"Chunk transcription error: {e}")
        
        return None
    
    async def finalize(self) -> str:
        """
        Process any remaining audio and wait for all pending tasks.
        
        Returns:
            Final complete transcription
        """
        # Process remaining buffer
        if len(self.audio_buffer) > self.sample_rate:  # At least 0.5s
            chunk_data = bytes(self.audio_buffer)
            task = asyncio.create_task(self._transcribe_chunk(chunk_data))
            self.pending_tasks.append(task)
        
        # Wait for all tasks to complete
        if self.pending_tasks:
            await asyncio.gather(*self.pending_tasks, return_exceptions=True)
        
        final_text = " ".join(self.full_transcription)
        logger.info(f"Final transcription: '{final_text}'")
        return final_text


async def transcribe_realtime_stream(
    audio_generator,
    sample_rate: int = 16000,
    chunk_duration: float = 1.0
):
    """
    Transcribe audio stream in real-time as chunks arrive.
    
    Args:
        audio_generator: AsyncGenerator yielding audio bytes
        sample_rate: Sample rate (Hz)
        chunk_duration: Duration per chunk (seconds)
        
    Yields:
        dict: Progressive transcription updates
    """
    transcriber = RealtimeTranscriber(sample_rate, chunk_duration)
    
    yield {
        "partial": True,
        "text": "",
        "status": "started"
    }
    
    try:
        async for audio_bytes in audio_generator:
            # Add chunk (non-blocking)
            result = await transcriber.add_audio_chunk(audio_bytes)
            
            # Yield if we got a result
            if result:
                yield {
                    "partial": True,
                    "text": result,
                    "status": "transcribing"
                }
        
        # Finalize
        final_text = await transcriber.finalize()
        
        yield {
            "partial": False,
            "text": final_text,
            "status": "complete"
        }
        
    except Exception as e:
        logger.error(f"Real-time transcription error: {e}")
        yield {
            "partial": False,
            "text": "",
            "status": "error",
            "error": str(e)
        }


# For compatibility with existing code
async def transcribe_audio_stream_fast(
    audio_data: bytes,
    sample_rate: int = 16000
):
    """
    Fast transcription using smaller chunks and SEQUENTIAL processing.
    NOTE: Whisper is NOT thread-safe, so we process sequentially but optimized.
    
    Args:
        audio_data: Complete audio data
        sample_rate: Sample rate
        
    Yields:
        dict: Progressive updates
    """
    global whisper_model, whisper_lock
    
    if whisper_model is None:
        raise RuntimeError("Whisper model not initialized")
    
    # Convert audio
    try:
        from pydub import AudioSegment
        from io import BytesIO
        
        audio_io = BytesIO(audio_data)
        audio = AudioSegment.from_file(audio_io)
        audio = audio.set_channels(1).set_frame_rate(sample_rate)
        
        # Get raw PCM
        audio_array = np.array(audio.get_array_of_samples(), dtype=np.int16)
        audio_float = audio_array.astype(np.float32) / 32768.0
        
    except Exception as e:
        logger.error(f"Audio conversion error: {e}")
        yield {"partial": False, "text": "", "status": "error", "error": str(e)}
        return
    
    # Process in small chunks SEQUENTIALLY (Whisper is not thread-safe)
    chunk_duration = 1.5  # 1.5 second chunks for balance
    chunk_samples = int(sample_rate * chunk_duration)
    
    # Split into chunks
    chunks = []
    for i in range(0, len(audio_float), chunk_samples):
        chunk = audio_float[i:i + chunk_samples]
        if len(chunk) > sample_rate * 0.5:  # At least 0.5s
            chunks.append(chunk)
    
    logger.info(f"Processing {len(chunks)} chunks sequentially (Whisper not thread-safe)")
    
    yield {
        "partial": True,
        "text": "",
        "status": "processing",
        "total_chunks": len(chunks)
    }
    
    # Process chunks SEQUENTIALLY with lock
    full_text = []
    
    for i, chunk_data in enumerate(chunks):
        try:
            # Use lock to ensure thread safety
            loop = asyncio.get_event_loop()
            
            def transcribe_with_lock():
                with whisper_lock:
                    return whisper_model.transcribe(
                        chunk_data,
                        language='en',
                        fp16=False,
                        verbose=False,
                        beam_size=1,  # Faster
                        best_of=1,
                        temperature=0.0
                    )
            
            result = await loop.run_in_executor(None, transcribe_with_lock)
            text = result["text"].strip()
            
            if text:
                full_text.append(text)
                current_text = " ".join(full_text)
                
                # Yield progressive update after each chunk
                yield {
                    "partial": (i + 1) < len(chunks),
                    "text": current_text,
                    "status": "transcribing",
                    "progress": int((i + 1) / len(chunks) * 100),
                    "chunk_number": i + 1
                }
                
                logger.info(f"Chunk {i+1}/{len(chunks)} completed: '{text}'")
        
        except Exception as e:
            logger.error(f"Error transcribing chunk {i+1}: {e}")
            # Continue with other chunks
    
    # Final result
    final_text = " ".join(full_text)
    logger.info(f"Sequential transcription complete: '{final_text}'")
    
    yield {
        "partial": False,
        "text": final_text,
        "status": "complete",
        "progress": 100
    }

