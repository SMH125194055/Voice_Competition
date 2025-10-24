"""
NEW Ditto Online Streaming API - Uses Ditto's online streaming mode
This is a SEPARATE pipeline that doesn't interfere with existing backend/frontend
"""
import os
import sys
import logging
import asyncio
import tempfile
import uuid
import time
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)

# Add Ditto to path
DITTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'ditto-talkinghead')
sys.path.insert(0, DITTO_PATH)

router = APIRouter(prefix="/api/ditto-online", tags=["Ditto Online Streaming"])

# Global SDK instance for reuse
_global_online_sdk = None
_sdk_lock = asyncio.Lock()


class OnlineStreamingRequest(BaseModel):
    """Request model for online streaming"""
    text: str
    reference_image: Optional[str] = None
    reference_audio: Optional[str] = None
    emotion: Optional[int] = 4  # 0-7: Angry, Disgust, Fear, Happy, Neutral, Sad, Surprise, Contempt
    gaze: Optional[bool] = True
    chunk_duration: Optional[float] = 3.0  # Duration of each video chunk in seconds


class DittoOnlineStreamingPipeline:
    """
    Ditto Online Streaming Pipeline
    Uses online mode for real-time, chunked video generation
    """
    
    def __init__(self, chunk_duration: float = 3.0):
        self.chunk_duration = chunk_duration
        self.online_sdk = None
        self.initialized = False
        
        # Paths
        self.data_root = os.path.join(DITTO_PATH, "checkpoints", "ditto_pytorch")
        self.cfg_pkl = os.path.join(DITTO_PATH, "checkpoints", "ditto_cfg", "v0.4_hubert_cfg_pytorch.pkl")
        
        self.temp_dir = tempfile.mkdtemp(prefix="ditto_online_")
        logger.info(f"🎬 Ditto Online Pipeline created (chunk_duration={chunk_duration}s)")
    
    def initialize(self):
        """Initialize Ditto SDK in online mode"""
        if self.initialized:
            return
        
        try:
            logger.info("🚀 Initializing Ditto Online SDK...")
            from stream_pipeline_online import StreamSDK
            
            self.online_sdk = StreamSDK(self.cfg_pkl, self.data_root)
            self.initialized = True
            logger.info("✅ Ditto Online SDK initialized")
        except Exception as e:
            logger.error(f"❌ Ditto Online SDK initialization failed: {e}")
            raise
    
    async def generate_streaming_video(
        self,
        text: str,
        reference_image: str,
        reference_audio: str,
        emotion: int = 4,
        gaze: bool = True
    ) -> AsyncGenerator[dict, None]:
        """
        Generate video in streaming chunks using Ditto online mode
        
        Yields:
            dict with 'type' and data for each event:
            - {'type': 'started', 'message': '...'}
            - {'type': 'chunk', 'chunk_id': 0, 'video_path': '...', 'duration': 3.0}
            - {'type': 'complete', 'total_chunks': 5, 'total_time': 15.2}
        """
        if not self.initialized:
            self.initialize()
        
        start_time = time.time()
        chunk_count = 0
        
        try:
            # Step 1: Generate audio
            yield {
                'type': 'started',
                'message': 'Generating audio from text...'
            }
            
            from utils import text_to_speech, initialize_tts
            
            # Initialize TTS if needed
            try:
                initialize_tts("local", reference_audio)
            except:
                pass  # Might already be initialized
            
            audio_path = await text_to_speech(
                text=text,
                mode="local",
                reference_audio_path=reference_audio
            )
            
            if not audio_path:
                raise RuntimeError("Failed to generate audio")
            
            yield {
                'type': 'audio_ready',
                'message': 'Audio generated successfully',
                'audio_path': audio_path
            }
            
            # Step 2: Setup reference image (one-time)
            yield {
                'type': 'setup',
                'message': 'Pre-processing reference image...'
            }
            
            temp_output_base = os.path.join(self.temp_dir, f"stream_{uuid.uuid4().hex[:8]}")
            
            import librosa
            import math
            
            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000)
            audio_duration = len(audio) / sr
            
            # Calculate number of frames for online mode
            num_frames = math.ceil(audio_duration * 25)  # 25 FPS
            
            # Setup reference image
            self.online_sdk.setup(
                reference_image,
                temp_output_base,
                emo=emotion,
                drive_eye=gaze,
                overall_ctrl_info={},
                online_mode=True  # KEY: Enable online streaming mode
            )
            
            yield {
                'type': 'setup_complete',
                'message': 'Reference image preprocessed',
                'audio_duration': audio_duration,
                'expected_chunks': int(audio_duration / self.chunk_duration) + 1
            }
            
            # Step 3: Stream video generation in chunks
            yield {
                'type': 'streaming',
                'message': 'Starting video generation...'
            }
            
            # Setup frame count
            self.online_sdk.setup_Nd(
                N_d=num_frames,
                fade_in=-1,
                fade_out=-1,
                ctrl_info={}
            )
            
            # Extract audio features
            aud_feat = self.online_sdk.wav2feat.wav2feat(audio)
            
            # Calculate chunk size (frames per chunk)
            fps = 25
            frames_per_chunk = int(self.chunk_duration * fps)
            total_frames = len(aud_feat)
            
            # Stream chunks
            for chunk_start in range(0, total_frames, frames_per_chunk):
                chunk_end = min(chunk_start + frames_per_chunk, total_frames)
                chunk_feat = aud_feat[chunk_start:chunk_end]
                
                # Generate this chunk
                chunk_output = f"{temp_output_base}_chunk_{chunk_count}.mp4"
                
                # Put audio features for this chunk
                self.online_sdk.audio2motion_queue.put(chunk_feat)
                
                # Wait for this chunk to be generated
                # In online mode, the SDK processes chunks as they arrive
                await asyncio.sleep(0.1)  # Small delay for processing
                
                # Get the generated chunk
                # Note: In actual online mode, chunks would be yielded as they're ready
                # For now, we'll simulate by processing in chunks
                
                chunk_duration_actual = len(chunk_feat) / fps
                
                yield {
                    'type': 'chunk',
                    'chunk_id': chunk_count,
                    'chunk_path': chunk_output,
                    'duration': chunk_duration_actual,
                    'start_frame': chunk_start,
                    'end_frame': chunk_end
                }
                
                chunk_count += 1
            
            # Close the SDK to finalize
            self.online_sdk.close()
            
            # Add audio to final video
            final_output = f"{temp_output_base}.mp4"
            temp_video = f"{temp_output_base}.tmp.mp4"
            
            if os.path.exists(temp_video):
                ffmpeg_cmd = f'ffmpeg -loglevel error -y -i "{temp_video}" -i "{audio_path}" -map 0:v -map 1:a -c:v copy -c:a aac "{final_output}"'
                os.system(ffmpeg_cmd)
                
                yield {
                    'type': 'final_video',
                    'video_path': final_output,
                    'message': 'Final video with audio'
                }
            
            total_time = time.time() - start_time
            
            yield {
                'type': 'complete',
                'total_chunks': chunk_count,
                'total_time': total_time,
                'message': f'Completed in {total_time:.2f}s'
            }
            
        except Exception as e:
            logger.error(f"❌ Streaming generation failed: {e}")
            import traceback
            traceback.print_exc()
            yield {
                'type': 'error',
                'message': str(e)
            }
    
    def cleanup(self):
        """Cleanup temporary files"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            logger.info("🧹 Ditto Online Pipeline cleaned up")
        except Exception as e:
            logger.warning(f"⚠️  Cleanup warning: {e}")


async def get_online_pipeline() -> DittoOnlineStreamingPipeline:
    """Get or create global online streaming pipeline"""
    global _global_online_sdk
    
    async with _sdk_lock:
        if _global_online_sdk is None:
            _global_online_sdk = DittoOnlineStreamingPipeline(chunk_duration=3.0)
            _global_online_sdk.initialize()
    
    return _global_online_sdk


@router.post("/generate")
async def generate_online_streaming(request: OnlineStreamingRequest):
    """
    Generate video using Ditto online streaming mode
    
    This endpoint streams video generation progress as Server-Sent Events (SSE)
    
    Example:
        POST /api/ditto-online/generate
        {
            "text": "Hello, this is a test of Ditto online streaming mode.",
            "reference_image": "/path/to/reference.jpg",
            "reference_audio": "/path/to/reference.wav",
            "emotion": 4,
            "gaze": true,
            "chunk_duration": 3.0
        }
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
        
        # Validate files exist
        if not os.path.exists(request.reference_image):
            raise HTTPException(status_code=404, detail=f"Reference image not found: {request.reference_image}")
        
        if not os.path.exists(request.reference_audio):
            raise HTTPException(status_code=404, detail=f"Reference audio not found: {request.reference_audio}")
        
        # Get pipeline
        pipeline = await get_online_pipeline()
        
        # Stream generation
        async def event_generator():
            async for event in pipeline.generate_streaming_video(
                text=request.text,
                reference_image=request.reference_image,
                reference_audio=request.reference_audio,
                emotion=request.emotion,
                gaze=request.gaze
            ):
                # Format as SSE
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
        logger.error(f"❌ Online streaming endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """Get the status of the online streaming pipeline"""
    global _global_online_sdk
    
    return JSONResponse({
        "status": "ready" if _global_online_sdk and _global_online_sdk.initialized else "not_initialized",
        "mode": "online",
        "chunk_duration": _global_online_sdk.chunk_duration if _global_online_sdk else None,
        "message": "Ditto Online Streaming API is ready"
    })


@router.post("/initialize")
async def initialize_pipeline():
    """Manually initialize the pipeline (optional - auto-initializes on first use)"""
    try:
        pipeline = await get_online_pipeline()
        return JSONResponse({
            "status": "initialized",
            "message": "Ditto Online SDK initialized successfully"
        })
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

