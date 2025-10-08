"""
Real-time Speech-to-Text with chunk-based processing.
Processes audio chunks as they arrive without waiting for complete audio.
"""

import os
import logging
import tempfile
import asyncio
import numpy as np
from typing import AsyncGenerator, Optional
import io

logger = logging.getLogger(__name__)

# Global Whisper model
whisper_model = None


def initialize_realtime_stt(model):
    """Initialize real-time STT with Whisper model."""
    global whisper_model
    whisper_model = model
    if whisper_model:
        logger.info("Real-time STT initialized with Whisper model")
    else:
        logger.warning("Real-time STT initialized but model is None")


async def transcribe_audio_chunks(
    audio_chunks: AsyncGenerator[bytes, None],
    sample_rate: int = 16000,
    chunk_duration: float = 2.0
) -> AsyncGenerator[dict, None]:
    """
    Transcribe audio chunks in real-time as they arrive.
    
    Args:
        audio_chunks: AsyncGenerator yielding audio data chunks
        sample_rate: Audio sample rate (default 16000 Hz)
        chunk_duration: Duration to accumulate before transcribing
        
    Yields:
        dict: Transcription results with partial/final status
    """
    global whisper_model
    
    if whisper_model is None:
        raise RuntimeError("Whisper model not initialized for real-time transcription")
    
    logger.info("Starting real-time chunk-based transcription")
    
    # Buffer to accumulate audio
    audio_buffer = bytearray()
    chunk_size = int(sample_rate * chunk_duration * 2)  # 2 bytes per sample (int16)
    
    full_transcription = []
    chunk_count = 0
    
    try:
        async for chunk in audio_chunks:
            audio_buffer.extend(chunk)
            
            # Process when we have enough audio
            while len(audio_buffer) >= chunk_size:
                # Extract chunk
                chunk_data = audio_buffer[:chunk_size]
                audio_buffer = audio_buffer[chunk_size:]
                
                chunk_count += 1
                logger.info(f"Processing audio chunk #{chunk_count} ({len(chunk_data)} bytes)")
                
                # Convert bytes to numpy array
                audio_array = np.frombuffer(bytes(chunk_data), dtype=np.int16)
                audio_float = audio_array.astype(np.float32) / 32768.0  # Normalize to [-1, 1]
                
                # Transcribe chunk
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: whisper_model.transcribe(
                        audio_float,
                        language='en',
                        fp16=False,
                        verbose=False
                    )
                )
                
                text = result["text"].strip()
                
                if text:
                    full_transcription.append(text)
                    combined_text = " ".join(full_transcription)
                    
                    logger.info(f"Chunk #{chunk_count} transcribed: '{text}'")
                    
                    # Yield partial result
                    yield {
                        "partial": True,
                        "text": combined_text,
                        "chunk": text,
                        "chunk_number": chunk_count,
                        "confidence": result.get("confidence", 0.8)
                    }
        
        # Process remaining audio in buffer
        if len(audio_buffer) > sample_rate:  # At least 0.5 seconds
            chunk_count += 1
            logger.info(f"Processing final chunk #{chunk_count} ({len(audio_buffer)} bytes)")
            
            audio_array = np.frombuffer(bytes(audio_buffer), dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: whisper_model.transcribe(
                    audio_float,
                    language='en',
                    fp16=False,
                    verbose=False
                )
            )
            
            text = result["text"].strip()
            if text:
                full_transcription.append(text)
        
        # Final result
        final_text = " ".join(full_transcription)
        logger.info(f"Real-time transcription complete: '{final_text}'")
        
        yield {
            "partial": False,
            "text": final_text,
            "total_chunks": chunk_count,
            "status": "complete"
        }
        
    except Exception as e:
        logger.error(f"Error in real-time transcription: {e}")
        yield {
            "partial": False,
            "text": "",
            "status": "error",
            "error": str(e)
        }


async def transcribe_stream_progressive(
    audio_data: bytes,
    sample_rate: int = 16000,
    mode: str = "local"
) -> AsyncGenerator[dict, None]:
    """
    Process audio data progressively in chunks for streaming transcription.
    
    Args:
        audio_data: Complete audio file data
        sample_rate: Sample rate (usually 16000 Hz)
        mode: "local" or "api"
        
    Yields:
        dict: Progressive transcription updates
    """
    global whisper_model
    
    if mode == "api":
        # For API mode, use the regular streaming approach
        from .streaming_stt import _transcribe_streaming_api
        async for result in _transcribe_streaming_api(audio_data):
            yield result
        return
    
    if whisper_model is None:
        raise RuntimeError("Whisper model not initialized")
    
    logger.info(f"Starting progressive transcription of {len(audio_data)} bytes")
    
    # Yield initial status
    yield {
        "partial": True,
        "text": "",
        "status": "processing",
        "progress": 0
    }
    
    try:
        # Convert audio data to numpy array
        import soundfile as sf
        from io import BytesIO
        
        # Read audio from bytes
        audio_io = BytesIO(audio_data)
        try:
            audio_array, sr = sf.read(audio_io)
        except Exception as e:
            logger.error(f"Failed to read audio with soundfile: {e}")
            # Try with pydub as fallback
            from pydub import AudioSegment
            audio_io = BytesIO(audio_data)
            audio = AudioSegment.from_file(audio_io)
            audio = audio.set_channels(1).set_frame_rate(sample_rate)
            audio_array = np.array(audio.get_array_of_samples(), dtype=np.int16).astype(np.float32) / 32768.0
            sr = sample_rate
        
        # Ensure correct dtype
        audio_array = audio_array.astype(np.float32)
        
        # Resample if needed
        if sr != sample_rate:
            import librosa
            audio_array = librosa.resample(audio_array, orig_sr=sr, target_sr=sample_rate)
            audio_array = audio_array.astype(np.float32)
        
        total_duration = len(audio_array) / sample_rate
        chunk_duration = 2.0  # 2 seconds per chunk
        chunk_samples = int(sample_rate * chunk_duration)
        
        full_text = []
        num_chunks = int(np.ceil(len(audio_array) / chunk_samples))
        
        logger.info(f"Processing {num_chunks} chunks (total duration: {total_duration:.2f}s)")
        
        for i in range(0, len(audio_array), chunk_samples):
            chunk = audio_array[i:i + chunk_samples]
            chunk_num = i // chunk_samples + 1
            progress = min(100, int((i + chunk_samples) / len(audio_array) * 100))
            
            logger.info(f"Processing chunk {chunk_num}/{num_chunks} (progress: {progress}%)")
            
            # Transcribe chunk
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: whisper_model.transcribe(
                    chunk,
                    language='en',
                    fp16=False,
                    verbose=False
                )
            )
            
            text = result["text"].strip()
            if text:
                full_text.append(text)
                combined = " ".join(full_text)
                
                # Yield progressive update
                yield {
                    "partial": True,
                    "text": combined,
                    "chunk": text,
                    "chunk_number": chunk_num,
                    "progress": progress,
                    "status": "transcribing"
                }
                
                # Small delay to make updates visible
                await asyncio.sleep(0.05)
        
        # Final result
        final_text = " ".join(full_text)
        logger.info(f"Progressive transcription complete: '{final_text}'")
        
        yield {
            "partial": False,
            "text": final_text,
            "progress": 100,
            "status": "complete"
        }
        
    except Exception as e:
        logger.error(f"Error in progressive transcription: {e}")
        yield {
            "partial": False,
            "text": "",
            "status": "error",
            "error": str(e)
        }


async def process_webm_stream(
    webm_data: bytes,
    chunk_duration: float = 2.0
) -> AsyncGenerator[dict, None]:
    """
    Process WebM audio stream in chunks.
    Converts WebM to PCM and processes in real-time.
    
    Args:
        webm_data: WebM audio data
        chunk_duration: Duration of each processing chunk
        
    Yields:
        dict: Transcription results
    """
    global whisper_model
    
    if whisper_model is None:
        raise RuntimeError("Whisper model not initialized")
    
    logger.info(f"Processing WebM stream: {len(webm_data)} bytes")
    
    try:
        # Convert WebM to WAV using pydub
        from pydub import AudioSegment
        from io import BytesIO
        
        # Load WebM
        audio_io = BytesIO(webm_data)
        audio = AudioSegment.from_file(audio_io, format="webm")
        
        # Convert to mono 16kHz
        audio = audio.set_channels(1).set_frame_rate(16000)
        
        # Get raw PCM data
        pcm_data = np.array(audio.get_array_of_samples(), dtype=np.int16)
        audio_float = pcm_data.astype(np.float32) / 32768.0
        
        # Process in chunks
        sample_rate = 16000
        chunk_samples = int(sample_rate * chunk_duration)
        full_text = []
        
        num_chunks = int(np.ceil(len(audio_float) / chunk_samples))
        logger.info(f"Processing {num_chunks} chunks from WebM")
        
        for i in range(0, len(audio_float), chunk_samples):
            chunk = audio_float[i:i + chunk_samples]
            chunk_num = i // chunk_samples + 1
            
            logger.info(f"Transcribing WebM chunk {chunk_num}/{num_chunks}")
            
            # Transcribe
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: whisper_model.transcribe(
                    chunk,
                    language='en',
                    fp16=False,
                    verbose=False
                )
            )
            
            text = result["text"].strip()
            if text:
                full_text.append(text)
                combined = " ".join(full_text)
                
                yield {
                    "partial": chunk_num < num_chunks,
                    "text": combined,
                    "chunk": text,
                    "chunk_number": chunk_num
                }
                
                await asyncio.sleep(0.05)
        
        final_text = " ".join(full_text)
        logger.info(f"WebM transcription complete: '{final_text}'")
        
        yield {
            "partial": False,
            "text": final_text,
            "status": "complete"
        }
        
    except Exception as e:
        logger.error(f"Error processing WebM stream: {e}")
        yield {
            "partial": False,
            "text": "",
            "status": "error",
            "error": str(e)
        }

