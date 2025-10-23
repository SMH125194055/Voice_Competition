"""
Ditto-TalkingHead avatar generator wrapper.
Provides same interface as SadTalker for easy switching.
"""

import os
import sys
import logging
import tempfile
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

# Add Ditto to path
DITTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'ditto-talkinghead')
sys.path.insert(0, DITTO_PATH)

class DittoAvatarGenerator:
    """
    Ditto-TalkingHead wrapper with SadTalker-compatible interface.
    Allows seamless switching between avatar models.
    """
    
    def __init__(
        self,
        checkpoint_dir: str = None,
        config_dir: str = None,
        device: str = 'cuda',
        size: int = 256,
        enhancer: Optional[str] = None
    ):
        """
        Initialize Ditto avatar generator.
        
        Args:
            checkpoint_dir: Not used (kept for SadTalker compatibility)
            config_dir: Not used (kept for SadTalker compatibility)
            device: 'cuda' or 'cpu'
            size: Not used by Ditto (output is fixed resolution)
            enhancer: Not used by Ditto (has built-in quality)
        """
        self.device = device
        self.size = size
        self.enhancer = enhancer
        self.initialized = False
        
        # Ditto configuration
        self.data_root = os.path.join(DITTO_PATH, "checkpoints", "ditto_pytorch")
        self.cfg_pkl = os.path.join(DITTO_PATH, "checkpoints", "ditto_cfg", "v0.4_hubert_cfg_pytorch.pkl")
        
        self.sdk = None
        self._image_cache = {}
        
        logger.info(f"Ditto avatar generator created (device={device})")
    
    def clear_cache(self):
        """Clear the image cache."""
        self._image_cache.clear()
        logger.info("🧹 Ditto cache cleared")
    
    def initialize(self):
        """Initialize Ditto SDK (lazy loading)."""
        if self.initialized:
            return
        
        try:
            logger.info("🎬 Initializing Ditto-TalkingHead SDK...")
            
            # Check if models exist
            if not os.path.exists(self.data_root):
                raise FileNotFoundError(
                    f"Ditto models not found at {self.data_root}\n"
                    "Please run: cd Avatar/ditto-talkinghead && source venv_ditto/bin/activate"
                )
            
            # Import and initialize SDK
            from stream_pipeline_offline import StreamSDK
            self.sdk = StreamSDK(self.cfg_pkl, self.data_root)
            
            self.initialized = True
            logger.info("✅ Ditto SDK initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Ditto: {e}")
            raise
    
    async def generate_avatar_video(
        self,
        audio_path: str,
        image_path: str,
        output_dir: str,
        still_mode: bool = True,
        preprocess: str = 'crop',
        expression_scale: float = 1.0,
        pic_size: int = None,
        enable_enhancer: bool = True,
        fast_mode: bool = True
    ) -> Optional[str]:
        """
        Generate avatar video using Ditto (SadTalker-compatible interface).
        
        Args:
            audio_path: Path to audio file
            image_path: Path to reference image
            output_dir: Output directory
            still_mode: Not used by Ditto (kept for compatibility)
            preprocess: Not used by Ditto (auto crops)
            expression_scale: Not used by Ditto
            pic_size: Not used by Ditto
            enable_enhancer: Not used by Ditto
            fast_mode: Not used by Ditto (always fast)
        
        Returns:
            Path to generated video or None on failure
        """
        if not self.initialized:
            self.initialize()
        
        try:
            # Create output path
            os.makedirs(output_dir, exist_ok=True)
            import uuid
            output_filename = f"avatar_{uuid.uuid4().hex[:8]}.mp4"
            output_path = os.path.join(output_dir, output_filename)
            temp_output = output_path.replace('.mp4', '_temp')
            
            logger.info(f"🎬 Ditto generating video: {output_filename}")
            
            # Run Ditto generation in thread pool (blocking I/O)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._run_ditto,
                audio_path,
                image_path,
                temp_output,
                output_path
            )
            
            if os.path.exists(output_path):
                logger.info(f"✅ Ditto video generated: {output_path}")
                return output_path
            else:
                logger.error("❌ Ditto video generation failed - output not found")
                return None
            
        except Exception as e:
            logger.error(f"❌ Ditto generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _run_ditto(self, audio_path, image_path, temp_output, output_path):
        """Run Ditto generation (blocking operation)."""
        import librosa
        import math
        
        try:
            # Setup SDK with source image
            self.sdk.setup(image_path, temp_output)
            
            # Load audio
            audio, sr = librosa.core.load(audio_path, sr=16000)
            num_frames = math.ceil(len(audio) / 16000 * 25)
            
            # Setup frame count
            self.sdk.setup_Nd(N_d=num_frames, fade_in=-1, fade_out=-1, ctrl_info={})
            
            # Generate motion from audio
            aud_feat = self.sdk.wav2feat.wav2feat(audio)
            self.sdk.audio2motion_queue.put(aud_feat)
            self.sdk.close()
            
            # SDK creates temp_output + ".tmp.mp4"
            actual_temp_file = temp_output + ".tmp.mp4"
            
            # Combine with audio using ffmpeg
            ffmpeg_cmd = (
                f'ffmpeg -loglevel error -y '
                f'-i "{actual_temp_file}" -i "{audio_path}" '
                f'-map 0:v -map 1:a -c:v copy -c:a aac "{output_path}"'
            )
            result = os.system(ffmpeg_cmd)
            
            if result != 0:
                raise RuntimeError("FFmpeg failed to add audio to video")
            
            # Cleanup temp file
            if os.path.exists(actual_temp_file):
                os.remove(actual_temp_file)
                
        except Exception as e:
            logger.error(f"Ditto generation error: {e}")
            raise


# Global instance (singleton pattern like SadTalker)
_ditto_generator = None

def initialize_ditto_generator(device='cuda', size=256, enhancer=None):
    """Initialize Ditto generator (matches SadTalker signature)."""
    global _ditto_generator
    try:
        _ditto_generator = DittoAvatarGenerator(device=device, size=size, enhancer=enhancer)
        _ditto_generator.initialize()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Ditto: {e}")
        return False

def get_ditto_generator():
    """Get Ditto generator instance."""
    return _ditto_generator

