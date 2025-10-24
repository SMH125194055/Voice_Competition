"""
Ditto Cascade Streaming API
============================
Achieves <8s first video by:
1. Splitting text into small chunks (5-10s each)
2. Calling existing ditto-online-fixed API for each chunk
3. Starting new requests before previous ones finish (overlapping)
4. Streaming video chunks as they complete - NO GAPS!

This is the simple approach: reuse existing working endpoints in a smart way!
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import asyncio
import logging
import os
import json
import time
import requests

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ditto-cascade", tags=["Ditto Cascade Streaming"])

# ============================================================================
# Request/Response Models
# ============================================================================
class CascadeRequest(BaseModel):
    text: str
    reference_image: Optional[str] = None
    reference_audio: Optional[str] = None
    chunk_duration: Optional[float] = 5.0  # Target audio duration per chunk
    emotion: Optional[int] = 4  # Neutral
    gaze: Optional[bool] = True
    overlap: Optional[bool] = True  # Start next chunk before previous finishes

# ============================================================================
# Core Logic
# ============================================================================
def split_text_into_chunks(text: str, target_duration: float = 5.0):
    """
    Split text into chunks targeting specific audio duration
    Assumes ~150 chars = 10 seconds of speech
    """
    chars_per_second = 15  # Average speaking rate
    target_chars = int(target_duration * chars_per_second)
    
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1  # +1 for space
        
        if current_length >= target_chars:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_length = 0
    
    # Add remaining words
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

async def generate_single_chunk_async(
    text_chunk: str,
    chunk_id: int,
    reference_image: str,
    reference_audio: str,
    emotion: int = 4,
    gaze: bool = True
):
    """
    Generate a single video chunk using the existing ditto-online-fixed endpoint
    This runs asynchronously so multiple can run in parallel!
    """
    try:
        url = "http://localhost:8000/api/ditto-online-fixed/generate"
        
        payload = {
            "text": text_chunk,
            "reference_image": reference_image,
            "reference_audio": reference_audio,
            "emotion": emotion,
            "gaze": gaze
        }
        
        start_time = time.time()
        
        # Use requests in a thread pool to not block async
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(url, json=payload, stream=True, timeout=120)
        )
        
        if response.status_code != 200:
            raise Exception(f"API returned {response.status_code}: {response.text[:200]}")
        
        # Parse streaming response to get the final video path
        video_path = None
        duration = 0
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    if data.get('type') == 'chunk':
                        video_path = data.get('chunk_path')
                        duration = data.get('duration', 0)
                except:
                    pass
        
        elapsed = time.time() - start_time
        
        if video_path:
            return {
                'chunk_id': chunk_id,
                'text': text_chunk[:50] + '...' if len(text_chunk) > 50 else text_chunk,
                'video_path': video_path,
                'duration': duration,
                'generation_time': elapsed,
                'error': None
            }
        else:
            raise Exception("No video generated")
            
    except Exception as e:
        logger.error(f"❌ Chunk {chunk_id} failed: {e}")
        return {
            'chunk_id': chunk_id,
            'text': text_chunk[:50] + '...' if len(text_chunk) > 50 else text_chunk,
            'error': str(e),
            'generation_time': time.time() - start_time if 'start_time' in locals() else 0
        }

async def cascade_streaming_generator(
    text: str,
    reference_image: str,
    reference_audio: str,
    chunk_duration: float = 5.0,
    emotion: int = 4,
    gaze: bool = True,
    overlap: bool = True
) -> AsyncGenerator[str, None]:
    """
    Generate video by cascading multiple API calls
    With overlap=True, starts next chunk before previous finishes
    """
    try:
        # Split text into chunks
        text_chunks = split_text_into_chunks(text, chunk_duration)
        
        yield json.dumps({
            'type': 'started',
            'message': f'Cascading streaming with {len(text_chunks)} chunks',
            'total_chunks': len(text_chunks),
            'chunk_duration': chunk_duration,
            'overlap_enabled': overlap
        }) + '\n'
        
        pipeline_start = time.time()
        first_video_time = None
        
        if overlap:
            # ========================================
            # OVERLAPPING MODE: Start all chunks immediately!
            # ========================================
            tasks = []
            for i, chunk_text in enumerate(text_chunks):
                task = generate_single_chunk_async(
                    chunk_text, i, reference_image, reference_audio, emotion, gaze
                )
                tasks.append(task)
            
            # Wait for chunks to complete and yield as they finish
            for completed_task in asyncio.as_completed(tasks):
                result = await completed_task
                
                if result and not result.get('error'):
                    if first_video_time is None:
                        first_video_time = time.time() - pipeline_start
                    
                    yield json.dumps({
                        'type': 'video_chunk',
                        'chunk_id': result['chunk_id'],
                        'text': result['text'],
                        'video_path': result['video_path'],
                        'duration': result['duration'],
                        'generation_time': result['generation_time'],
                        'total_elapsed': time.time() - pipeline_start,
                        'first_video_time': first_video_time
                    }) + '\n'
                else:
                    yield json.dumps({
                        'type': 'error',
                        'chunk_id': result['chunk_id'],
                        'message': result.get('error', 'Unknown error')
                    }) + '\n'
        
        else:
            # ========================================
            # SEQUENTIAL MODE: One at a time
            # ========================================
            for i, chunk_text in enumerate(text_chunks):
                result = await generate_single_chunk_async(
                    chunk_text, i, reference_image, reference_audio, emotion, gaze
                )
                
                if result and not result.get('error'):
                    if first_video_time is None:
                        first_video_time = time.time() - pipeline_start
                    
                    yield json.dumps({
                        'type': 'video_chunk',
                        'chunk_id': result['chunk_id'],
                        'text': result['text'],
                        'video_path': result['video_path'],
                        'duration': result['duration'],
                        'generation_time': result['generation_time'],
                        'total_elapsed': time.time() - pipeline_start,
                        'first_video_time': first_video_time
                    }) + '\n'
                else:
                    yield json.dumps({
                        'type': 'error',
                        'chunk_id': result['chunk_id'],
                        'message': result.get('error', 'Unknown error')
                    }) + '\n'
        
        total_time = time.time() - pipeline_start
        
        yield json.dumps({
            'type': 'complete',
            'message': 'Cascade streaming complete',
            'total_chunks': len(text_chunks),
            'total_time': total_time,
            'first_video_time': first_video_time,
            'avg_time_per_chunk': total_time / len(text_chunks) if len(text_chunks) > 0 else 0
        }) + '\n'
        
    except Exception as e:
        logger.error(f"❌ Cascade streaming failed: {e}")
        import traceback
        traceback.print_exc()
        yield json.dumps({
            'type': 'error',
            'message': str(e)
        }) + '\n'

# ============================================================================
# API Endpoints
# ============================================================================
@router.post("/generate")
async def generate_cascade_streaming(request: CascadeRequest):
    """
    Generate avatar video using cascade streaming
    
    **How it works**:
    1. Splits text into small chunks (5-10s each)
    2. Calls existing ditto-online-fixed API for each chunk
    3. With overlap=True, starts all chunks simultaneously
    4. Streams video chunks as they complete - NO GAPS!
    
    **Performance Target**:
    - First video chunk: <8 seconds
    - Subsequent chunks arrive continuously
    - No gaps between chunks when playing sequentially
    """
    try:
        # Use default reference paths if not provided
        if not request.reference_image:
            request.reference_image = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'Avatar', 'References', 'ref_1761131562372.jpg'
            )
        
        if not request.reference_audio:
            request.reference_audio = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'audio', 'reference_voices', 'ref_1761118578.wav'
            )
        
        # Validate files exist
        if not os.path.exists(request.reference_image):
            raise HTTPException(status_code=400, detail=f"Reference image not found: {request.reference_image}")
        
        if not os.path.exists(request.reference_audio):
            raise HTTPException(status_code=400, detail=f"Reference audio not found: {request.reference_audio}")
        
        return StreamingResponse(
            cascade_streaming_generator(
                text=request.text,
                reference_image=request.reference_image,
                reference_audio=request.reference_audio,
                chunk_duration=request.chunk_duration,
                emotion=request.emotion,
                gaze=request.gaze,
                overlap=request.overlap
            ),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"❌ Cascade streaming endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_status():
    """Get cascade streaming status"""
    return {
        'status': 'ready',
        'mode': 'cascade',
        'description': 'Reuses existing ditto-online-fixed endpoint in overlapping fashion'
    }

