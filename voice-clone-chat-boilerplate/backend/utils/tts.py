"""
Text-to-Speech (TTS) utility using ChatterBox.
Supports both local model with voice cloning and API mode.
"""

import os
import sys
import logging
import tempfile
from typing import Optional
import torch
import torchaudio as ta

logger = logging.getLogger(__name__)

# Global ChatterBox model and settings
chatterbox_model = None
voice_clone_audio_path = None
device = None


def initialize_tts(mode: str, voice_audio_path: Optional[str] = None):
    """
    Initialize TTS based on mode.
    
    Args:
        mode: "local" or "api"
        voice_audio_path: Path to reference audio for voice cloning (local mode)
    """
    global chatterbox_model, voice_clone_audio_path, device
    
    if mode == "local":
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
            
            from chatterbox.tts import ChatterboxTTS
            
            # Detect device
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
            
            logger.info(f"Using device: {device}")
            logger.info("Loading ChatterBox TTS model...")
            
            chatterbox_model = ChatterboxTTS.from_pretrained(device=device)
            voice_clone_audio_path = voice_audio_path
            
            logger.info("ChatterBox TTS model loaded successfully")
            if voice_clone_audio_path:
                logger.info(f"Voice clone audio: {voice_clone_audio_path}")
                
        except Exception as e:
            logger.error(f"Failed to load ChatterBox model: {e}")
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
    """Generate speech using local ChatterBox model."""
    global chatterbox_model, voice_clone_audio_path
    
    if chatterbox_model is None:
        raise RuntimeError("ChatterBox model not initialized. Call initialize_tts first.")
    
    try:
        logger.info(f"Generating speech for text: {text[:100]}...")
        
        # Use provided reference audio or fall back to global setting
        ref_audio = reference_audio_path if reference_audio_path else voice_clone_audio_path
        
        # Generate audio with optional voice cloning
        # Using optimized parameters for faster generation
        if ref_audio and os.path.exists(ref_audio):
            logger.info(f"Using reference voice: {ref_audio}")
            wav = chatterbox_model.generate(text, audio_prompt_path=ref_audio)
        else:
            logger.info("Using default voice (no reference provided)")
            wav = chatterbox_model.generate(text)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        output_path = temp_file.name
        temp_file.close()
        
        ta.save(output_path, wav, chatterbox_model.sr)
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
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        output_path = temp_file.name
        temp_file.close()
        
        response.stream_to_file(output_path)
        logger.info(f"Audio saved to: {output_path}")
        
        return output_path
        
    except Exception as e:
        logger.error(f"API TTS failed: {e}")
        raise


