"""
OPTIMIZED STREAMING: Offline Mode + Pre-warming = <5s per chunk!

Key optimizations:
1. Pre-warm SDK at startup (saves 5s)
2. Pre-process reference images at startup (saves 5s)
3. Reuse SDK properly for all chunks (stable)
4. Use OFFLINE mode (stable, quality)
"""
import os
import sys
import logging
import asyncio
import tempfile
import uuid
import time
import re
from typing import Optional, AsyncGenerator, Dict
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)

# Add Ditto to path
DITTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'ditto-talkinghead')
sys.path.insert(0, DITTO_PATH)

router = APIRouter(prefix="/api/ditto-optimized", tags=["Ditto Optimized Streaming"])

# Global pre-warmed resources
_global_sdk = None
_preprocessed_references = {}
_initialization_lock = asyncio.Lock()
_is_initialized = False


class OptimizedStreamingRequest(BaseModel):
    """Request for optimized streaming"""
    text: str
    reference_image: Optional[str] = None
    reference_audio: Optional[str] = None
    emotion: Optional[int] = 4
    gaze: Optional[bool] = True
    target_chunk_duration: Optional[float] = 3.0


def split_text_into_chunks(text: str, target_words_per_chunk: int = 30):
    """Split text into natural chunks"""
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
            chunks.append(current_chunk.strip())
            current_chunk = full_sentence
            current_word_count = word_count
        else:
            current_chunk += " " + full_sentence
            current_word_count += word_count
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


async def initialize_global_sdk():
    """
    Initialize SDK ONCE at startup
    This eliminates the 5s initialization delay on first request
    """
    global _global_sdk, _is_initialized
    
    if _is_initialized:
        return
    
    async with _initialization_lock:
        if _is_initialized:
            return
        
        try:
            logger.info("🔥 PRE-WARMING: Initializing global Ditto SDK...")
            start_time = time.time()
            
            from stream_pipeline_offline import StreamSDK
            
            data_root = os.path.join(DITTO_PATH, "checkpoints", "ditto_pytorch")
            cfg_pkl = os.path.join(DITTO_PATH, "checkpoints", "ditto_cfg", "v0.4_hubert_cfg_pytorch.pkl")
            
            _global_sdk = StreamSDK(cfg_pkl, data_root)
            
            elapsed = time.time() - start_time
            logger.info(f"✅ PRE-WARMING: SDK initialized in {elapsed:.2f}s")
            _is_initialized = True
            
        except Exception as e:
            logger.error(f"❌ SDK initialization failed: {e}")
            raise


async def preprocess_reference_image(image_path: str, emotion: int = 4, gaze: bool = True) -> str:
    """
    Pre-process reference image ONCE
    This eliminates the 5s setup delay on first request
    """
    global _preprocessed_references
    
    cache_key = f"{image_path}_{emotion}_{gaze}"
    
    if cache_key in _preprocessed_references:
        logger.info(f"✅ Using cached reference: {cache_key}")
        return _preprocessed_references[cache_key]
    
    try:
        logger.info(f"🔥 PRE-WARMING: Preprocessing reference image...")
        start_time = time.time()
        
        # Create a dummy output path for setup
        temp_output = os.path.join(tempfile.gettempdir(), f"ref_setup_{uuid.uuid4().hex[:8]}")
        
        # Setup reference (this does the preprocessing)
        _global_sdk.setup(
            image_path,
            temp_output,
            emo=emotion,
            drive_eye=gaze,
            overall_ctrl_info={}
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✅ PRE-WARMING: Reference preprocessed in {elapsed:.2f}s")
        
        # Cache the result
        _preprocessed_references[cache_key] = temp_output
        
        return temp_output
        
    except Exception as e:
        logger.error(f"❌ Reference preprocessing failed: {e}")
        raise


async def generate_audio_chunk(
    text_chunk: str,
    reference_audio: str,
    output_dir: str,
    chunk_id: int
) -> Optional[str]:
    """Generate audio for a single text chunk"""
    try:
        from utils import text_to_speech
        
        audio_path = await text_to_speech(
            text=text_chunk,
            mode="local",
            reference_audio_path=reference_audio
        )
        
        if audio_path:
            new_path = os.path.join(output_dir, f"audio_chunk_{chunk_id:04d}.wav")
            os.rename(audio_path, new_path)
            return new_path
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Audio generation failed for chunk {chunk_id}: {e}")
        return None


async def generate_video_chunk_optimized(
    audio_path: str,
    reference_setup_path: str,  # Pre-processed reference
    output_dir: str,
    chunk_id: int
) -> Optional[dict]:
    """
    Generate video using PRE-PROCESSED reference
    This is FAST because reference is already set up!
    """
    try:
        import librosa
        import math
        
        # Load audio
        audio, sr = librosa.load(audio_path, sr=16000)
        duration = len(audio) / sr
        num_frames = math.ceil(duration * 25)
        
        # Output path
        temp_output = os.path.join(output_dir, f"video_chunk_{chunk_id:04d}_temp")
        
        # NOTE: Reference is ALREADY preprocessed! Just need to set frame count
        _global_sdk.setup_Nd(
            N_d=num_frames,
            fade_in=-1,
            fade_out=-1,
            ctrl_info={}
        )
        
        # Generate video
        gen_start = time.time()
        aud_feat = _global_sdk.wav2feat.wav2feat(audio)
        _global_sdk.audio2motion_queue.put(aud_feat)
        _global_sdk.close()
        gen_time = time.time() - gen_start
        
        # Combine with audio
        temp_video = temp_output + ".tmp.mp4"
        final_video = os.path.join(output_dir, f"video_chunk_{chunk_id:04d}.mp4")
        
        if os.path.exists(temp_video):
            ffmpeg_cmd = f'ffmpeg -loglevel error -y -i "{temp_video}" -i "{audio_path}" -map 0:v -map 1:a -c:v copy -c:a aac "{final_video}"'
            os.system(ffmpeg_cmd)
            
            os.unlink(temp_video)
            
            return {
                'chunk_id': chunk_id,
                'video_path': final_video,
                'audio_duration': duration,
                'generation_time': gen_time
            }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Video generation failed for chunk {chunk_id}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def optimized_streaming_pipeline(
    text: str,
    reference_image: str,
    reference_audio: str,
    emotion: int = 4,
    gaze: bool = True,
    target_chunk_duration: float = 3.0
) -> AsyncGenerator[dict, None]:
    """
    OPTIMIZED PIPELINE: Pre-warmed SDK + Pre-processed reference = <5s per chunk!
    """
    pipeline_start = time.time()
    output_dir = tempfile.mkdtemp(prefix="ditto_optimized_")
    
    try:
        # Step 1: Ensure SDK is initialized (should already be from startup)
        if not _is_initialized:
            yield {'type': 'initializing', 'message': 'Initializing SDK...'}
            await initialize_global_sdk()
        
        # Step 2: Ensure reference is preprocessed (cache lookup or preprocess)
        yield {'type': 'setup', 'message': 'Checking reference cache...'}
        reference_setup = await preprocess_reference_image(reference_image, emotion, gaze)
        
        # Step 3: Split text
        yield {'type': 'started', 'message': 'Splitting text into chunks...'}
        
        target_words = int(target_chunk_duration * 2.5)
        text_chunks = split_text_into_chunks(text, target_words_per_chunk=target_words)
        
        yield {
            'type': 'text_chunked',
            'total_chunks': len(text_chunks),
            'chunks': [{'id': i, 'text': chunk[:50] + '...' if len(chunk) > 50 else chunk} 
                      for i, chunk in enumerate(text_chunks)]
        }
        
        # Step 4: Process chunks
        for chunk_id, text_chunk in enumerate(text_chunks):
            chunk_start = time.time()
            
            yield {
                'type': 'chunk_started',
                'chunk_id': chunk_id,
                'text': text_chunk,
                'message': f'Processing chunk {chunk_id + 1}/{len(text_chunks)}...'
            }
            
            # Generate audio
            audio_start = time.time()
            audio_path = await generate_audio_chunk(
                text_chunk,
                reference_audio,
                output_dir,
                chunk_id
            )
            audio_time = time.time() - audio_start
            
            if not audio_path:
                yield {'type': 'error', 'chunk_id': chunk_id, 'message': 'Audio failed'}
                continue
            
            yield {
                'type': 'audio_ready',
                'chunk_id': chunk_id,
                'audio_path': audio_path,
                'generation_time': audio_time
            }
            
            # Generate video (FAST - uses pre-processed reference!)
            video_start = time.time()
            video_result = await generate_video_chunk_optimized(
                audio_path,
                reference_setup,
                output_dir,
                chunk_id
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
                
                if chunk_id == 0:
                    yield {
                        'type': 'first_chunk_milestone',
                        'time_to_first_chunk': elapsed,
                        'message': f'🎉 First chunk ready in {elapsed:.2f}s!',
                        'target_met': elapsed <= 5.0,
                        'note': 'With pre-warming at startup, this should be <5s!'
                    }
            else:
                yield {'type': 'error', 'chunk_id': chunk_id, 'message': 'Video failed'}
        
        total_time = time.time() - pipeline_start
        
        yield {
            'type': 'complete',
            'total_chunks': len(text_chunks),
            'total_time': total_time,
            'output_dir': output_dir,
            'message': f'All {len(text_chunks)} chunks complete in {total_time:.2f}s'
        }
        
    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        yield {'type': 'error', 'message': str(e)}


@router.post("/generate")
async def generate_optimized_streaming(request: OptimizedStreamingRequest):
    """
    OPTIMIZED STREAMING: <5s per chunk with pre-warming!
    
    Key optimizations:
    1. SDK pre-warmed at startup (eliminates 5s delay)
    2. Reference pre-processed (eliminates 5s delay)
    3. Offline mode for stability
    4. Clean SDK reuse
    
    Expected performance:
    - First chunk: ~5s (2s audio + 3s video)
    - Subsequent: ~5s each
    """
    try:
        # Defaults
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
        
        # Validate
        if not os.path.exists(request.reference_image):
            raise HTTPException(status_code=404, detail="Reference image not found")
        
        if not os.path.exists(request.reference_audio):
            raise HTTPException(status_code=404, detail="Reference audio not found")
        
        # Stream
        async def event_generator():
            async for event in optimized_streaming_pipeline(
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
        logger.error(f"❌ Endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Get status"""
    return JSONResponse({
        "status": "ready" if _is_initialized else "not_initialized",
        "mode": "optimized_offline",
        "preprocessed_references": len(_preprocessed_references),
        "message": "Ditto Optimized Streaming - <5s per chunk with pre-warming"
    })


@router.post("/prewarm")
async def prewarm_system():
    """
    Manually pre-warm the system
    (Should be called at startup automatically)
    """
    try:
        await initialize_global_sdk()
        
        # Pre-process default reference
        default_ref = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'Avatar', 'References', 'ref_1761131562372.jpg'
        )
        
        if os.path.exists(default_ref):
            await preprocess_reference_image(default_ref, emotion=4, gaze=True)
        
        return JSONResponse({
            "status": "pre-warmed",
            "sdk_initialized": _is_initialized,
            "references_cached": len(_preprocessed_references),
            "message": "System pre-warmed and ready for <5s responses"
        })
    except Exception as e:
        logger.error(f"❌ Pre-warming failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

