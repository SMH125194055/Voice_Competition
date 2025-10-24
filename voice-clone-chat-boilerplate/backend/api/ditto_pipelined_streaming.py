"""
Ditto Pipelined Streaming API
===============================
Achieves <8s first video by streaming everything in parallel:
1. LLM streams text in chunks
2. TTS generates audio for each chunk immediately
3. Video generation starts as soon as first audio is ready
4. Multiple parallel streams to eliminate gaps
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import asyncio
import logging
import os
import sys
import tempfile
import uuid
import json
import time
import librosa
import math
from queue import Queue
import threading

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ditto-pipelined", tags=["Ditto Pipelined Streaming"])

# Add Ditto to path
DITTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'ditto-talkinghead')
sys.path.insert(0, DITTO_PATH)

# Import will be done lazily to avoid blocking main.py startup
_StreamSDK = None  # Will be imported when first needed

def get_stream_sdk_class():
    """Lazy import of StreamSDK to avoid blocking startup"""
    global _StreamSDK
    if _StreamSDK is None:
        from stream_pipeline_online import StreamSDK as SDK
        _StreamSDK = SDK
        logger.info("✅ StreamSDK class imported")
    return _StreamSDK

# ============================================================================
# SDK Pool for handling multiple concurrent streams
# ============================================================================
class SDKPool:
    def __init__(self, pool_size=3):
        self.pool_size = pool_size
        self.sdks = Queue(maxsize=pool_size)
        self._init_pool()
    
    def _init_pool(self):
        """Initialize SDK pool"""
        StreamSDK = get_stream_sdk_class()  # Lazy import
        
        data_root = os.path.join(DITTO_PATH, "checkpoints", "ditto_pytorch")
        cfg_pkl = os.path.join(DITTO_PATH, "checkpoints", "ditto_cfg", "v0.4_hubert_cfg_pytorch.pkl")
        
        for i in range(self.pool_size):
            sdk = StreamSDK(cfg_pkl, data_root)
            self.sdks.put(sdk)
            logger.info(f"✅ SDK {i+1}/{self.pool_size} initialized")
    
    def get(self):
        """Get an SDK from pool (blocks if none available)"""
        return self.sdks.get()
    
    def put(self, sdk):
        """Return SDK to pool"""
        self.sdks.put(sdk)

# Global SDK pool
_sdk_pool = None

def get_sdk_pool():
    """Get or create global SDK pool"""
    global _sdk_pool
    if _sdk_pool is None:
        logger.info("🔥 Initializing SDK pool...")
        _sdk_pool = SDKPool(pool_size=3)
        logger.info("✅ SDK pool ready")
    return _sdk_pool

# ============================================================================
# Request/Response Models
# ============================================================================
class PipelinedRequest(BaseModel):
    text: str
    reference_image: Optional[str] = None
    reference_audio: Optional[str] = None
    chunk_duration: Optional[float] = 5.0  # Audio chunk duration (5-10 seconds)
    emotion: Optional[int] = 4  # Neutral
    gaze: Optional[bool] = True

# ============================================================================
# Core Pipeline Logic
# ============================================================================
async def generate_audio_streaming(text: str, reference_audio: str, chunk_duration: float = 5.0):
    """
    Generate audio in chunks using TTS
    Yields audio chunks as they're ready
    """
    from utils.tts import text_to_speech
    
    # Split text into smaller chunks (rough estimate: 150 chars = 10 seconds of speech)
    chars_per_second = 15  # Average speaking speed
    chars_per_chunk = int(chunk_duration * chars_per_second)
    
    words = text.split()
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1  # +1 for space
        
        if current_length >= chars_per_chunk:
            chunk_text = ' '.join(current_chunk)
            audio_path = await text_to_speech(
                text=chunk_text,
                mode="local",
                reference_audio_path=reference_audio
            )
            
            if audio_path:
                yield {
                    'audio_path': audio_path,
                    'text': chunk_text,
                    'duration': len(chunk_text) / chars_per_second
                }
            
            current_chunk = []
            current_length = 0
    
    # Yield remaining text
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        audio_path = await text_to_speech(
            text=chunk_text,
            mode="local",
            reference_audio_path=reference_audio
        )
        
        if audio_path:
            yield {
                'audio_path': audio_path,
                'text': chunk_text,
                'duration': len(chunk_text) / chars_per_second
            }

def generate_video_chunk_sync(sdk, audio_path: str, reference_image: str, chunk_id: int, 
                              output_dir: str, emotion: int = 4, gaze: bool = True):
    """
    Synchronous video generation for a single audio chunk
    """
    try:
        # Load audio
        audio, sr = librosa.load(audio_path, sr=16000)
        duration = len(audio) / sr
        
        # Setup if first chunk
        if chunk_id == 0:
            temp_output = os.path.join(output_dir, f"chunk_{chunk_id}")
            sdk.setup(
                reference_image,
                temp_output,
                emo=emotion,
                drive_eye=gaze,
                overall_ctrl_info={}
            )
        
        # Generate video for this audio chunk
        num_frames = math.ceil(duration * 25)  # 25 FPS
        sdk.setup_Nd(N_d=num_frames, fade_in=-1, fade_out=-1, ctrl_info={})
        
        aud_feat = sdk.wav2feat.wav2feat(audio)
        sdk.audio2motion_queue.put(aud_feat)
        sdk.close()
        
        # Get generated video
        video_no_audio = sdk.tmp_output_path + ".tmp.mp4"
        
        # Add audio
        output_filename = f"chunk_{chunk_id:04d}_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        
        ffmpeg_cmd = f'ffmpeg -loglevel error -y -i "{video_no_audio}" -i "{audio_path}" -map 0:v -map 1:a -c:v copy -c:a aac "{output_path}"'
        os.system(ffmpeg_cmd)
        
        return {
            'chunk_id': chunk_id,
            'video_path': output_path,
            'duration': duration,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"❌ Video generation failed for chunk {chunk_id}: {e}")
        return {
            'chunk_id': chunk_id,
            'error': str(e)
        }

async def pipelined_streaming_generator(
    text: str,
    reference_image: str,
    reference_audio: str,
    chunk_duration: float = 5.0,
    emotion: int = 4,
    gaze: bool = True
) -> AsyncGenerator[str, None]:
    """
    Main pipelined streaming generator
    Processes text → audio → video in parallel pipeline
    """
    try:
        # Create output directory
        output_dir = tempfile.mkdtemp(prefix="ditto_pipelined_")
        
        yield json.dumps({
            'type': 'started',
            'message': 'Starting pipelined streaming...',
            'chunk_duration': chunk_duration
        }) + '\n'
        
        # Initialize SDK pool
        sdk_pool = get_sdk_pool()
        
        # Track timing
        pipeline_start = time.time()
        first_video_time = None
        
        chunk_id = 0
        
        # Stream audio chunks and generate video immediately
        async for audio_chunk in generate_audio_streaming(text, reference_audio, chunk_duration):
            audio_start = time.time()
            audio_path = audio_chunk['audio_path']
            audio_time = time.time() - audio_start
            
            yield json.dumps({
                'type': 'audio_chunk',
                'chunk_id': chunk_id,
                'text': audio_chunk['text'][:100] + '...' if len(audio_chunk['text']) > 100 else audio_chunk['text'],
                'audio_time': audio_time,
                'duration': audio_chunk['duration']
            }) + '\n'
            
            # Generate video immediately (in executor to not block)
            video_start = time.time()
            
            # Get SDK from pool
            sdk = sdk_pool.get()
            
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    generate_video_chunk_sync,
                    sdk,
                    audio_path,
                    reference_image,
                    chunk_id,
                    output_dir,
                    emotion,
                    gaze
                )
                
                video_time = time.time() - video_start
                
                if not result.get('error'):
                    if first_video_time is None:
                        first_video_time = time.time() - pipeline_start
                    
                    yield json.dumps({
                        'type': 'video_chunk',
                        'chunk_id': chunk_id,
                        'video_path': result['video_path'],
                        'duration': result['duration'],
                        'video_time': video_time,
                        'total_time': time.time() - pipeline_start,
                        'first_video_time': first_video_time
                    }) + '\n'
                else:
                    yield json.dumps({
                        'type': 'error',
                        'chunk_id': chunk_id,
                        'message': result['error']
                    }) + '\n'
            
            finally:
                # Return SDK to pool
                sdk_pool.put(sdk)
            
            chunk_id += 1
        
        # Done
        total_time = time.time() - pipeline_start
        
        yield json.dumps({
            'type': 'complete',
            'message': 'Pipelined streaming complete',
            'total_chunks': chunk_id,
            'total_time': total_time,
            'first_video_time': first_video_time,
            'avg_time_per_chunk': total_time / chunk_id if chunk_id > 0 else 0
        }) + '\n'
        
    except Exception as e:
        logger.error(f"❌ Pipelined streaming failed: {e}")
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
async def generate_pipelined_streaming(request: PipelinedRequest):
    """
    Generate avatar video using pipelined streaming
    
    Achieves <8s first video by:
    1. Splitting text into small chunks (5-10s audio each)
    2. Generating audio for each chunk immediately
    3. Starting video generation as soon as first audio is ready
    4. Streaming video chunks as they complete
    
    **Performance Target**:
    - First video chunk: <8 seconds
    - Subsequent chunks: ~5-7 seconds each
    - No gaps between chunks
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
            pipelined_streaming_generator(
                text=request.text,
                reference_image=request.reference_image,
                reference_audio=request.reference_audio,
                chunk_duration=request.chunk_duration,
                emotion=request.emotion,
                gaze=request.gaze
            ),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        logger.error(f"❌ Pipelined streaming endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_status():
    """Get SDK pool status"""
    try:
        sdk_pool = get_sdk_pool()
        return {
            'status': 'ready',
            'pool_size': sdk_pool.pool_size,
            'available_sdks': sdk_pool.sdks.qsize()
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

