"""
Ditto Streaming Avatar Generator
Generates video frames in-memory and streams them without disk I/O
"""
import os
import sys
import logging
import asyncio
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Add Ditto to path
DITTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'ditto-talkinghead')
sys.path.insert(0, DITTO_PATH)

from stream_pipeline_offline import StreamSDK
from core.atomic_components.frame_streamer import FrameStreamer, encode_frames_to_mp4_bytes, encode_frames_streaming
import librosa
import math


class DittoStreamingGenerator:
    """
    Zero-disk-I/O streaming video generator
    """
    def __init__(self, device='cuda', emotion=4, gaze=True):
        self.device = device
        self.emotion = emotion
        self.gaze = gaze
        self.initialized = False
        
        # Use PyTorch models
        self.data_root = os.path.join(DITTO_PATH, "checkpoints", "ditto_pytorch")
        self.cfg_pkl = os.path.join(DITTO_PATH, "checkpoints", "ditto_cfg", "v0.4_hubert_cfg_pytorch.pkl")
        
        self.sdk = None
        logger.info(f"[DittoStreaming] Initialized (device={device})")
    
    def initialize(self):
        """Initialize the SDK"""
        if self.initialized:
            return
        
        try:
            logger.info("[DittoStreaming] Loading SDK...")
            self.sdk = StreamSDK(self.cfg_pkl, self.data_root)
            self.initialized = True
            logger.info("[DittoStreaming] ✅ SDK ready")
        except Exception as e:
            logger.error(f"[DittoStreaming] ❌ Initialization failed: {e}")
            raise
    
    def generate_frames(self, audio_path: str, image_path: str) -> list:
        """
        Generate video frames in-memory (no disk I/O)
        
        Returns:
            List of numpy arrays (RGB frames)
        """
        if not self.initialized:
            self.initialize()
        
        try:
            logger.info(f"[DittoStreaming] Generating frames...")
            start_time = __import__('time').time()
            
            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000)
            num_frames = math.ceil(len(audio) / sr * 25)
            
            logger.info(f"[DittoStreaming] Audio: {len(audio)/sr:.2f}s, {num_frames} frames")
            
            # Setup SDK with dummy output path
            import tempfile
            temp_path = os.path.join(tempfile.gettempdir(), "dummy_output")
            
            self.sdk.setup(
                image_path,
                temp_path,
                emo=self.emotion,
                drive_eye=self.gaze,
                overall_ctrl_info={}
            )
            
            # NOW replace the writer with our frame streamer (after setup() creates it)
            frame_streamer = FrameStreamer(fps=25)
            self.sdk.writer = frame_streamer
            
            logger.info(f"[DittoStreaming] Replaced writer with frame streamer")
            
            # Setup frame count
            self.sdk.setup_Nd(
                N_d=num_frames,
                fade_in=-1,
                fade_out=-1,
                ctrl_info={}
            )
            
            # Generate frames
            aud_feat = self.sdk.wav2feat.wav2feat(audio)
            self.sdk.audio2motion_queue.put(aud_feat)
            self.sdk.close()
            
            # Get frames from streamer
            frames = frame_streamer.get_frames()
            
            elapsed = __import__('time').time() - start_time
            logger.info(f"[DittoStreaming] ✅ Generated {len(frames)} frames in {elapsed:.2f}s")
            
            return frames
        
        except Exception as e:
            logger.error(f"[DittoStreaming] ❌ Frame generation failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def generate_video_bytes(self, audio_path: str, image_path: str) -> bytes:
        """
        Generate complete video as bytes in-memory
        
        Returns:
            bytes: MP4 video data
        """
        frames = self.generate_frames(audio_path, image_path)
        
        logger.info(f"[DittoStreaming] Encoding {len(frames)} frames to MP4...")
        start_time = __import__('time').time()
        
        video_bytes = encode_frames_to_mp4_bytes(frames, fps=25, audio_path=audio_path)
        
        elapsed = __import__('time').time() - start_time
        logger.info(f"[DittoStreaming] ✅ Encoded to {len(video_bytes)/1024/1024:.2f}MB in {elapsed:.2f}s")
        
        return video_bytes
    
    async def generate_video_stream(
        self, 
        audio_path: str, 
        image_path: str
    ) -> AsyncGenerator[bytes, None]:
        """
        Generate video and stream it in chunks (async generator)
        
        Yields:
            bytes: Chunks of MP4 video data
        """
        # Generate frames in executor to avoid blocking
        loop = asyncio.get_event_loop()
        frames = await loop.run_in_executor(None, self.generate_frames, audio_path, image_path)
        
        logger.info(f"[DittoStreaming] Streaming {len(frames)} frames...")
        
        # Stream encoded chunks
        async for chunk in encode_frames_streaming(frames, fps=25, audio_path=audio_path):
            yield chunk
        
        logger.info(f"[DittoStreaming] ✅ Streaming complete")


# Global instance
_streaming_generator = None

def get_streaming_generator():
    """Get or create global streaming generator"""
    global _streaming_generator
    if _streaming_generator is None:
        _streaming_generator = DittoStreamingGenerator()
        _streaming_generator.initialize()
    return _streaming_generator

