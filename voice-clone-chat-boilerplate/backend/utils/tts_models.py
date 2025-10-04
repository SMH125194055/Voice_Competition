"""
TTS Model interfaces and implementations.
Supports multiple TTS backends: ChatterBox, VoxCPM, and future models.
"""

import os
import sys
import logging
from abc import ABC, abstractmethod
from typing import Optional
import torch
import numpy as np

logger = logging.getLogger(__name__)


class TTSModelBase(ABC):
    """Base class for all TTS models."""
    
    def __init__(self, voice_audio_path: Optional[str] = None):
        self.voice_audio_path = voice_audio_path
        self.model = None
        self.device = self._detect_device()
        
    def _detect_device(self) -> str:
        """Detect available device (cuda/mps/cpu)."""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    @abstractmethod
    def load_model(self):
        """Load the TTS model."""
        pass
    
    @abstractmethod
    def generate(self, text: str, reference_audio_path: Optional[str] = None) -> tuple:
        """
        Generate speech from text.
        
        Args:
            text: Text to synthesize
            reference_audio_path: Optional reference audio for voice cloning
            
        Returns:
            Tuple of (audio_tensor, sample_rate)
        """
        pass
    
    @abstractmethod
    def get_sample_rate(self) -> int:
        """Get the model's sample rate."""
        pass


class ChatterBoxTTS(TTSModelBase):
    """ChatterBox TTS implementation."""
    
    def load_model(self):
        """Load ChatterBox model."""
        try:
            # Add Chatterbox to path
            chatterbox_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "Chatterbox-gitclone",
                "chatterbox",
                "src"
            )
            if chatterbox_path not in sys.path:
                sys.path.insert(0, chatterbox_path)
            
            from chatterbox.tts import ChatterboxTTS as ChatterboxModel
            
            logger.info(f"Loading ChatterBox TTS model on {self.device}...")
            self.model = ChatterboxModel.from_pretrained(device=self.device)
            logger.info("ChatterBox TTS model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load ChatterBox model: {e}")
            raise
    
    def generate(self, text: str, reference_audio_path: Optional[str] = None) -> tuple:
        """Generate speech using ChatterBox."""
        if self.model is None:
            raise RuntimeError("ChatterBox model not initialized. Call load_model first.")
        
        # Use provided reference audio or fall back to default
        ref_audio = reference_audio_path if reference_audio_path else self.voice_audio_path
        
        logger.info(f"Generating speech with ChatterBox for text: {text[:100]}...")
        
        if ref_audio and os.path.exists(ref_audio):
            logger.info(f"Using reference voice: {ref_audio}")
            wav = self.model.generate(text, audio_prompt_path=ref_audio)
        else:
            logger.info("Using default voice (no reference provided)")
            wav = self.model.generate(text)
        
        return wav, self.model.sr
    
    def get_sample_rate(self) -> int:
        """Get ChatterBox sample rate."""
        if self.model is None:
            return 16000  # Default
        return self.model.sr


class VoxCPMTTS(TTSModelBase):
    """VoxCPM TTS implementation."""
    
    def __init__(
        self,
        voice_audio_path: Optional[str] = None,
        model_path: str = "VoxCPM-0.5B",
        cfg_value: float = 2.0,
        inference_timesteps: int = 10,
        normalize: bool = True,
        denoise: bool = True,
        retry_badcase: bool = True
    ):
        super().__init__(voice_audio_path)
        self.model_path = model_path
        self.cfg_value = cfg_value
        self.inference_timesteps = inference_timesteps
        self.normalize = normalize
        self.denoise = denoise
        self.retry_badcase = retry_badcase
        
    def load_model(self):
        """Load VoxCPM model."""
        try:
            # Add VoxCPM to path if needed
            voxcpm_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "VoxCpm-gitclone",
                "VoxCPM",
                "src"
            )
            if voxcpm_path not in sys.path:
                sys.path.insert(0, voxcpm_path)
            
            from voxcpm import VoxCPM
            
            logger.info(f"Loading VoxCPM TTS model from {self.model_path} on {self.device}...")
            
            # Check if model_path is absolute or relative
            if not os.path.isabs(self.model_path):
                # Relative path - assume it's in backend directory
                full_model_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    self.model_path
                )
            else:
                full_model_path = self.model_path
            
            # Load from local path
            if os.path.exists(full_model_path):
                logger.info(f"Loading VoxCPM from local path: {full_model_path}")
                self.model = VoxCPM.from_pretrained(full_model_path)
            else:
                # Try loading from HuggingFace
                logger.info(f"Loading VoxCPM from HuggingFace: {self.model_path}")
                self.model = VoxCPM.from_pretrained(self.model_path)
            
            logger.info("VoxCPM TTS model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load VoxCPM model: {e}")
            raise
    
    def generate(self, text: str, reference_audio_path: Optional[str] = None) -> tuple:
        """Generate speech using VoxCPM."""
        if self.model is None:
            raise RuntimeError("VoxCPM model not initialized. Call load_model first.")
        
        # Use provided reference audio or fall back to default
        ref_audio = reference_audio_path if reference_audio_path else self.voice_audio_path
        
        logger.info(f"Generating speech with VoxCPM for text: {text[:100]}...")
        
        # VoxCPM requires BOTH prompt_wav_path and prompt_text, or BOTH None
        # If we have reference audio, we need to provide dummy prompt text
        if ref_audio and os.path.exists(ref_audio):
            logger.info(f"Using reference voice: {ref_audio}")
            prompt_wav_path = ref_audio
            # VoxCPM needs prompt_text when using prompt_wav_path
            # Use a generic prompt text or extract from the reference audio
            prompt_text = "This is a sample voice for voice cloning."
        else:
            logger.info("Using default voice (no reference provided)")
            prompt_wav_path = None
            prompt_text = None
        
        wav = self.model.generate(
            text=text,
            prompt_wav_path=prompt_wav_path,
            prompt_text=prompt_text,  # Now properly paired with prompt_wav_path
            cfg_value=self.cfg_value,
            inference_timesteps=self.inference_timesteps,
            normalize=self.normalize,
            denoise=self.denoise,
            retry_badcase=self.retry_badcase,
            retry_badcase_max_times=3,
            retry_badcase_ratio_threshold=6.0
        )
        
        # VoxCPM returns 1D tensor, but torchaudio.save expects 2D (channels, samples)
        # Reshape to (1, samples) for mono audio if needed
        if isinstance(wav, torch.Tensor):
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)  # Add channel dimension: (samples,) -> (1, samples)
                logger.info(f"Reshaped audio tensor from 1D to 2D: {wav.shape}")
        else:
            # If it's a numpy array, convert to tensor
            if isinstance(wav, np.ndarray):
                wav = torch.from_numpy(wav)
                if wav.dim() == 1:
                    wav = wav.unsqueeze(0)
                logger.info(f"Converted numpy array to tensor: {wav.shape}")
        
        return wav, 16000  # VoxCPM uses 16kHz
    
    def get_sample_rate(self) -> int:
        """Get VoxCPM sample rate."""
        return 16000


class TTSModelFactory:
    """Factory for creating TTS model instances."""
    
    _models = {
        "chatterbox": ChatterBoxTTS,
        "voxcpm": VoxCPMTTS,
    }
    
    @classmethod
    def create_model(
        cls,
        model_name: str,
        voice_audio_path: Optional[str] = None,
        **kwargs
    ) -> TTSModelBase:
        """
        Create a TTS model instance.
        
        Args:
            model_name: Name of the model (chatterbox, voxcpm, etc.)
            voice_audio_path: Path to reference audio for voice cloning
            **kwargs: Additional model-specific parameters
            
        Returns:
            TTSModelBase instance
        """
        model_name = model_name.lower()
        
        if model_name not in cls._models:
            available = ", ".join(cls._models.keys())
            raise ValueError(
                f"Unknown TTS model: {model_name}. "
                f"Available models: {available}"
            )
        
        model_class = cls._models[model_name]
        
        # Create model instance with appropriate parameters
        if model_name == "voxcpm":
            return model_class(
                voice_audio_path=voice_audio_path,
                model_path=kwargs.get("model_path", "VoxCPM-0.5B"),
                cfg_value=kwargs.get("cfg_value", 2.0),
                inference_timesteps=kwargs.get("inference_timesteps", 10),
                normalize=kwargs.get("normalize", True),
                denoise=kwargs.get("denoise", True),
                retry_badcase=kwargs.get("retry_badcase", True)
            )
        else:
            return model_class(voice_audio_path=voice_audio_path)
    
    @classmethod
    def register_model(cls, name: str, model_class: type):
        """
        Register a new TTS model.
        
        Args:
            name: Model name
            model_class: Model class (must inherit from TTSModelBase)
        """
        if not issubclass(model_class, TTSModelBase):
            raise TypeError(f"Model class must inherit from TTSModelBase")
        
        cls._models[name.lower()] = model_class
        logger.info(f"Registered TTS model: {name}")
    
    @classmethod
    def list_models(cls):
        """List all available TTS models."""
        return list(cls._models.keys())

