"""
Streaming Avatar Video Generation API Endpoint
Supports real-time video generation with LLM response streaming
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator, List
import os
import sys
import asyncio
import logging
import json
import uuid
from pathlib import Path
import time

logger = logging.getLogger(__name__)

router = APIRouter()

# Add utils to path
BACKEND_PATH = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BACKEND_PATH)

from utils.optimized_streaming_avatar import OptimizedStreamingAvatar


class StreamingAvatarRequest(BaseModel):
    """Request for streaming avatar generation"""
    text: str
    reference_image: Optional[str] = None
    reference_audio: Optional[str] = None
    emotion: Optional[int] = 4  # Neutral
    pose: Optional[dict] = None
    gaze: Optional[bool] = True
    chunk_duration: Optional[float] = 2.0
    mode: Optional[str] = "offline"  # offline or online


class StreamingAvatarChunk(BaseModel):
    """Single chunk of generated video"""
    chunk_idx: int
    video_url: str
    duration: float
    start_time: float
    end_time: float
    is_last: bool
    generation_time: float


# Global generator instance (reuse for efficiency)
_streaming_generator = None
_generator_lock = asyncio.Lock()


async def get_streaming_generator():
    """Get or create streaming generator instance"""
    global _streaming_generator
    
    async with _generator_lock:
        if _streaming_generator is None:
            # Read settings from env
            chunk_duration = float(os.getenv('DITTO_CHUNK_DURATION', '2.0'))
            overlap = float(os.getenv('DITTO_CHUNK_OVERLAP', '0.3'))
            max_parallel = int(os.getenv('DITTO_MAX_PARALLEL_CHUNKS', '3'))
            
            _streaming_generator = OptimizedStreamingAvatar(
                chunk_duration=chunk_duration,
                overlap_duration=overlap,
                max_parallel_workers=max_parallel
            )
            
            logger.info("✅ Streaming generator initialized")
        
        return _streaming_generator


@router.post("/api/avatar/generate-streaming")
async def generate_streaming_avatar(request: StreamingAvatarRequest):
    """
    Generate avatar video in streaming mode from audio
    Returns: Stream of Server-Sent Events with video chunks
    """
    try:
        # Get generator
        generator = await get_streaming_generator()
        
        # Use provided or default reference files
        if request.reference_image:
            image_path = request.reference_image
        else:
            image_path = os.path.join(BACKEND_PATH, "Avatar/References/ref_1761131562372.jpg")
        
        if request.reference_audio:
            audio_path = request.reference_audio
        else:
            # In real system, this would be TTS output
            audio_path = os.path.join(BACKEND_PATH, "audio/reference_voices/ref_1761118578.wav")
        
        # Output directory
        session_id = str(uuid.uuid4())[:8]
        output_dir = os.path.join(BACKEND_PATH, "generated_videos", "streaming", session_id)
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"🎬 Starting streaming generation (session: {session_id})")
        
        # Stream video chunks
        async def video_chunk_stream():
            """Generate and stream video chunks as SSE"""
            try:
                chunk_count = 0
                start_time = time.time()
                
                async for chunk in generator.generate_streaming(
                    audio_path,
                    image_path,
                    output_dir,
                    emotion=request.emotion,
                    pose=request.pose or {},
                    gaze=request.gaze
                ):
                    chunk_count += 1
                    elapsed = time.time() - start_time
                    
                    # Create relative video URL
                    video_filename = os.path.basename(chunk['video_path'])
                    video_url = f"/generated_videos/streaming/{session_id}/{video_filename}"
                    
                    # Prepare chunk data
                    chunk_data = {
                        "chunk_idx": chunk['chunk_idx'],
                        "video_url": video_url,
                        "duration": chunk['duration'],
                        "start_time": chunk['start_time'],
                        "end_time": chunk['end_time'],
                        "is_last": chunk['is_last'],
                        "generation_time": chunk.get('generation_time', 0),
                        "total_elapsed": elapsed,
                        "session_id": session_id
                    }
                    
                    # Send as SSE
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                    
                    if chunk['is_last']:
                        logger.info(f"✅ Streaming complete: {chunk_count} chunks in {elapsed:.2f}s")
                        # Send completion event
                        yield f"data: {json.dumps({'event': 'complete', 'total_chunks': chunk_count, 'total_time': elapsed})}\n\n"
                
            except Exception as e:
                logger.error(f"❌ Streaming error: {e}")
                error_data = {"event": "error", "message": str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            video_chunk_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Streaming avatar generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/avatar/generate-from-llm-stream")
async def generate_from_llm_stream(request: dict):
    """
    Generate avatar video from streaming LLM response
    Pipeline: LLM Stream -> TTS -> Video Chunks
    """
    try:
        # This would integrate with your LLM streaming
        # For now, return mock stream
        
        async def llm_to_video_stream():
            """Stream video as LLM generates text"""
            # Mock: In real system, this receives LLM stream
            yield f"data: {json.dumps({'event': 'started'})}\n\n"
            
            # Simulate LLM chunks
            llm_text = request.get('text', 'Hello, this is a streaming response.')
            
            # Would integrate with your TTS and video generator
            yield f"data: {json.dumps({'event': 'text_chunk', 'text': llm_text})}\n\n"
            
            # Video chunks would stream here as they're generated
            await asyncio.sleep(1)
            
            yield f"data: {json.dumps({'event': 'complete'})}\n\n"
        
        return StreamingResponse(
            llm_to_video_stream(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"❌ LLM streaming failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/avatar/streaming-status")
async def get_streaming_status():
    """Get current streaming generator status"""
    global _streaming_generator
    
    if _streaming_generator is None:
        return {"status": "not_initialized"}
    
    return {
        "status": "ready",
        "chunk_duration": _streaming_generator.chunk_duration,
        "overlap_duration": _streaming_generator.overlap_duration,
        "max_workers": _streaming_generator.max_parallel_workers,
        "sdk_initialized": _streaming_generator.sdk_initialized
    }


@router.post("/api/avatar/clear-streaming-cache")
async def clear_streaming_cache():
    """Clear streaming generator cache"""
    global _streaming_generator
    
    if _streaming_generator:
        _streaming_generator.shutdown()
        _streaming_generator = None
        return {"status": "cleared"}
    
    return {"status": "nothing_to_clear"}

