"""
Text-to-Speech (TTS) utility with support for multiple models.
Supports local models (ChatterBox, VoxCPM) and API mode.
"""

import os
import logging
import tempfile
from typing import Optional
import torchaudio as ta

from .tts_models import TTSModelFactory, TTSModelBase

logger = logging.getLogger(__name__)

# Global TTS model instance
tts_model: Optional[TTSModelBase] = None
tts_model_name: Optional[str] = None
voice_clone_audio_path: Optional[str] = None


def initialize_tts(mode: str, voice_audio_path: Optional[str] = None):
    """
    Initialize TTS based on mode and configuration.
    
    Args:
        mode: "local" or "api"
        voice_audio_path: Path to reference audio for voice cloning (local mode)
    """
    global tts_model, tts_model_name, voice_clone_audio_path
    
    if mode == "local":
        try:
            # Get TTS model from environment
            model_name = os.getenv("TTS_MODEL", "chatterbox").lower()
            tts_model_name = model_name
            voice_clone_audio_path = voice_audio_path
            
            logger.info(f"Initializing TTS with model: {model_name}")
            
            # Prepare model-specific parameters
            model_kwargs = {}
            
            if model_name == "voxcpm":
                # Load VoxCPM-specific parameters from environment
                model_kwargs = {
                    "model_path": os.getenv("VOXCPM_MODEL_PATH", "VoxCPM-0.5B"),
                    "cfg_value": float(os.getenv("VOXCPM_CFG_VALUE", "2.0")),
                    "inference_timesteps": int(os.getenv("VOXCPM_INFERENCE_TIMESTEPS", "10")),
                    "normalize": os.getenv("VOXCPM_NORMALIZE", "true").lower() == "true",
                    "denoise": os.getenv("VOXCPM_DENOISE", "true").lower() == "true",
                    "retry_badcase": os.getenv("VOXCPM_RETRY_BADCASE", "true").lower() == "true"
                }
                logger.info(f"VoxCPM parameters: {model_kwargs}")
            
            # Create model instance using factory
            tts_model = TTSModelFactory.create_model(
                model_name,
                voice_audio_path=voice_audio_path,
                **model_kwargs
            )
            
            # Load the model
            tts_model.load_model()
            
            logger.info(f"TTS model '{model_name}' initialized successfully")
            if voice_audio_path:
                logger.info(f"Voice clone audio: {voice_audio_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize TTS model: {e}")
            raise
    else:
        logger.info("TTS mode set to API")


async def text_to_speech(text: str, mode: str, reference_audio_path: Optional[str] = None) -> str:
    """
    Convert text to speech audio.
    
    Args:
        text: Text to synthesize
        mode: "local" or "api"
        reference_audio_path: Optional path to reference audio for voice cloning
        
    Returns:
        Path to generated audio file
    """
    if mode == "local":
        return await _tts_local(text, reference_audio_path)
    else:
        return await _tts_api(text)


async def _tts_local(text: str, reference_audio_path: Optional[str] = None) -> str:
    """Generate speech using local TTS model."""
    global tts_model, voice_clone_audio_path
    
    if tts_model is None:
        raise RuntimeError("TTS model not initialized. Call initialize_tts first.")
    
    try:
        logger.info(f"Generating speech for text: {text[:100]}...")
        
        # Use provided reference audio or fall back to global setting
        ref_audio = reference_audio_path if reference_audio_path else voice_clone_audio_path
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audio", "generated")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate unique filename based on timestamp
        import time
        timestamp = int(time.time() * 1000)
        output_path = os.path.join(output_dir, f"voice_{timestamp}.wav")
        
        # Generate audio using the model
        wav, sample_rate = tts_model.generate(text, ref_audio)
        
        # Save audio to file
        ta.save(output_path, wav, sample_rate)
        logger.info(f"Audio saved to: {output_path}")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Local TTS failed: {e}")
        raise


async def _tts_api(text: str) -> str:
    """Generate speech using OpenAI TTS API."""
    try:
        from openai import OpenAI
        
        # Create client with minimal parameters
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            default_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "Voice Chat App"}
        )
        
        logger.info(f"Generating speech via API for text: {text[:100]}...")
        
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audio", "generated")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate unique filename
        import time
        timestamp = int(time.time() * 1000)
        output_path = os.path.join(output_dir, f"voice_{timestamp}.mp3")
        
        response.stream_to_file(output_path)
        logger.info(f"Audio saved to: {output_path}")
        
        return output_path
        
    except Exception as e:
        logger.error(f"API TTS failed: {e}")
        raise


def get_current_model_info() -> dict:
    """
    Get information about the currently loaded TTS model.
    
    Returns:
        Dictionary with model information
    """
    global tts_model, tts_model_name
    
    if tts_model is None:
        return {
            "model": "none",
            "status": "not_initialized"
        }
    
    return {
        "model": tts_model_name,
        "device": tts_model.device,
        "sample_rate": tts_model.get_sample_rate(),
        "status": "ready"
    }


def list_available_models() -> list:
    """List all available TTS models."""
    return TTSModelFactory.list_models()
