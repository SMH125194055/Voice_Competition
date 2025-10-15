"""
Avatar generation service using SadTalker for near real-time video generation.
Optimized for parallel processing with voice cloning.
"""

import os
import sys
import logging
import tempfile
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
import torch

logger = logging.getLogger(__name__)

# Add SadTalker to path
SADTALKER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'SadTalker')
sys.path.insert(0, SADTALKER_PATH)

# Global avatar generator instance
_avatar_generator = None

class AvatarGenerator:
    """
    Handles avatar video generation using SadTalker.
    Optimized for speed and parallel processing.
    """
    
    def __init__(
        self,
        checkpoint_dir: str,
        config_dir: str,
        device: str = 'cuda',
        size: int = 256,  # Use 256 for faster processing
        enhancer: Optional[str] = 'gfpgan'
    ):
        """
        Initialize avatar generator.
        
        Args:
            checkpoint_dir: Path to SadTalker checkpoints
            config_dir: Path to SadTalker config
            device: 'cuda' or 'cpu'
            size: Output video size (256 or 512). 256 is faster.
            enhancer: Face enhancer ('gfpgan' or None)
        """
        self.checkpoint_dir = checkpoint_dir
        self.config_dir = config_dir
        self.device = device
        self.size = size
        self.enhancer = enhancer
        self.initialized = False
        
        # Lazy-loaded models
        self.preprocess_model = None
        self.audio_to_coeff = None
        self.animate_from_coeff = None
        self.sadtalker_paths = None
        
        logger.info(f"Avatar generator created (device={device}, size={size})")
    
    def initialize(self):
        """Initialize SadTalker models (lazy loading)."""
        if self.initialized:
            return
        
        try:
            logger.info("🎬 Initializing SadTalker models...")
            
            # Import SadTalker modules
            from src.utils.preprocess import CropAndExtract
            from src.test_audio2coeff import Audio2Coeff
            from src.facerender.animate import AnimateFromCoeff
            from src.utils.init_path import init_path
            
            # Initialize paths
            self.sadtalker_paths = init_path(
                self.checkpoint_dir,
                self.config_dir,
                self.size,
                old_version=False,
                preprocess='crop'
            )
            
            # Initialize models
            self.preprocess_model = CropAndExtract(self.sadtalker_paths, self.device)
            self.audio_to_coeff = Audio2Coeff(self.sadtalker_paths, self.device)
            self.animate_from_coeff = AnimateFromCoeff(self.sadtalker_paths, self.device)
            
            self.initialized = True
            logger.info("✅ SadTalker models initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize SadTalker: {e}")
            raise
    
    async def generate_avatar_video(
        self,
        audio_path: str,
        image_path: str,
        output_dir: str,
        still_mode: bool = True,
        preprocess: str = 'crop',
        expression_scale: float = 1.0
    ) -> Optional[str]:
        """
        Generate avatar video from audio and image.
        
        Args:
            audio_path: Path to audio file
            image_path: Path to reference image
            output_dir: Output directory for video
            still_mode: Enable still mode for better quality
            preprocess: Preprocessing mode ('crop' or 'full')
            expression_scale: Expression intensity (0.0-2.0)
            
        Returns:
            Path to generated video file, or None if failed
        """
        if not self.initialized:
            self.initialize()
        
        try:
            logger.info(f"🎬 Generating avatar video...")
            logger.info(f"  Audio: {audio_path}")
            logger.info(f"  Image: {image_path}")
            
            # Import required modules
            from src.generate_batch import get_data
            from src.generate_facerender_batch import get_facerender_data
            from time import strftime
            import shutil
            
            # Create timestamped output directory
            save_dir = os.path.join(output_dir, strftime("%Y_%m_%d_%H.%M.%S"))
            os.makedirs(save_dir, exist_ok=True)
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            video_path = await loop.run_in_executor(
                None,
                self._generate_sync,
                audio_path,
                image_path,
                save_dir,
                still_mode,
                preprocess,
                expression_scale
            )
            
            return video_path
            
        except Exception as e:
            logger.error(f"❌ Avatar generation failed: {e}")
            return None
    
    def _generate_sync(
        self,
        audio_path: str,
        image_path: str,
        save_dir: str,
        still_mode: bool,
        preprocess: str,
        expression_scale: float
    ) -> Optional[str]:
        """
        Synchronous avatar generation (runs in executor).
        """
        try:
            from src.generate_batch import get_data
            from src.generate_facerender_batch import get_facerender_data
            import shutil
            
            # Step 1: Crop image and extract 3DMM
            first_frame_dir = os.path.join(save_dir, 'first_frame_dir')
            os.makedirs(first_frame_dir, exist_ok=True)
            
            logger.info("📷 Extracting 3DMM from image...")
            first_coeff_path, crop_pic_path, crop_info = self.preprocess_model.generate(
                image_path,
                first_frame_dir,
                preprocess,
                source_image_flag=True,
                pic_size=self.size
            )
            
            if first_coeff_path is None:
                logger.error("Failed to extract coefficients from image")
                return None
            
            # Step 2: Audio to coefficients
            logger.info("🎵 Processing audio...")
            batch = get_data(first_coeff_path, audio_path, self.device, None, still=still_mode)
            coeff_path = self.audio_to_coeff.generate(batch, save_dir, pose_style=0, ref_pose_coeff_path=None)
            
            # Step 3: Generate video
            logger.info("🎥 Rendering video...")
            data = get_facerender_data(
                coeff_path,
                crop_pic_path,
                first_coeff_path,
                audio_path,
                batch_size=2,
                input_yaw_list=None,
                input_pitch_list=None,
                input_roll_list=None,
                expression_scale=expression_scale,
                still_mode=still_mode,
                preprocess=preprocess,
                size=self.size
            )
            
            result = self.animate_from_coeff.generate(
                data,
                save_dir,
                image_path,
                crop_info,
                enhancer=self.enhancer,
                background_enhancer=None,
                preprocess=preprocess,
                img_size=self.size
            )
            
            # Move to final location
            final_path = save_dir + '.mp4'
            shutil.move(result, final_path)
            logger.info(f"✅ Video generated: {final_path}")
            
            # Cleanup temp directory (keep final video)
            try:
                shutil.rmtree(save_dir)
            except:
                pass
            
            return final_path
            
        except Exception as e:
            logger.error(f"❌ Sync generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def generate_avatar_streaming(
        self,
        audio_path: str,
        image_path: str,
        output_dir: str
    ) -> Optional[str]:
        """
        Generate avatar with optimized settings for streaming (faster but lower quality).
        
        Args:
            audio_path: Path to audio file
            image_path: Path to reference image
            output_dir: Output directory
            
        Returns:
            Path to generated video
        """
        # Use faster settings for streaming
        return await self.generate_avatar_video(
            audio_path=audio_path,
            image_path=image_path,
            output_dir=output_dir,
            still_mode=True,  # Still mode is faster
            preprocess='crop',  # Crop is faster than full
            expression_scale=1.0
        )


def get_avatar_generator() -> Optional[AvatarGenerator]:
    """Get global avatar generator instance."""
    return _avatar_generator


def initialize_avatar_generator(
    device: str = 'cuda',
    size: int = 256,
    enhancer: Optional[str] = 'gfpgan'
):
    """
    Initialize global avatar generator.
    
    Args:
        device: 'cuda' or 'cpu'
        size: Output size (256 or 512)
        enhancer: Face enhancer or None
    """
    global _avatar_generator
    
    try:
        # Determine paths
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        sadtalker_dir = os.path.join(backend_dir, 'Avatar', 'SadTalker')
        checkpoint_dir = os.path.join(sadtalker_dir, 'checkpoints')
        config_dir = os.path.join(sadtalker_dir, 'src', 'config')
        
        # Check if paths exist
        if not os.path.exists(checkpoint_dir):
            logger.warning(f"⚠️ SadTalker checkpoints not found: {checkpoint_dir}")
            return False
        
        # Create generator
        _avatar_generator = AvatarGenerator(
            checkpoint_dir=checkpoint_dir,
            config_dir=config_dir,
            device=device,
            size=size,
            enhancer=enhancer
        )
        
        # Initialize models
        _avatar_generator.initialize()
        
        logger.info("✅ Avatar generator initialized")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize avatar generator: {e}")
        return False


async def generate_avatar(
    audio_path: str,
    image_path: str,
    output_dir: str,
    fast_mode: bool = True
) -> Optional[str]:
    """
    Generate avatar video (convenience function).
    
    Args:
        audio_path: Path to audio file
        image_path: Path to reference image
        output_dir: Output directory
        fast_mode: Use fast settings for near real-time
        
    Returns:
        Path to generated video or None
    """
    generator = get_avatar_generator()
    
    if generator is None:
        logger.error("Avatar generator not initialized")
        return None
    
    if fast_mode:
        return await generator.generate_avatar_streaming(audio_path, image_path, output_dir)
    else:
        return await generator.generate_avatar_video(audio_path, image_path, output_dir)


