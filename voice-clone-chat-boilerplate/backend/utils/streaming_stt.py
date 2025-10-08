"""
Real-time Streaming Speech-to-Text utility.
Provides partial transcriptions as audio is being recorded.
"""

import os
import logging
import tempfile
from typing import AsyncGenerator
import asyncio

logger = logging.getLogger(__name__)

# Global Whisper model (shared with stt.py)
whisper_model = None


def initialize_streaming_stt(model=None):
    """Initialize streaming STT with an existing model."""
    global whisper_model
    whisper_model = model
    if whisper_model is not None:
        logger.info("Streaming STT initialized successfully with Whisper model")
    else:
        logger.warning("Streaming STT initialized but Whisper model is None")


async def transcribe_streaming(
    audio_file_path: str, 
    mode: str,
    chunk_duration: float = 2.0
) -> AsyncGenerator[dict, None]:
    """
    Transcribe audio with streaming/progressive updates.
    
    Args:
        audio_file_path: Path to audio file
        mode: "local" or "api"
        chunk_duration: Duration of each chunk for progressive transcription
        
    Yields:
        dict: {"partial": bool, "text": str, "confidence": float}
    """
    if mode == "local":
        async for result in _transcribe_streaming_local(audio_file_path, chunk_duration):
            yield result
    else:
        async for result in _transcribe_streaming_api(audio_file_path):
            yield result


async def _transcribe_streaming_local(
    audio_file_path: str, 
    chunk_duration: float = 2.0
) -> AsyncGenerator[dict, None]:
    """
    Transcribe using local Whisper model with progressive updates.
    Note: Whisper doesn't natively support streaming, so we simulate it
    by transcribing the full audio but yielding results progressively.
    """
    global whisper_model
    
    if whisper_model is None:
        logger.error("Whisper model not initialized in streaming_stt module")
        raise RuntimeError("Whisper model not initialized")
    
    logger.info(f"Using Whisper model: {type(whisper_model)}")
    
    try:
        logger.info(f"Starting streaming transcription: {audio_file_path}")
        
        # Yield initial status
        yield {
            "partial": True,
            "text": "",
            "status": "processing",
            "confidence": 0.0
        }
        
        # Simulate progressive loading
        await asyncio.sleep(0.1)
        yield {
            "partial": True,
            "text": "...",
            "status": "transcribing",
            "confidence": 0.0
        }
        
        # Run transcription in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            whisper_model.transcribe, 
            audio_file_path
        )
        
        text = result["text"].strip()
        
        # If the text is short, yield it all at once
        if len(text) < 50:
            yield {
                "partial": False,
                "text": text,
                "status": "complete",
                "confidence": 1.0
            }
        else:
            # Simulate progressive transcription by yielding words progressively
            words = text.split()
            for i in range(0, len(words), 3):  # Yield 3 words at a time
                partial_text = " ".join(words[:i+3])
                is_final = (i + 3) >= len(words)
                
                yield {
                    "partial": not is_final,
                    "text": partial_text,
                    "status": "complete" if is_final else "transcribing",
                    "confidence": 0.8 if not is_final else 1.0
                }
                
                if not is_final:
                    await asyncio.sleep(0.1)  # Small delay for progressive effect
        
        logger.info(f"Streaming transcription complete: {text}")
        
    except Exception as e:
        logger.error(f"Streaming transcription failed: {e}")
        yield {
            "partial": False,
            "text": "",
            "status": "error",
            "error": str(e),
            "confidence": 0.0
        }


async def _transcribe_streaming_api(audio_file_path: str) -> AsyncGenerator[dict, None]:
    """
    Transcribe using OpenAI Whisper API.
    Note: The API doesn't support true streaming, so we simulate it.
    """
    try:
        from openai import OpenAI
        
        # Yield initial status
        yield {
            "partial": True,
            "text": "",
            "status": "processing",
            "confidence": 0.0
        }
        
        await asyncio.sleep(0.1)
        yield {
            "partial": True,
            "text": "...",
            "status": "transcribing",
            "confidence": 0.0
        }
        
        # Create client
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Voice Chat App"
            }
        )
        
        logger.info(f"Transcribing via streaming API: {audio_file_path}")
        
        # OpenAI API doesn't support streaming for transcription
        # So we run it normally and yield the result
        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"  # Get more detailed info
            )
        
        text = transcript.text.strip()
        
        # Simulate progressive output
        if len(text) < 50:
            yield {
                "partial": False,
                "text": text,
                "status": "complete",
                "confidence": 1.0
            }
        else:
            words = text.split()
            for i in range(0, len(words), 3):
                partial_text = " ".join(words[:i+3])
                is_final = (i + 3) >= len(words)
                
                yield {
                    "partial": not is_final,
                    "text": partial_text,
                    "status": "complete" if is_final else "transcribing",
                    "confidence": 0.9 if not is_final else 1.0
                }
                
                if not is_final:
                    await asyncio.sleep(0.05)
        
        logger.info(f"API streaming transcription complete: {text}")
        
    except Exception as e:
        logger.error(f"API streaming transcription failed: {e}")
        yield {
            "partial": False,
            "text": "",
            "status": "error",
            "error": str(e),
            "confidence": 0.0
        }

