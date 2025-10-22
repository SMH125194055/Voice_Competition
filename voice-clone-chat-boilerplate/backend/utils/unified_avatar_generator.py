"""
Unified Avatar Generator - Supports both SadTalker and MuseTalk
Allows switching between models with a consistent API
"""

import os
import sys
import logging
import tempfile
import asyncio
from typing import Optional, Dict, Any, Literal
from pathlib import Path
import torch

logger = logging.getLogger(__name__)

# Avatar engine types
AvatarEngine = Literal["sadtalker", "musetalk"]

# Global generator instance
_unified_generator = None


class UnifiedAvatarGenerator:
    """
    Unified interface for both SadTalker and MuseTalker avatar generation.
    Allows switching between engines while maintaining consistent API.
    """
    
    def __init__(
        self,
        engine: AvatarEngine = "sadtalker",
        device: str = 'cuda',
        size: int = 256,
        enhancer: Optional[str] = 'gfpgan'
    ):
        """
        Initialize unified avatar generator.
        
        Args:
            engine: 'sadtalker' or 'musetalk'
            device: 'cuda' or 'cpu'
            size: Output video size (256 or 512)
            enhancer: Face enhancer ('gfpgan' or None) - only for SadTalker
        """
        self.engine = engine
        self.device = device
        self.size = size
        self.enhancer = enhancer
        self.initialized = False
        
        # Engine-specific instances
        self.sadtalker_generator = None
        self.musetalk_api = None
        
        # Cache for preprocessed avatars
        self._avatar_cache = {}
        
        logger.info(f"🎭 Unified Avatar Generator created (engine={engine}, device={device})")
    
    def initialize(self):
        """Initialize the selected engine."""
        if self.initialized:
            return
        
        try:
            if self.engine == "sadtalker":
                self._initialize_sadtalker()
            elif self.engine == "musetalk":
                self._initialize_musetalk()
            else:
                raise ValueError(f"Unknown engine: {self.engine}")
            
            self.initialized = True
            logger.info(f"✅ {self.engine.upper()} engine initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize {self.engine}: {e}")
            raise
    
    def _initialize_sadtalker(self):
        """Initialize SadTalker engine."""
        from utils.avatar_generator import AvatarGenerator
        
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        sadtalker_dir = os.path.join(backend_dir, 'Avatar', 'SadTalker')
        checkpoint_dir = os.path.join(sadtalker_dir, 'checkpoints')
        config_dir = os.path.join(sadtalker_dir, 'src', 'config')
        
        if not os.path.exists(checkpoint_dir):
            raise FileNotFoundError(f"SadTalker checkpoints not found: {checkpoint_dir}")
        
        self.sadtalker_generator = AvatarGenerator(
            checkpoint_dir=checkpoint_dir,
            config_dir=config_dir,
            device=self.device,
            size=self.size,
            enhancer=self.enhancer
        )
        self.sadtalker_generator.initialize()
        
        logger.info("📊 SadTalker Pipeline:")
        logger.info("  1. Reference Image → Face Detection & Crop")
        logger.info("  2. Extract 3DMM Coefficients (CACHED)")
        logger.info("  3. Audio → Motion Coefficients")
        logger.info("  4. Render Animation")
        logger.info("  5. Face Enhancement (GFPGAN)" if self.enhancer else "  5. Skip Enhancement")
        logger.info("  6. Export Video")
    
    def _initialize_musetalk(self):
        """Initialize MuseTalk engine."""
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        musetalk_dir = os.path.join(backend_dir, 'Avatar', 'MuseTalk')
        
        # Add MuseTalk to path
        if musetalk_dir not in sys.path:
            sys.path.insert(0, musetalk_dir)
        
        from musetalk_api import MuseTalkAPI
        
        # Extract CUDA device number
        cuda_device = 0
        if 'cuda' in self.device and ':' in self.device:
            cuda_device = int(self.device.split(':')[1])
        
        self.musetalk_api = MuseTalkAPI(
            musetalk_dir=musetalk_dir,
            cuda_device=cuda_device,
            batch_size=32,
            fps=25,
            fast_mode=False  # Can be toggled for speed
        )
        
        logger.info("📊 MuseTalk Pipeline:")
        logger.info("  1. Reference Image → Face Detection & Alignment (DWPose)")
        logger.info("  2. Encode to VAE Latent Space (CACHED)")
        logger.info("  3. Audio → Whisper Embeddings")
        logger.info("  4. Cross-Attention Fusion (UNet - Single Step!)")
        logger.info("  5. Decode from Latent Space")
        logger.info("  6. Composite & Export Video (Real-time capable!)")
    
    def switch_engine(self, new_engine: AvatarEngine):
        """
        Switch to a different avatar engine.
        
        Args:
            new_engine: 'sadtalker' or 'musetalk'
        """
        if new_engine == self.engine:
            logger.info(f"Already using {new_engine}")
            return
        
        logger.info(f"🔄 Switching from {self.engine} to {new_engine}")
        self.engine = new_engine
        self.initialized = False
        self.initialize()
    
    async def generate_avatar_video(
        self,
        audio_path: str,
        image_path: str,
        output_dir: str,
        avatar_id: Optional[str] = None,
        preprocess: str = 'crop',
        expression_scale: float = 1.0,
        pic_size: int = None,
        enable_enhancer: bool = True,
        fast_mode: bool = False
    ) -> Optional[str]:
        """
        Generate avatar video using the active engine.
        
        Args:
            audio_path: Path to audio file
            image_path: Path to reference image
            output_dir: Output directory for video
            avatar_id: Unique ID for caching (auto-generated if None)
            preprocess: Preprocessing mode (SadTalker only)
            expression_scale: Expression intensity (SadTalker only)
            pic_size: Image size (256 or 512)
            enable_enhancer: Enable face enhancement (SadTalker only)
            fast_mode: Enable fast mode for MuseTalk
            
        Returns:
            Path to generated video file, or None if failed
        """
        if not self.initialized:
            self.initialize()
        
        # Auto-generate avatar_id if not provided
        if avatar_id is None:
            avatar_id = Path(image_path).stem
        
        logger.info(f"🎬 Generating video with {self.engine.upper()}")
        logger.info(f"  Engine: {self.engine}")
        logger.info(f"  Audio: {Path(audio_path).name}")
        logger.info(f"  Image: {Path(image_path).name}")
        logger.info(f"  Avatar ID: {avatar_id}")
        
        try:
            if self.engine == "sadtalker":
                return await self._generate_sadtalker(
                    audio_path, image_path, output_dir,
                    preprocess, expression_scale, pic_size, enable_enhancer
                )
            elif self.engine == "musetalk":
                return await self._generate_musetalk(
                    audio_path, image_path, output_dir, avatar_id, fast_mode
                )
            else:
                raise ValueError(f"Unknown engine: {self.engine}")
                
        except Exception as e:
            logger.error(f"❌ Avatar generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _generate_sadtalker(
        self,
        audio_path: str,
        image_path: str,
        output_dir: str,
        preprocess: str,
        expression_scale: float,
        pic_size: int,
        enable_enhancer: bool
    ) -> Optional[str]:
        """Generate video using SadTalker."""
        logger.info("🎭 Using SadTalker Pipeline:")
        logger.info("  Step 1: Preprocessing reference image...")
        logger.info("  Step 2: Extracting 3DMM coefficients (cached)...")
        logger.info("  Step 3: Processing audio to motion...")
        logger.info("  Step 4: Rendering animation...")
        logger.info("  Step 5: Applying face enhancement..." if enable_enhancer else "  Step 5: Skipping enhancement")
        
        video_path = await self.sadtalker_generator.generate_avatar_video(
            audio_path=audio_path,
            image_path=image_path,
            output_dir=output_dir,
            still_mode=True,
            preprocess=preprocess,
            expression_scale=expression_scale,
            pic_size=pic_size or self.size,
            enable_enhancer=enable_enhancer
        )
        
        return video_path
    
    async def _generate_musetalk(
        self,
        audio_path: str,
        image_path: str,
        output_dir: str,
        avatar_id: str,
        fast_mode: bool
    ) -> Optional[str]:
        """Generate video using MuseTalk."""
        logger.info("🎙️ Using MuseTalk Pipeline:")
        
        # Prepare avatar if not cached
        if avatar_id not in self._avatar_cache:
            logger.info(f"  Step 1: Preparing avatar '{avatar_id}' (face detection + VAE encoding)...")
            
            # Toggle fast mode if requested
            original_fast_mode = self.musetalk_api.fast_mode
            if fast_mode and not self.musetalk_api.fast_mode:
                self.musetalk_api.fast_mode = True
                self.musetalk_api.batch_size = 64
                self.musetalk_api.fps = 15
                logger.info("  ⚡ Fast mode activated: FPS=15, Batch=64")
            
            # Run preparation in executor
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self.musetalk_api.prepare_avatar,
                avatar_id,
                image_path
            )
            
            if not success:
                logger.error("Failed to prepare avatar")
                return None
            
            self._avatar_cache[avatar_id] = {
                'image_path': image_path,
                'prepared': True
            }
            logger.info("  ✅ Avatar prepared and cached!")
        else:
            logger.info(f"  Step 1: Using cached avatar '{avatar_id}'")
        
        logger.info("  Step 2: Processing audio (Whisper embeddings)...")
        logger.info("  Step 3: Cross-attention fusion (single-step UNet)...")
        logger.info("  Step 4: VAE decoding...")
        logger.info("  Step 5: Compositing final video...")
        
        # Generate video
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{Path(audio_path).stem}.mp4")
        
        loop = asyncio.get_event_loop()
        video_path = await loop.run_in_executor(
            None,
            self.musetalk_api.generate,
            avatar_id,
            audio_path,
            output_path,
            True  # skip_save_images
        )
        
        return video_path
    
    def clear_cache(self, avatar_id: Optional[str] = None):
        """
        Clear avatar cache.
        
        Args:
            avatar_id: Specific avatar to clear, or None to clear all
        """
        if avatar_id:
            if self.engine == "sadtalker" and self.sadtalker_generator:
                self.sadtalker_generator.clear_cache()
            elif self.engine == "musetalk" and self.musetalk_api:
                self.musetalk_api.clear_avatar_cache(avatar_id)
            
            if avatar_id in self._avatar_cache:
                del self._avatar_cache[avatar_id]
            logger.info(f"🧹 Cleared cache for avatar: {avatar_id}")
        else:
            if self.engine == "sadtalker" and self.sadtalker_generator:
                self.sadtalker_generator.clear_cache()
            elif self.engine == "musetalk" and self.musetalk_api:
                for aid in list(self._avatar_cache.keys()):
                    self.musetalk_api.clear_avatar_cache(aid)
            
            self._avatar_cache.clear()
            logger.info("🧹 Cleared all avatar cache")
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about the current engine."""
        return {
            "engine": self.engine,
            "device": self.device,
            "size": self.size,
            "enhancer": self.enhancer if self.engine == "sadtalker" else "N/A",
            "initialized": self.initialized,
            "cached_avatars": len(self._avatar_cache),
            "capabilities": self._get_capabilities()
        }
    
    def _get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of the current engine."""
        if self.engine == "sadtalker":
            return {
                "speed": "moderate",
                "quality": "high",
                "lip_sync": "good",
                "full_body": True,
                "real_time": False,
                "face_enhancement": True,
                "pose_control": True,
                "typical_fps": "5-10 seconds per clip"
            }
        else:  # musetalk
            return {
                "speed": "very fast",
                "quality": "very high",
                "lip_sync": "excellent",
                "full_body": False,
                "real_time": True,
                "face_enhancement": False,
                "pose_control": False,
                "typical_fps": "30+ FPS (real-time)"
            }


# Global functions for easy access

def get_unified_generator() -> Optional[UnifiedAvatarGenerator]:
    """Get global unified avatar generator instance."""
    return _unified_generator


def initialize_unified_generator(
    engine: AvatarEngine = "sadtalker",
    device: str = None,
    size: int = 256,
    enhancer: Optional[str] = 'gfpgan'
) -> bool:
    """
    Initialize global unified avatar generator.
    
    Args:
        engine: 'sadtalker' or 'musetalk'
        device: 'cuda:0', 'cuda:1', 'cpu', etc.
        size: Output size (256 or 512)
        enhancer: Face enhancer (SadTalker only)
        
    Returns:
        True if successful
    """
    global _unified_generator
    
    try:
        # If device not specified, check environment variable
        if device is None:
            device = os.getenv("AVATAR_DEVICE", "cuda")
        
        _unified_generator = UnifiedAvatarGenerator(
            engine=engine,
            device=device,
            size=size,
            enhancer=enhancer
        )
        
        _unified_generator.initialize()
        
        logger.info(f"✅ Unified avatar generator initialized")
        logger.info(f"   Active Engine: {engine.upper()}")
        logger.info(f"   Device: {device}")
        logger.info(f"   Size: {size}x{size}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize unified generator: {e}")
        return False


async def generate_avatar(
    audio_path: str,
    image_path: str,
    output_dir: str,
    avatar_id: Optional[str] = None,
    fast_mode: bool = True,
    preprocess: str = 'crop',
    pic_size: int = None,
    enable_enhancer: bool = True
) -> Optional[str]:
    """
    Generate avatar video using the active engine.
    
    Args:
        audio_path: Path to audio file
        image_path: Path to reference image
        output_dir: Output directory
        avatar_id: Avatar ID for caching
        fast_mode: Use fast settings
        preprocess: Preprocessing mode (SadTalker)
        pic_size: Image size (256 or 512)
        enable_enhancer: Enable face enhancement (SadTalker)
        
    Returns:
        Path to generated video or None
    """
    generator = get_unified_generator()
    
    if generator is None:
        logger.error("Unified avatar generator not initialized")
        return None
    
    return await generator.generate_avatar_video(
        audio_path=audio_path,
        image_path=image_path,
        output_dir=output_dir,
        avatar_id=avatar_id,
        preprocess=preprocess,
        pic_size=pic_size,
        enable_enhancer=enable_enhancer,
        fast_mode=fast_mode
    )


def switch_avatar_engine(new_engine: AvatarEngine):
    """
    Switch the active avatar engine.
    
    Args:
        new_engine: 'sadtalker' or 'musetalk'
    """
    generator = get_unified_generator()
    
    if generator is None:
        logger.error("Unified avatar generator not initialized")
        return False
    
    generator.switch_engine(new_engine)
    return True


def get_engine_info() -> Optional[Dict[str, Any]]:
    """Get information about the current avatar engine."""
    generator = get_unified_generator()
    
    if generator is None:
        return None
    
    return generator.get_engine_info()

