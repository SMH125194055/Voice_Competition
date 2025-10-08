"""
TRUE Parallel Whisper Processing using Multiple Model Instances.
Each worker gets its own Whisper model to avoid KV cache conflicts.
"""

import asyncio
import logging
import numpy as np
from typing import List, Tuple
from io import BytesIO
import os

logger = logging.getLogger(__name__)

# Global model pool
whisper_model_pool: List = []
model_semaphore = None
NUM_WORKERS = 3  # Number of parallel Whisper models


def initialize_parallel_whisper(base_model, num_workers: int = 3):
    """
    Initialize multiple Whisper model instances for parallel processing.
    
    Args:
        base_model: The main Whisper model (used as reference)
        num_workers: Number of parallel workers (default: 3)
    """
    global whisper_model_pool, model_semaphore, NUM_WORKERS
    
    NUM_WORKERS = num_workers
    
    try:
        import whisper
        
        # Get model name from base model
        if hasattr(base_model, 'dims'):
            # Detect model size from dimensions
            if base_model.dims.n_text_state == 512:
                model_name = "base"
            elif base_model.dims.n_text_state == 384:
                model_name = "tiny"
            elif base_model.dims.n_text_state == 768:
                model_name = "small"
            elif base_model.dims.n_text_state == 1024:
                model_name = "medium"
            elif base_model.dims.n_text_state == 1280:
                model_name = "large"
            else:
                model_name = "base"  # Default
        else:
            model_name = os.getenv("WHISPER_MODEL", "base")
        
        logger.info(f"Loading {num_workers} instances of Whisper '{model_name}' model...")
        
        # Load multiple model instances
        whisper_model_pool = []
        for i in range(num_workers):
            model = whisper.load_model(model_name)
            whisper_model_pool.append(model)
            logger.info(f"Loaded Whisper model {i+1}/{num_workers}")
        
        # Create semaphore to limit concurrent access
        model_semaphore = asyncio.Semaphore(num_workers)
        
        logger.info(f"✅ Parallel Whisper initialized with {num_workers} workers")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize parallel Whisper: {e}")
        logger.warning("Falling back to single model")
        # Fallback: use base model
        if base_model:
            whisper_model_pool = [base_model]
            model_semaphore = asyncio.Semaphore(1)
        return False


async def transcribe_chunk_parallel(
    chunk_data: np.ndarray,
    chunk_index: int
) -> Tuple[int, str]:
    """
    Transcribe a single chunk using an available model from the pool.
    
    Args:
        chunk_data: Audio chunk as numpy array
        chunk_index: Index of this chunk
        
    Returns:
        Tuple of (index, transcribed_text)
    """
    global whisper_model_pool, model_semaphore
    
    if not whisper_model_pool:
        raise RuntimeError("Whisper model pool not initialized")
    
    # Wait for an available model slot
    async with model_semaphore:
        # Get model from pool (round-robin)
        model_idx = chunk_index % len(whisper_model_pool)
        model = whisper_model_pool[model_idx]
        
        # Transcribe in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: model.transcribe(
                chunk_data,
                language='en',
                fp16=False,
                verbose=False,
                beam_size=1,  # Faster
                best_of=1,
                temperature=0.0
            )
        )
        
        text = result["text"].strip()
        logger.info(f"✅ Chunk {chunk_index + 1} transcribed by model {model_idx + 1}: '{text}'")
        return (chunk_index, text)


async def transcribe_audio_parallel(
    audio_data: bytes,
    sample_rate: int = 16000,
    chunk_duration: float = 1.5
):
    """
    Transcribe audio with TRUE parallel processing using model pool.
    
    Args:
        audio_data: Complete audio data
        sample_rate: Sample rate (Hz)
        chunk_duration: Duration per chunk (seconds)
        
    Yields:
        dict: Progressive transcription updates
    """
    global whisper_model_pool
    
    if not whisper_model_pool:
        raise RuntimeError("Parallel Whisper not initialized. Call initialize_parallel_whisper() first.")
    
    # Convert audio
    try:
        from pydub import AudioSegment
        
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
    
    # Split into chunks
    chunk_samples = int(sample_rate * chunk_duration)
    chunks = []
    for i in range(0, len(audio_float), chunk_samples):
        chunk = audio_float[i:i + chunk_samples]
        if len(chunk) > sample_rate * 0.5:  # At least 0.5s
            chunks.append(chunk)
    
    total_chunks = len(chunks)
    logger.info(f"🚀 Processing {total_chunks} chunks with {len(whisper_model_pool)} parallel workers")
    
    yield {
        "partial": True,
        "text": "",
        "status": "processing",
        "total_chunks": total_chunks,
        "workers": len(whisper_model_pool)
    }
    
    # Create ALL tasks at once (TRUE parallelism!)
    tasks = [
        transcribe_chunk_parallel(chunk, i)
        for i, chunk in enumerate(chunks)
    ]
    
    # Process results as they complete
    full_text = [""] * total_chunks
    completed = 0
    
    # Use asyncio.as_completed to get results as they finish
    for coro in asyncio.as_completed(tasks):
        try:
            index, text = await coro
            full_text[index] = text
            completed += 1
            
            # Build current text (in order)
            current_text = " ".join(t for t in full_text if t)
            
            # Yield progressive update
            yield {
                "partial": completed < total_chunks,
                "text": current_text,
                "status": "transcribing",
                "progress": int(completed / total_chunks * 100),
                "completed": completed,
                "total": total_chunks
            }
            
            logger.info(f"Progress: {completed}/{total_chunks} chunks completed")
            
        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            completed += 1
    
    # Final result
    final_text = " ".join(t for t in full_text if t)
    logger.info(f"🎉 Parallel transcription complete: '{final_text}'")
    
    yield {
        "partial": False,
        "text": final_text,
        "status": "complete",
        "progress": 100
    }


async def transcribe_audio_batched(
    audio_data: bytes,
    sample_rate: int = 16000,
    chunk_duration: float = 1.5,
    batch_size: int = None
):
    """
    Transcribe audio with batched parallel processing.
    Processes chunks in batches to manage memory.
    
    Args:
        audio_data: Complete audio data
        sample_rate: Sample rate (Hz)
        chunk_duration: Duration per chunk (seconds)
        batch_size: Number of chunks per batch (default: num_workers)
        
    Yields:
        dict: Progressive transcription updates
    """
    global whisper_model_pool
    
    if not whisper_model_pool:
        raise RuntimeError("Parallel Whisper not initialized")
    
    if batch_size is None:
        batch_size = len(whisper_model_pool)
    
    # Convert audio
    try:
        from pydub import AudioSegment
        
        audio_io = BytesIO(audio_data)
        audio = AudioSegment.from_file(audio_io)
        audio = audio.set_channels(1).set_frame_rate(sample_rate)
        
        audio_array = np.array(audio.get_array_of_samples(), dtype=np.int16)
        audio_float = audio_array.astype(np.float32) / 32768.0
        
    except Exception as e:
        logger.error(f"Audio conversion error: {e}")
        yield {"partial": False, "text": "", "status": "error", "error": str(e)}
        return
    
    # Split into chunks
    chunk_samples = int(sample_rate * chunk_duration)
    chunks = []
    for i in range(0, len(audio_float), chunk_samples):
        chunk = audio_float[i:i + chunk_samples]
        if len(chunk) > sample_rate * 0.5:
            chunks.append(chunk)
    
    total_chunks = len(chunks)
    logger.info(f"📦 Processing {total_chunks} chunks in batches of {batch_size}")
    
    yield {
        "partial": True,
        "text": "",
        "status": "processing",
        "total_chunks": total_chunks
    }
    
    # Process in batches
    full_text = [""] * total_chunks
    
    for batch_start in range(0, total_chunks, batch_size):
        batch_end = min(batch_start + batch_size, total_chunks)
        batch_chunks = chunks[batch_start:batch_end]
        
        logger.info(f"Processing batch {batch_start // batch_size + 1}: chunks {batch_start+1}-{batch_end}")
        
        # Process batch in parallel
        batch_tasks = [
            transcribe_chunk_parallel(chunk, batch_start + i)
            for i, chunk in enumerate(batch_chunks)
        ]
        
        # Wait for batch to complete
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Store results
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Batch task failed: {result}")
                continue
            
            index, text = result
            full_text[index] = text
            
            # Yield progressive update
            current_text = " ".join(t for t in full_text if t)
            progress = int((batch_end) / total_chunks * 100)
            
            yield {
                "partial": batch_end < total_chunks,
                "text": current_text,
                "status": "transcribing",
                "progress": progress,
                "completed": batch_end,
                "total": total_chunks
            }
    
    # Final result
    final_text = " ".join(t for t in full_text if t)
    logger.info(f"Batched transcription complete: '{final_text}'")
    
    yield {
        "partial": False,
        "text": final_text,
        "status": "complete",
        "progress": 100
    }


def get_pool_info():
    """Get information about the model pool."""
    global whisper_model_pool, NUM_WORKERS
    
    return {
        "workers": len(whisper_model_pool),
        "target_workers": NUM_WORKERS,
        "initialized": len(whisper_model_pool) > 0
    }




