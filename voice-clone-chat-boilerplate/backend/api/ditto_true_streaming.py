"""
TRUE STREAMING: Text → Audio Chunks → Video Chunks (Real-time)
First chunk within 5 seconds!
"""
import os
import sys
import logging
import asyncio
import tempfile
import uuid
import time
import re
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)

# Add Ditto to path
DITTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'ditto-talkinghead')
sys.path.insert(0, DITTO_PATH)

router = APIRouter(prefix="/api/ditto-streaming", tags=["Ditto True Streaming"])

# Global SDK pool for parallel processing
_sdk_pool = []
_sdk_pool_lock = asyncio.Lock()
_pool_initialized = False


class TrueStreamingRequest(BaseModel):
    """Request for true end-to-end streaming"""
    text: str
    reference_image: Optional[str] = None
    reference_audio: Optional[str] = None
    emotion: Optional[int] = 4
    gaze: Optional[bool] = True
    target_chunk_duration: Optional[float] = 3.0  # Target seconds per chunk


def split_text_into_chunks(text: str, target_words_per_chunk: int = 30):
    """
    Split text into natural chunks (sentences/phrases)
    Target ~30 words per chunk = ~3 seconds of audio
    """
    # Split by sentence boundaries
    sentences = re.split(r'([.!?]+)', text)
    
    chunks = []
    current_chunk = ""
    current_word_count = 0
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        punctuation = sentences[i+1] if i+1 < len(sentences) else ""
        full_sentence = sentence + punctuation
        
        word_count = len(sentence.split())
        
        if current_word_count + word_count > target_words_per_chunk and current_chunk:
            # Save current chunk and start new one
            chunks.append(current_chunk.strip())
            current_chunk = full_sentence
            current_word_count = word_count
        else:
            # Add to current chunk
            current_chunk += " " + full_sentence
            current_word_count += word_count
    
    # Add remaining text
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


async def initialize_sdk_pool(pool_size: int = 2):
    """Initialize a pool of Ditto SDKs for parallel processing"""
    global _sdk_pool, _pool_initialized
    
    if _pool_initialized:
        return
    
    async with _sdk_pool_lock:
        if _pool_initialized:
            return
        
        try:
            logger.info(f"🔥 Initializing Ditto SDK pool (size={pool_size})...")
            from stream_pipeline_offline import StreamSDK
            
            data_root = os.path.join(DITTO_PATH, "checkpoints", "ditto_pytorch")
            cfg_pkl = os.path.join(DITTO_PATH, "checkpoints", "ditto_cfg", "v0.4_hubert_cfg_pytorch.pkl")
            
            for i in range(pool_size):
                sdk = StreamSDK(cfg_pkl, data_root)
                _sdk_pool.append(sdk)
                logger.info(f"   SDK {i+1}/{pool_size} initialized")
            
            _pool_initialized = True
            logger.info(f"✅ Ditto SDK pool ready ({pool_size} instances)")
            
        except Exception as e:
            logger.error(f"❌ SDK pool initialization failed: {e}")
            raise


async def get_sdk_from_pool():
    """Get an SDK from the pool (round-robin)"""
    if not _pool_initialized:
        await initialize_sdk_pool()
    
    # Simple round-robin
    import random
    return random.choice(_sdk_pool)


async def generate_audio_chunk(
    text_chunk: str,
    reference_audio: str,
    output_dir: str,
    chunk_id: int
) -> Optional[str]:
    """
    Generate audio for a single text chunk
    Returns path to generated audio file
    """
    try:
        from utils import text_to_speech
        
        # Generate audio
        audio_path = await text_to_speech(
            text=text_chunk,
            mode="local",
            reference_audio_path=reference_audio
        )
        
        if audio_path:
            # Move to our output dir with consistent naming
            new_path = os.path.join(output_dir, f"audio_chunk_{chunk_id:04d}.wav")
            os.rename(audio_path, new_path)
            return new_path
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Audio generation failed for chunk {chunk_id}: {e}")
        return None


async def generate_video_chunk(
    audio_path: str,
    reference_image: str,
    output_dir: str,
    chunk_id: int,
    emotion: int = 4,
    gaze: bool = True,
    is_first: bool = False
) -> Optional[dict]:
    """
    Generate video for a single audio chunk
    Returns dict with video info
    """
    try:
        import librosa
        import math
        
        # Get SDK from pool
        sdk = await get_sdk_from_pool()
        
        # Load audio
        audio, sr = librosa.load(audio_path, sr=16000)
        duration = len(audio) / sr
        num_frames = math.ceil(duration * 25)  # 25 FPS
        
        # Output path
        temp_output = os.path.join(output_dir, f"video_chunk_{chunk_id:04d}_temp")
        
        # Setup reference image (only for first chunk)
        if is_first:
            logger.info(f"[Chunk {chunk_id}] Setting up reference image...")
            setup_start = time.time()
            sdk.setup(
                reference_image,
                temp_output,
                emo=emotion,
                drive_eye=gaze,
                overall_ctrl_info={}
            )
            setup_time = time.time() - setup_start
            logger.info(f"[Chunk {chunk_id}] Reference setup: {setup_time:.2f}s")
        
        # Setup frame count
        sdk.setup_Nd(
            N_d=num_frames,
            fade_in=-1,
            fade_out=-1,
            ctrl_info={}
        )
        
        # Generate video
        gen_start = time.time()
        aud_feat = sdk.wav2feat.wav2feat(audio)
        sdk.audio2motion_queue.put(aud_feat)
        sdk.close()
        gen_time = time.time() - gen_start
        
        # Combine with audio using FFmpeg
        temp_video = temp_output + ".tmp.mp4"
        final_video = os.path.join(output_dir, f"video_chunk_{chunk_id:04d}.mp4")
        
        if os.path.exists(temp_video):
            ffmpeg_cmd = f'ffmpeg -loglevel error -y -i "{temp_video}" -i "{audio_path}" -map 0:v -map 1:a -c:v copy -c:a aac "{final_video}"'
            os.system(ffmpeg_cmd)
            
            # Cleanup temp
            os.unlink(temp_video)
            
            return {
                'chunk_id': chunk_id,
                'video_path': final_video,
                'audio_duration': duration,
                'generation_time': gen_time,
                'setup_time': setup_time if is_first else 0
            }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Video generation failed for chunk {chunk_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def true_streaming_pipeline(
    text: str,
    reference_image: str,
    reference_audio: str,
    emotion: int = 4,
    gaze: bool = True,
    target_chunk_duration: float = 3.0
) -> AsyncGenerator[dict, None]:
    """
    TRUE STREAMING: Text → Audio chunks → Video chunks
    First chunk within 5 seconds!
    """
    pipeline_start = time.time()
    output_dir = tempfile.mkdtemp(prefix="ditto_streaming_")
    
    try:
        # Initialize SDK pool
        yield {
            'type': 'initializing',
            'message': 'Initializing Ditto SDK pool...'
        }
        
        await initialize_sdk_pool(pool_size=2)
        
        # Step 1: Split text into chunks
        yield {
            'type': 'started',
            'message': 'Splitting text into chunks...'
        }
        
        # Calculate target words per chunk based on duration
        # Rough estimate: 150 words per minute = 2.5 words per second
        target_words = int(target_chunk_duration * 2.5)
        text_chunks = split_text_into_chunks(text, target_words_per_chunk=target_words)
        
        yield {
            'type': 'text_chunked',
            'total_chunks': len(text_chunks),
            'chunks': [{'id': i, 'text': chunk[:50] + '...' if len(chunk) > 50 else chunk} 
                      for i, chunk in enumerate(text_chunks)]
        }
        
        # Step 2: Process chunks in parallel (audio + video)
        chunk_tasks = []
        
        for chunk_id, text_chunk in enumerate(text_chunks):
            chunk_start = time.time()
            
            yield {
                'type': 'chunk_started',
                'chunk_id': chunk_id,
                'text': text_chunk,
                'message': f'Processing chunk {chunk_id + 1}/{len(text_chunks)}...'
            }
            
            # Generate audio for this chunk
            audio_start = time.time()
            audio_path = await generate_audio_chunk(
                text_chunk,
                reference_audio,
                output_dir,
                chunk_id
            )
            audio_time = time.time() - audio_start
            
            if not audio_path:
                yield {
                    'type': 'error',
                    'chunk_id': chunk_id,
                    'message': 'Audio generation failed'
                }
                continue
            
            yield {
                'type': 'audio_ready',
                'chunk_id': chunk_id,
                'audio_path': audio_path,
                'generation_time': audio_time
            }
            
            # Generate video for this chunk
            video_start = time.time()
            video_result = await generate_video_chunk(
                audio_path,
                reference_image,
                output_dir,
                chunk_id,
                emotion=emotion,
                gaze=gaze,
                is_first=(chunk_id == 0)  # Only setup reference for first chunk
            )
            video_time = time.time() - video_start
            
            if video_result:
                chunk_total = time.time() - chunk_start
                elapsed = time.time() - pipeline_start
                
                yield {
                    'type': 'chunk_complete',
                    'chunk_id': chunk_id,
                    'video_path': video_result['video_path'],
                    'audio_duration': video_result['audio_duration'],
                    'audio_time': audio_time,
                    'video_time': video_time,
                    'chunk_total_time': chunk_total,
                    'elapsed_time': elapsed,
                    'message': f'Chunk {chunk_id + 1} complete in {chunk_total:.2f}s'
                }
                
                # IMPORTANT: First chunk milestone
                if chunk_id == 0:
                    yield {
                        'type': 'first_chunk_milestone',
                        'time_to_first_chunk': elapsed,
                        'message': f'🎉 First chunk ready in {elapsed:.2f}s!',
                        'target_met': elapsed <= 5.0
                    }
            else:
                yield {
                    'type': 'error',
                    'chunk_id': chunk_id,
                    'message': 'Video generation failed'
                }
        
        # All chunks complete
        total_time = time.time() - pipeline_start
        
        yield {
            'type': 'complete',
            'total_chunks': len(text_chunks),
            'total_time': total_time,
            'output_dir': output_dir,
            'message': f'All {len(text_chunks)} chunks complete in {total_time:.2f}s'
        }
        
    except Exception as e:
        logger.error(f"❌ Streaming pipeline error: {e}")
        import traceback
        traceback.print_exc()
        yield {
            'type': 'error',
            'message': str(e)
        }


@router.post("/generate")
async def generate_true_streaming(request: TrueStreamingRequest):
    """
    TRUE STREAMING: Text → Audio Chunks → Video Chunks
    
    First chunk arrives within 5 seconds!
    
    This endpoint:
    1. Splits text into natural chunks (~3 seconds each)
    2. Generates audio for each chunk as it goes
    3. Generates video for each chunk immediately after audio
    4. Streams results in real-time
    
    Events:
    - initializing → SDK pool warming up
    - started → Text splitting
    - text_chunked → Text split into N chunks
    - chunk_started → Processing chunk N
    - audio_ready → Audio for chunk N ready
    - chunk_complete → Video for chunk N ready
    - first_chunk_milestone → First chunk complete (target: <5s)
    - complete → All chunks done
    """
    try:
        # Get default paths if not provided
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
        
        # Validate files
        if not os.path.exists(request.reference_image):
            raise HTTPException(status_code=404, detail="Reference image not found")
        
        if not os.path.exists(request.reference_audio):
            raise HTTPException(status_code=404, detail="Reference audio not found")
        
        # Stream generation
        async def event_generator():
            async for event in true_streaming_pipeline(
                text=request.text,
                reference_image=request.reference_image,
                reference_audio=request.reference_audio,
                emotion=request.emotion,
                gaze=request.gaze,
                target_chunk_duration=request.target_chunk_duration
            ):
                yield f"data: {json.dumps(event)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ True streaming endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Get status of the true streaming pipeline"""
    global _pool_initialized
    
    return JSONResponse({
        "status": "ready" if _pool_initialized else "not_initialized",
        "mode": "true_streaming",
        "pool_size": len(_sdk_pool),
        "message": "Ditto True Streaming API - First chunk in <5s"
    })


@router.post("/initialize")
async def initialize_pipeline():
    """Pre-warm the SDK pool"""
    try:
        await initialize_sdk_pool(pool_size=2)
        return JSONResponse({
            "status": "initialized",
            "pool_size": len(_sdk_pool),
            "message": "SDK pool ready"
        })
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

