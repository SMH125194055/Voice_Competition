"""
Real-Time Streaming Avatar Generator
- Captures frames as they're generated
- Encodes in small chunks (0.5-1s each)
- Streams via WebSocket
- ZERO disk I/O
"""
import os
import sys
import logging
import asyncio
import queue
import threading
import time
import subprocess
from typing import AsyncGenerator
import numpy as np

logger = logging.getLogger(__name__)

# Add Ditto to path
DITTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'ditto-talkinghead')
sys.path.insert(0, DITTO_PATH)

from stream_pipeline_offline import StreamSDK
import librosa
import math


class RealTimeFrameCapture:
    """
    Captures frames in real-time as Ditto generates them
    Encodes small chunks for streaming
    """
    def __init__(self, fps=25, chunk_frames=12):  # 12 frames = 0.48s chunks
        self.fps = fps
        self.chunk_frames = chunk_frames
        self.frame_queue = queue.Queue(maxsize=50)
        self.encoding_active = False
        
    def __call__(self, img, fmt="bgr"):
        """Called by Ditto for each frame"""
        if fmt == "bgr":
            frame = img[..., ::-1]  # BGR to RGB
        else:
            frame = img
        
        # Put frame in queue for encoding
        self.frame_queue.put(frame.copy())
    
    def close(self):
        """Signal that no more frames will come"""
        self.frame_queue.put(None)  # Sentinel


class RealTimeStreamingAvatar:
    """
    Generate and stream avatar videos in real-time
    - First chunk ready in ~3-5 seconds
    - Continuous streaming with no gaps
    """
    def __init__(self):
        self.data_root = os.path.join(DITTO_PATH, "checkpoints", "ditto_pytorch")
        self.cfg_pkl = os.path.join(DITTO_PATH, "checkpoints", "ditto_cfg", "v0.4_hubert_cfg_pytorch.pkl")
        self.sdk = None
        self.initialized = False
        
    def initialize(self):
        """Initialize SDK"""
        if self.initialized:
            return
        
        logger.info("[RealTimeStreaming] Initializing Ditto SDK...")
        self.sdk = StreamSDK(self.cfg_pkl, self.data_root)
        self.initialized = True
        logger.info("[RealTimeStreaming] ✅ SDK ready")
    
    async def stream_video_chunks(
        self,
        audio_path: str,
        image_path: str,
        emotion: int = 4,
        gaze: bool = True
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream video chunks as they're generated
        Yields MP4 fragments that can be played immediately
        """
        if not self.initialized:
            self.initialize()
        
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000)
            duration = len(audio) / sr
            num_frames = math.ceil(len(audio) / sr * 25)
            
            logger.info(f"[RealTimeStreaming] Audio: {duration:.2f}s, {num_frames} frames")
            logger.info(f"[RealTimeStreaming] Target: {num_frames/12:.0f} chunks of ~0.5s each")
            
            # Create frame capture
            frame_capture = RealTimeFrameCapture(fps=25, chunk_frames=12)
            
            # Replace SDK writer with our capture
            import tempfile
            temp_path = os.path.join(tempfile.gettempdir(), f"stream_{int(time.time())}")
            
            # Setup SDK
            self.sdk.setup(
                image_path,
                temp_path,
                emo=emotion,
                drive_eye=gaze,
                overall_ctrl_info={}
            )
            
            # Replace writer AFTER setup
            self.sdk.writer = frame_capture
            
            # Setup frame count
            self.sdk.setup_Nd(
                N_d=num_frames,
                fade_in=-1,
                fade_out=-1,
                ctrl_info={}
            )
            
            # Start encoding thread
            chunk_queue = asyncio.Queue()
            encoding_done = asyncio.Event()
            
            async def encode_frames_async():
                """Encode frames as they arrive"""
                chunk_idx = 0
                frames_buffer = []
                
                loop = asyncio.get_event_loop()
                
                while True:
                    try:
                        # Get frame from queue (non-blocking)
                        frame = await loop.run_in_executor(
                            None,
                            lambda: frame_capture.frame_queue.get(timeout=0.5)
                        )
                        
                        if frame is None:  # Done signal
                            # Encode remaining frames
                            if frames_buffer:
                                logger.info(f"[Encoder] Final chunk {chunk_idx} ({len(frames_buffer)} frames)")
                                chunk_bytes = await self._encode_chunk(frames_buffer, audio_path, loop)
                                if chunk_bytes:
                                    await chunk_queue.put(('chunk', chunk_idx, chunk_bytes))
                            break
                        
                        frames_buffer.append(frame)
                        
                        # Encode when we have enough frames
                        if len(frames_buffer) >= frame_capture.chunk_frames:
                            logger.info(f"[Encoder] 🎬 Encoding chunk {chunk_idx} ({len(frames_buffer)} frames)")
                            start = time.time()
                            
                            chunk_bytes = await self._encode_chunk(frames_buffer, audio_path, loop)
                            
                            if chunk_bytes:
                                elapsed = time.time() - start
                                logger.info(f"[Encoder] ✅ Chunk {chunk_idx} ready: {len(chunk_bytes)/1024:.1f}KB in {elapsed:.2f}s")
                                await chunk_queue.put(('chunk', chunk_idx, chunk_bytes))
                                chunk_idx += 1
                            
                            frames_buffer = []
                    
                    except queue.Empty:
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"[Encoder] Error: {e}")
                        import traceback
                        traceback.print_exc()
                        break
                
                await chunk_queue.put(('done', None, None))
                encoding_done.set()
                logger.info("[Encoder] ✅ Complete")
            
            # Start encoder
            encoder_task = asyncio.create_task(encode_frames_async())
            
            # Start Ditto generation in background
            loop = asyncio.get_event_loop()
            
            async def generate_frames():
                """Generate frames in executor"""
                try:
                    logger.info("[Generator] Starting frame generation...")
                    aud_feat = self.sdk.wav2feat.wav2feat(audio)
                    
                    # Run in executor to avoid blocking
                    await loop.run_in_executor(None, self.sdk.audio2motion_queue.put, aud_feat)
                    await loop.run_in_executor(None, self.sdk.close)
                    
                    # Signal encoder that generation is done
                    frame_capture.close()
                    logger.info("[Generator] ✅ Frame generation complete")
                except Exception as e:
                    logger.error(f"[Generator] Error: {e}")
                    import traceback
                    traceback.print_exc()
                    frame_capture.close()
            
            generator_task = asyncio.create_task(generate_frames())
            
            # Yield chunks as they're encoded
            first_chunk = True
            start_time = time.time()
            
            while True:
                try:
                    msg_type, chunk_idx, chunk_bytes = await asyncio.wait_for(
                        chunk_queue.get(),
                        timeout=60.0
                    )
                    
                    if msg_type == 'done':
                        break
                    
                    if msg_type == 'chunk':
                        if first_chunk:
                            elapsed = time.time() - start_time
                            logger.info(f"🎉 FIRST CHUNK IN: {elapsed:.2f}s")
                            first_chunk = False
                        
                        yield chunk_bytes
                
                except asyncio.TimeoutError:
                    logger.error("[Stream] Timeout waiting for chunk")
                    break
            
            # Wait for tasks
            await generator_task
            await encoder_task
            
            logger.info("[RealTimeStreaming] ✅ Streaming complete")
        
        except Exception as e:
            logger.error(f"[RealTimeStreaming] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _encode_chunk(self, frames, audio_path, loop):
        """Encode a chunk of frames to MP4 bytes"""
        if not frames:
            return None
        
        try:
            height, width = frames[0].shape[:2]
            num_frames = len(frames)
            duration_s = num_frames / 25.0
            
            # FFmpeg command for fragmented MP4 (streamable)
            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-s', f'{width}x{height}',
                '-pix_fmt', 'rgb24',
                '-r', '25',
                '-i', '-',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-crf', '28',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+frag_keyframe+empty_moov+default_base_moof',
                '-f', 'mp4',
                'pipe:1'
            ]
            
            # Run FFmpeg in executor
            def run_ffmpeg():
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=10**8
                )
                
                # Write frames
                for frame in frames:
                    process.stdin.write(frame.tobytes())
                process.stdin.close()
                
                # Read output
                output = process.stdout.read()
                process.wait()
                
                return output
            
            output_bytes = await loop.run_in_executor(None, run_ffmpeg)
            return output_bytes
        
        except Exception as e:
            logger.error(f"[Encoder] FFmpeg error: {e}")
            return None


# Global instance
_realtime_avatar = None

def get_realtime_avatar():
    """Get or create global instance"""
    global _realtime_avatar
    if _realtime_avatar is None:
        _realtime_avatar = RealTimeStreamingAvatar()
        _realtime_avatar.initialize()
    return _realtime_avatar

