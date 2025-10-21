"""
Speech-to-Text (STT) utility using Whisper.
Supports both local model and API mode.
"""


import os
import logging
from typing import Optional
import tempfile

logger = logging.getLogger(__name__)

# Global Whisper model (loaded at startup if MODE=local)
whisper_model = None


def initialize_stt(mode: str, model_name: str = "base"):
    """
    Initialize STT based on mode.
    
    Args:
        mode: "local" or "api"
        model_name: Whisper model size (tiny, base, small, medium, large)
    """
    global whisper_model
    
    if mode == "local":
        try:
            import whisper
            import torch
            
            # Check for STT_DEVICE environment variable
            stt_device = os.getenv("STT_DEVICE")
            if stt_device:
                logger.info(f"Loading Whisper model: {model_name} on device: {stt_device}")
                whisper_model = whisper.load_model(model_name, device=stt_device)
                logger.info(f"Whisper model loaded successfully on {stt_device}")
            else:
                logger.info(f"Loading Whisper model: {model_name} (auto-detect device)")
                whisper_model = whisper.load_model(model_name)
                logger.info("Whisper model loaded successfully")
        except ImportError:
            logger.error("Whisper not installed. Install with: pip install git+https://github.com/openai/whisper.git")
            raise
        except FileNotFoundError as e:
            logger.error("FFmpeg not found. Whisper requires FFmpeg to be installed.")
            logger.error("Download from: https://ffmpeg.org/download.html")
            logger.error("Or install via: winget install ffmpeg (Windows)")
            raise RuntimeError("FFmpeg not found. Please install FFmpeg and add it to PATH.") from e
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    else:
        logger.info("STT mode set to API")


async def transcribe_audio(audio_file_path: str, mode: str) -> str:
    """
    Transcribe audio to text.
    
    Args:
        audio_file_path: Path to audio file
        mode: "local" or "api"
        
    Returns:
        Transcribed text
    """
    if mode == "local":
        return await _transcribe_local(audio_file_path)
    else:
        return await _transcribe_api(audio_file_path)


async def _transcribe_local(audio_file_path: str) -> str:
    """Transcribe using local Whisper model - ENGLISH ONLY."""
    global whisper_model
    
    if whisper_model is None:
        raise RuntimeError("Whisper model not initialized. Call initialize_stt first.")
    
    try:
        logger.info(f"Transcribing audio file (English only): {audio_file_path}")
        # Force English language to prevent vague behavior with other languages
        result = whisper_model.transcribe(
            audio_file_path,
            language='en',  # Force English
            fp16=False
        )
        text = result["text"].strip()
        logger.info(f"Transcription result (en): {text}")
        return text
    except Exception as e:
        logger.error(f"Local transcription failed: {e}")
        raise


async def _transcribe_api(audio_file_path: str) -> str:
    """Transcribe using OpenAI Whisper API - ENGLISH ONLY."""
    try:
        from openai import OpenAI
        
        # Create client with minimal parameters
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            default_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "Voice Chat App"}
        )
        
        logger.info(f"Transcribing via API (English only): {audio_file_path}")
        
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"  # Force English
            )
        
        text = transcript.text.strip()
        logger.info(f"API transcription result (en): {text}")
        return text
    except Exception as e:
        logger.error(f"API transcription failed: {e}")
        raise


