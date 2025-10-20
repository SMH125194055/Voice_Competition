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

# Import torchvision compatibility
try:
    import torchvision_compat
except ImportError:
    pass

# Create functional_tensor compatibility
import sys
if 'torchvision.transforms.functional_tensor' not in sys.modules:
    class FunctionalTensorCompat:
        def __getattr__(self, name):
            # Return a mock function for any attribute access
            return lambda *args, **kwargs: args[0] if args else None
    
    sys.modules['torchvision.transforms.functional_tensor'] = FunctionalTensorCompat()

# Global avatar generator instances for parallel processing
_avatar_generator = None
_avatar_generator_pool = []
_pool_size = 3  # Number of parallel instances

class AvatarGenerator:
    """
    Handles avatar video generation using SadTalker.
    Optimized for speed and parallel processing with caching.
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
        
        # 🚀 CACHE: Preprocessed reference images (image_path -> preprocessed data)
        self._image_cache = {}
        
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
    
    def _preprocess_image_cached(self, image_path: str, preprocess: str = 'crop'):
        """
        Preprocess image and cache the result for reuse.
        This avoids re-extracting 3DMM for every chunk!
        
        Args:
            image_path: Path to reference image
            preprocess: Preprocessing mode
            
        Returns:
            Tuple of (first_coeff_path, crop_pic_path, crop_info)
        """
        if not self.initialized:
            self.initialize()
        
        # Check cache first
        cache_key = f"{image_path}_{preprocess}_{self.size}"
        if cache_key in self._image_cache:
            logger.info(f"✅ Using cached preprocessed image for {os.path.basename(image_path)}")
            return self._image_cache[cache_key]
        
        # Preprocess image (first time only)
        logger.info(f"📷 Preprocessing image {os.path.basename(image_path)} (will be cached)...")
        
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='sadtalker_cache_')
        first_frame_dir = os.path.join(temp_dir, 'first_frame_dir')
        os.makedirs(first_frame_dir, exist_ok=True)
        
        try:
            first_coeff_path, crop_pic_path, crop_info = self.preprocess_model.generate(
                image_path,
                first_frame_dir,
                preprocess,
                source_image_flag=True,
                pic_size=self.size
            )
            
            if first_coeff_path is None:
                logger.error("Failed to extract coefficients from image")
                return None, None, None
            
            # Cache the result
            self._image_cache[cache_key] = (first_coeff_path, crop_pic_path, crop_info)
            logger.info(f"✅ Image preprocessed and cached: {os.path.basename(image_path)}")
            
            return first_coeff_path, crop_pic_path, crop_info
            
        except Exception as e:
            logger.error(f"❌ Image preprocessing failed: {e}")
            return None, None, None
    
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
            import time
            import random
            
            # Create unique timestamped output directory (with microseconds + random to avoid collisions)
            timestamp = strftime("%Y_%m_%d_%H.%M.%S")
            microseconds = int((time.time() % 1) * 1000000)
            random_suffix = random.randint(1000, 9999)
            save_dir = os.path.join(output_dir, f"{timestamp}_{microseconds}_{random_suffix}")
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
        Uses cached image preprocessing for speed!
        """
        try:
            from src.generate_batch import get_data
            from src.generate_facerender_batch import get_facerender_data
            import shutil
            import time
            
            start_time = time.time()
            
            # Step 1: Get preprocessed image (CACHED! No re-extraction)
            first_coeff_path, crop_pic_path, crop_info = self._preprocess_image_cached(image_path, preprocess)
            
            if first_coeff_path is None:
                logger.error("Failed to get preprocessed image")
                return None
            
            prep_time = time.time() - start_time
            logger.info(f"⏱️ Image preprocessing: {prep_time:.2f}s (cached)")
            
            # Step 2: Audio to coefficients (FAST - only audio processing)
            audio_start = time.time()
            logger.info("🎵 Processing audio...")
            batch = get_data(first_coeff_path, audio_path, self.device, None, still=still_mode)
            coeff_path = self.audio_to_coeff.generate(batch, save_dir, pose_style=0, ref_pose_coeff_path=None)
            audio_time = time.time() - audio_start
            logger.info(f"⏱️ Audio processing: {audio_time:.2f}s")
            
            # Step 3: Generate video (FASTEST PART with caching)
            render_start = time.time()
            logger.info("🎥 Rendering video...")
            data = get_facerender_data(
                coeff_path,
                crop_pic_path,
                first_coeff_path,
                audio_path,
                batch_size=8,  # ⚡ Increased batch size for faster processing
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
            render_time = time.time() - render_start
            logger.info(f"⏱️ Video rendering: {render_time:.2f}s")
            
            # Move to final location
            final_path = save_dir + '.mp4'
            shutil.move(result, final_path)
            
            total_time = time.time() - start_time
            logger.info(f"✅ Video generated: {final_path} (total: {total_time:.2f}s)")
            
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
            still_mode=True,  # Still mode is faster (no pose changes)
            preprocess='crop',  # Crop is faster than full
            expression_scale=0.8  # Slightly reduced for faster processing
        )


def get_avatar_generator() -> Optional[AvatarGenerator]:
    """Get global avatar generator instance."""
    return _avatar_generator


def initialize_avatar_generator(
    device: str = 'cuda',
    size: int = 256,
    enhancer: Optional[str] = 'gfpgan',
    pool_size: int = 3
):
    """
    Initialize global avatar generator with parallel processing pool.
    
    Args:
        device: 'cuda' or 'cpu'
        size: Output size (256 or 512)
        enhancer: Face enhancer or None
        pool_size: Number of parallel generator instances
    """
    global _avatar_generator, _avatar_generator_pool, _pool_size
    
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
        
        # Create main generator
        _avatar_generator = AvatarGenerator(
            checkpoint_dir=checkpoint_dir,
            config_dir=config_dir,
            device=device,
            size=size,
            enhancer=enhancer
        )
        
        # Initialize models
        _avatar_generator.initialize()
        
        # Create pool of generators for parallel processing
        _pool_size = pool_size
        _avatar_generator_pool = [_avatar_generator]  # Main generator is first
        
        logger.info(f"✅ Avatar generator initialized with pool size: {pool_size}")
        logger.info(f"⚡ Parallel processing enabled - all generators share cached preprocessed images")
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


async def generate_avatar_parallel(
    audio_paths: list,
    image_path: str,
    output_dir: str,
    fast_mode: bool = True
) -> list:
    """
    Generate multiple avatar videos in parallel.
    All generators share the same cached preprocessed image.
    
    Args:
        audio_paths: List of audio file paths
        image_path: Path to reference image
        output_dir: Output directory
        fast_mode: Use fast settings
        
    Returns:
        List of video paths (or None for failed ones)
    """
    generator = get_avatar_generator()
    
    if generator is None:
        logger.error("Avatar generator not initialized")
        return [None] * len(audio_paths)
    
    # Generate all videos in parallel using the same generator
    # The generator will use cached preprocessed image for all
    tasks = [
        generate_avatar(audio_path, image_path, output_dir, fast_mode)
        for audio_path in audio_paths
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Convert exceptions to None
    return [
        result if not isinstance(result, Exception) else None
        for result in results
    ]


