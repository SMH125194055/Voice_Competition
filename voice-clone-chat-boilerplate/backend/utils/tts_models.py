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
        """Detect available device (cuda/mps/cpu) from env or auto-detect."""
        # Check for TTS_DEVICE environment variable first
        tts_device = os.getenv("TTS_DEVICE")
        if tts_device:
            logger.info(f"Using TTS_DEVICE from environment: {tts_device}")
            return tts_device
        
        # Auto-detect if not specified
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
        """Generate speech using ChatterBox with speed optimizations."""
        if self.model is None:
            raise RuntimeError("ChatterBox model not initialized. Call load_model first.")
        
        # Use provided reference audio or fall back to default
        ref_audio = reference_audio_path if reference_audio_path else self.voice_audio_path
        
        logger.info(f"Generating speech with ChatterBox for text: {text[:100]}...")
        
        # Speed optimization parameters
        speed_params = {
            "temperature": float(os.getenv("CHATTERBOX_TEMPERATURE", "0.7")),  # Lower = faster, more deterministic
            "cfg_weight": float(os.getenv("CHATTERBOX_CFG_WEIGHT", "0.3")),   # Lower = faster
            "repetition_penalty": float(os.getenv("CHATTERBOX_REPETITION_PENALTY", "1.15")),
            "min_p": float(os.getenv("CHATTERBOX_MIN_P", "0.1")),  # Higher = faster, fewer options
            "top_p": float(os.getenv("CHATTERBOX_TOP_P", "0.9")),  # Lower = faster
            "exaggeration": float(os.getenv("CHATTERBOX_EXAGGERATION", "0.3"))  # Lower = less processing
        }
        
        if ref_audio and os.path.exists(ref_audio):
            logger.info(f"Using reference voice: {ref_audio}")
            wav = self.model.generate(text, audio_prompt_path=ref_audio, **speed_params)
        else:
            logger.info("Using default voice (no reference provided)")
            wav = self.model.generate(text, **speed_params)
        
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
            inference_timesteps=100,
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


class RVCTTS(TTSModelBase):
    """RVC-based voice cloning (fastest CPU option)."""
    
    def __init__(
        self,
        voice_audio_path: Optional[str] = None,
        base_tts: str = "piper",
        pitch_shift: int = 0,
        index_rate: float = 0.5,
        filter_radius: int = 3,
        rms_mix_rate: float = 0.25,
        protect_rate: float = 0.33
    ):
        super().__init__(voice_audio_path)
        self.base_tts = base_tts
        self.pitch_shift = pitch_shift
        self.index_rate = index_rate
        self.filter_radius = filter_radius
        self.rms_mix_rate = rms_mix_rate
        self.protect_rate = protect_rate
        self.piper_model = None
        self.rvc_model = None
        
    def load_model(self):
        """Load Piper TTS and RVC models."""
        try:
            # Import RVC
            try:
                from rvc_python.infer import RVCInference
                logger.info("RVC library loaded successfully")
            except ImportError:
                logger.error("rvc-python not installed. Install with: pip install rvc-python")
                raise
            
            # Import Piper
            try:
                from piper import PiperVoice
                logger.info("Piper TTS library loaded successfully")
            except ImportError:
                logger.error("piper-tts not installed. Install with: pip install piper-tts")
                raise
            
            logger.info(f"Loading RVC TTS on {self.device}...")
            
            # Load Piper for base TTS (very fast)
            logger.info("Loading Piper TTS model...")
            # Piper will use default voice, we'll convert it with RVC
            self.piper_model = "piper"  # Placeholder - actual implementation may vary
            
            logger.info("RVC TTS initialized successfully")
            logger.info("Note: RVC will train on reference audio at first use")
            
        except Exception as e:
            logger.error(f"Failed to load RVC model: {e}")
            raise
    
    def generate(self, text: str, reference_audio_path: Optional[str] = None) -> tuple:
        """Generate speech using Piper + RVC voice conversion."""
        try:
            # Use provided reference audio or fall back to default
            ref_audio = reference_audio_path if reference_audio_path else self.voice_audio_path
            
            logger.info(f"Generating speech with RVC for text: {text[:100]}...")
            
            # Step 1: Generate base audio with Piper (fast TTS)
            logger.info("Step 1/2: Generating base audio with edge-tts...")
            
            # Use edge-tts as a fast alternative (much faster than ChatterBox/VoxCPM)
            import edge_tts
            
            # Generate base audio
            communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
            temp_base = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            
            # Since we're already in an async context, we can await directly
            # But we need to run it in a new thread to avoid event loop conflicts
            import concurrent.futures
            import asyncio
            
            def _sync_generate():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(communicate.save(temp_base.name))
                    return temp_base.name
                finally:
                    loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_sync_generate)
                base_audio_path = future.result()
            
            logger.info(f"Base audio generated: {base_audio_path}")
            
            # Step 2: Convert voice with RVC if reference provided
            if ref_audio and os.path.exists(ref_audio):
                logger.info(f"Step 2/2: Converting voice with RVC using reference: {ref_audio}")
                
                from rvc_python.infer import RVCInference
                
                # Initialize RVC
                rvc = RVCInference(device=self.device)
                
                # Convert the voice
                output_audio = rvc.infer_file(
                    input_path=base_audio_path,
                    reference_path=ref_audio,
                    pitch_shift=self.pitch_shift,
                    index_rate=self.index_rate,
                    filter_radius=self.filter_radius,
                    rms_mix_rate=self.rms_mix_rate,
                    protect_rate=self.protect_rate
                )
                
                logger.info("Voice conversion complete")
            else:
                logger.info("No reference audio, using base voice")
                # Load base audio
                import torchaudio as ta
                output_audio, sr = ta.load(base_audio_path)
                if output_audio.dim() == 2 and output_audio.size(0) > 1:
                    output_audio = output_audio.mean(dim=0, keepdim=True)  # Convert to mono
            
            # Cleanup base audio
            try:
                os.unlink(base_audio_path)
            except:
                pass
            
            # Ensure 2D tensor
            if isinstance(output_audio, torch.Tensor):
                if output_audio.dim() == 1:
                    output_audio = output_audio.unsqueeze(0)
            elif isinstance(output_audio, np.ndarray):
                output_audio = torch.from_numpy(output_audio)
                if output_audio.dim() == 1:
                    output_audio = output_audio.unsqueeze(0)
            
            return output_audio, 16000  # RVC typically uses 16kHz
            
        except Exception as e:
            logger.error(f"RVC TTS failed: {e}")
            raise
    
    def get_sample_rate(self) -> int:
        """Get RVC sample rate."""
        return 16000


class CoquiXTTS(TTSModelBase):
    """Coqui XTTS - Fast voice cloning with good quality."""
    
    def __init__(self, voice_audio_path: Optional[str] = None, language: str = "en"):
        super().__init__(voice_audio_path)
        self.language = language
        self.model = None
        
    def load_model(self):
        """Load Coqui XTTS model."""
        try:
            from TTS.api import TTS
            logger.info(f"Loading Coqui XTTS model on {self.device}...")
            
            # Use XTTS v2 - fast and good quality
            self.model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
            
            logger.info("Coqui XTTS model loaded successfully")
            logger.info("XTTS supports voice cloning with reference audio")
            
        except ImportError:
            logger.error("Coqui TTS not installed. Install with: pip install TTS")
            raise
        except Exception as e:
            logger.error(f"Failed to load Coqui XTTS model: {e}")
            raise
    
    def generate(self, text: str, reference_audio_path: Optional[str] = None) -> tuple:
        """Generate speech using Coqui XTTS with voice cloning."""
        if self.model is None:
            raise RuntimeError("Coqui XTTS model not initialized. Call load_model first.")
        
        try:
            # Use provided reference audio or fall back to default
            ref_audio = reference_audio_path if reference_audio_path else self.voice_audio_path
            
            logger.info(f"Generating speech with Coqui XTTS for text: {text[:100]}...")
            
            if ref_audio and os.path.exists(ref_audio):
                logger.info(f"Using reference voice: {ref_audio}")
                
                
                # Generate with voice cloning
                wav = self.model.tts(
                    text=text,
                    speaker_wav=ref_audio,
                    language=self.language
                )
            else:
                logger.info("No reference audio, using default voice")
                wav = self.model.tts(text=text, language=self.language)
            
            # Convert to tensor
            if isinstance(wav, list):
                wav = np.array(wav, dtype=np.float32)
            
            if isinstance(wav, np.ndarray):
                wav = torch.from_numpy(wav)
            
            # Ensure 2D tensor
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            
            logger.info(f"Audio generated with shape: {wav.shape}")
            
            return wav, 22050  # XTTS uses 22.05kHz
            
        except Exception as e:
            logger.error(f"Coqui XTTS failed: {e}")
            raise
    
    def get_sample_rate(self) -> int:
        """Get Coqui XTTS sample rate."""
        return 22050


class FastTTS(TTSModelBase):
    """Fast TTS using edge-tts (no voice cloning, but very fast)."""
    
    def __init__(self, voice_audio_path: Optional[str] = None, voice: str = "en-US-GuyNeural"):
        super().__init__(voice_audio_path)
        self.voice = voice
        
    def load_model(self):
        """Load edge-tts (no model loading needed)."""
        try:
            import edge_tts
            logger.info("FastTTS initialized with edge-tts")
            logger.info("Note: FastTTS doesn't do voice cloning, but is very fast (~2-3 seconds)")
        except ImportError:
            logger.error("edge-tts not installed. Install with: pip install edge-tts")
            raise
    
    def generate(self, text: str, reference_audio_path: Optional[str] = None) -> tuple:
        """Generate speech using edge-tts (fast, no cloning)."""
        try:
            logger.info(f"Generating speech with FastTTS for text: {text[:100]}...")
            
            import edge_tts
            import concurrent.futures
            import asyncio
            
            # Generate audio with edge-tts
            communicate = edge_tts.Communicate(text, voice=self.voice)
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            
            def _sync_generate():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(communicate.save(temp_output.name))
                    return temp_output.name
                finally:
                    loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_sync_generate)
                audio_path = future.result()
            
            logger.info(f"Audio generated: {audio_path}")
            
            # Load audio and convert to tensor
            import torchaudio as ta
            audio, sr = ta.load(audio_path)
            
            # Convert to mono if stereo
            if audio.dim() == 2 and audio.size(0) > 1:
                audio = audio.mean(dim=0, keepdim=True)
            
            # Ensure 2D tensor
            if audio.dim() == 1:
                audio = audio.unsqueeze(0)
            
            # Cleanup
            try:
                os.unlink(audio_path)
            except:
                pass
            
            # Note: edge-tts uses 24kHz typically, but we'll resample if needed
            return audio, sr
            
        except Exception as e:
            logger.error(f"FastTTS failed: {e}")
            raise
    
    def get_sample_rate(self) -> int:
        """Get edge-tts sample rate."""
        return 24000


import tempfile


class TTSModelFactory:
    """Factory for creating TTS model instances."""
    
    _models = {
        "chatterbox": ChatterBoxTTS,
        "voxcpm": VoxCPMTTS,
        "rvc": RVCTTS,
        "fast": FastTTS,
        "xtts": CoquiXTTS,
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
            model_name: Name of the model (chatterbox, voxcpm, rvc, etc.)
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
        elif model_name == "rvc":
            return model_class(
                voice_audio_path=voice_audio_path,
                base_tts=kwargs.get("base_tts", "piper"),
                pitch_shift=kwargs.get("pitch_shift", 0),
                index_rate=kwargs.get("index_rate", 0.5),
                filter_radius=kwargs.get("filter_radius", 3),
                rms_mix_rate=kwargs.get("rms_mix_rate", 0.25),
                protect_rate=kwargs.get("protect_rate", 0.33)
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

