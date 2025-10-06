"""
FastAPI backend for voice chat application.
Supports STT (Whisper), LLM (OpenRouter), and TTS (ChatterBox) with voice cloning.
"""

import os
import logging
import tempfile
import base64
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from utils import (
    initialize_stt,
    initialize_tts,
    transcribe_audio,
    chat_with_llm,
    text_to_speech,
    get_current_model_info,
    list_available_models
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

MODE = os.getenv("MODE", "local")
VOICE_CLONE_AUDIO = os.getenv("VOICE_CLONE_AUDIO", "audio/Nafay_Org.mp3")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown lifecycle handler.
    Preload models at startup when MODE=local.
    """
    logger.info(f"Starting application in {MODE} mode")
    
    # Initialize STT
    try:
        initialize_stt(MODE, WHISPER_MODEL)
    except Exception as e:
        logger.error(f"Failed to initialize STT: {e}")
    
    # Initialize TTS
    try:
        initialize_tts(MODE, VOICE_CLONE_AUDIO)
    except Exception as e:
        logger.error(f"Failed to initialize TTS: {e}")
    
    logger.info("Application startup complete")
    
    yield
    
    logger.info("Application shutdown")


# Create FastAPI app
app = FastAPI(
    title="Voice Chat API",
    description="Voice chat backend with STT, LLM, and TTS capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class SpeakRequest(BaseModel):
    text: str


class TranscribeResponse(BaseModel):
    text: str


# Root endpoint
@app.get("/")
async def root():
    """Health check endpoint with model information."""
    model_info = get_current_model_info()
    return {
        "status": "running",
        "mode": MODE,
        "tts_model": model_info.get("model", "unknown"),
        "tts_device": model_info.get("device", "unknown"),
        "available_tts_models": list_available_models(),
        "endpoints": ["/transcribe", "/chat", "/speak", "/chat-voice"]
    }


# Endpoint 1: Transcribe audio to text
@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    """
    Transcribe audio file to text using Whisper.
    
    Args:
        audio: Audio file (WAV, MP3, WebM, etc.)
        
    Returns:
        Transcribed text
    """
    temp_audio = None
    
    try:
        # Detect file extension from content type or filename
        file_ext = ".webm"  # Default to webm
        if audio.content_type:
            logger.info(f"Received audio with content type: {audio.content_type}")
            if "wav" in audio.content_type or "wave" in audio.content_type:
                file_ext = ".wav"
            elif "mp3" in audio.content_type:
                file_ext = ".mp3"
            elif "webm" in audio.content_type:
                file_ext = ".webm"
        
        # Save uploaded file temporarily
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        content = await audio.read()
        logger.info(f"Received {len(content)} bytes of audio data")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Received empty audio file")
        
        temp_audio.write(content)
        temp_audio.flush()  # Ensure data is written to disk
        temp_audio.close()
        
        logger.info(f"Saved audio to: {temp_audio.name}")
        
        # Transcribe
        text = await transcribe_audio(temp_audio.name, MODE)
        
        return TranscribeResponse(text=text)
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup
        if temp_audio and os.path.exists(temp_audio.name):
            try:
                os.unlink(temp_audio.name)
            except:
                pass


# Endpoint 2: Chat with LLM
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the LLM and get a response.
    
    Args:
        request: Chat request with message
        
    Returns:
        LLM response
    """
    try:
        reply = await chat_with_llm(request.message)
        return ChatResponse(reply=reply)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint 3: Text to speech
@app.post("/speak")
async def speak(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    reference_audio: UploadFile = File(None)
):
    """
    Convert text to speech with cloned voice.
    
    Args:
        text: Text to convert to speech
        reference_audio: Optional reference audio for voice cloning
        
    Returns:
        Audio file stream
    """
    temp_ref_audio = None
    output_audio = None
    
    try:
        # Save reference audio temporarily if provided
        ref_audio_path = None
        if reference_audio:
            # Save the uploaded audio (could be WebM, WAV, MP3, etc.)
            temp_uploaded = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
            content = await reference_audio.read()
            temp_uploaded.write(content)
            temp_uploaded.close()
            
            # Convert to WAV format for XTTS compatibility
            try:
                from pydub import AudioSegment
                
                # Load the audio (pydub auto-detects format)
                audio = AudioSegment.from_file(temp_uploaded.name)
                
                # Convert to WAV
                temp_ref_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                audio.export(temp_ref_audio.name, format="wav")
                temp_ref_audio.close()
                
                ref_audio_path = temp_ref_audio.name
                
                # Clean up the uploaded file
                os.unlink(temp_uploaded.name)
                
                logger.info(f"Converted reference audio to WAV: {ref_audio_path}")
                
            except Exception as conv_error:
                logger.error(f"Audio conversion failed: {conv_error}")
                # Clean up
                if os.path.exists(temp_uploaded.name):
                    os.unlink(temp_uploaded.name)
                raise HTTPException(status_code=500, detail=f"Failed to convert audio format: {conv_error}")
        else:
            # Use default from .env if no reference provided
            ref_audio_path = VOICE_CLONE_AUDIO
        
        # Generate speech with specified reference audio
        output_audio = await text_to_speech(text, MODE, ref_audio_path)
        
        # Schedule cleanup of generated audio after response is sent
        async def cleanup_file():
            try:
                import asyncio
                await asyncio.sleep(2)  # Wait for file to be sent
                if output_audio and os.path.exists(output_audio):
                    os.unlink(output_audio)
                    logger.info(f"Cleaned up: {output_audio}")
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")
        
        background_tasks.add_task(cleanup_file)
        
        # Return audio file
        return FileResponse(
            output_audio,
            media_type="audio/wav",
            filename="speech.wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup temporary reference audio
        if temp_ref_audio and os.path.exists(temp_ref_audio.name):
            try:
                os.unlink(temp_ref_audio.name)
            except:
                pass


# Endpoint 4: Full voice chat pipeline
@app.post("/chat-voice")
async def chat_voice(audio: UploadFile = File(...)):
    """
    Complete voice chat pipeline:
    1. Transcribe user audio to text
    2. Send text to LLM
    3. Convert LLM response to speech with cloned voice
    4. Return both text reply and audio
    
    Args:
        audio: User's audio file
        
    Returns:
        JSON with reply text + audio file
    """
    temp_audio = None
    output_audio = None
    
    try:
        # Detect file extension from content type
        file_ext = ".webm"  # Default to webm
        if audio.content_type:
            logger.info(f"Received audio with content type: {audio.content_type}")
            if "wav" in audio.content_type or "wave" in audio.content_type:
                file_ext = ".wav"
            elif "mp3" in audio.content_type:
                file_ext = ".mp3"
            elif "webm" in audio.content_type:
                file_ext = ".webm"
        
        # Step 1: Transcribe user audio
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        content = await audio.read()
        logger.info(f"Received {len(content)} bytes of audio data")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Received empty audio file")
        
        temp_audio.write(content)
        temp_audio.flush()  # Ensure data is written to disk
        temp_audio.close()
        
        logger.info(f"Saved audio to: {temp_audio.name}")
        logger.info("Step 1: Transcribing user audio...")
        user_text = await transcribe_audio(temp_audio.name, MODE)
        logger.info(f"User said: {user_text}")
        
        # Step 2: Get LLM response
        logger.info("Step 2: Getting LLM response...")
        reply_text = await chat_with_llm(user_text)
        logger.info(f"LLM replied: {reply_text}")
        
        # Step 3: Convert reply to speech
        logger.info("Step 3: Generating speech...")
        output_audio = await text_to_speech(reply_text, MODE)
        
        # Encode reply text for safe HTTP header transmission
        reply_text_encoded = base64.b64encode(reply_text.encode('utf-8')).decode('ascii')
        
        # Return both text and audio
        return FileResponse(
            output_audio,
            media_type="audio/wav",
            filename="reply.wav",
            headers={
                "Content-Disposition": "attachment; filename=reply.wav",
                "X-Reply-Text": reply_text_encoded,  # Base64 encoded text
                "X-Reply-Text-Encoding": "base64"  # Indicate encoding
            }
        )
        
    except Exception as e:
        logger.error(f"Voice chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup input audio
        if temp_audio and os.path.exists(temp_audio.name):
            try:
                os.unlink(temp_audio.name)
            except:
                pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


