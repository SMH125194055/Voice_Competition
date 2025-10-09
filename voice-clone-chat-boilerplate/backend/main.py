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
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import json

from utils import (
    initialize_stt,
    initialize_tts,
    transcribe_audio,
    chat_with_llm,
    text_to_speech,
    get_current_model_info,
    list_available_models,
    get_vad_processor,
    detect_speech,
    has_speech,
    clean_audio
)
from utils.streaming_stt import transcribe_streaming, initialize_streaming_stt
from utils.realtime_stt import (
    transcribe_stream_progressive, 
    initialize_realtime_stt,
    process_webm_stream
)
from utils.websocket_stt import (
    transcribe_audio_stream_fast,
    initialize_websocket_stt
)
from utils.parallel_whisper import (
    initialize_parallel_whisper,
    transcribe_audio_parallel,
    transcribe_audio_batched,
    get_pool_info
)
from utils.text_chunking import chunk_text_by_words, get_word_timestamps
import utils.stt as stt_module
import asyncio

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
TRANSCRIPTION_MODE = os.getenv("TRANSCRIPTION_MODE", "parallel")  # "parallel" or "sequential"

# Reference voice storage directory
REFERENCE_VOICE_DIR = "audio/reference_voices"
os.makedirs(REFERENCE_VOICE_DIR, exist_ok=True)


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
        # Initialize streaming STT with the same model
        initialize_streaming_stt(stt_module.whisper_model)
        initialize_realtime_stt(stt_module.whisper_model)
        initialize_websocket_stt(stt_module.whisper_model)
        
        # Initialize parallel Whisper with multiple model instances (if enabled)
        if TRANSCRIPTION_MODE == "parallel":
            num_workers = int(os.getenv("WHISPER_WORKERS", "3"))
            logger.info(f"Initializing {num_workers} parallel Whisper workers...")
            initialize_parallel_whisper(stt_module.whisper_model, num_workers=num_workers)
            logger.info(f"✅ Parallel processing STT initialized with {num_workers} workers")
        else:
            logger.info(f"Sequential processing mode enabled (TRANSCRIPTION_MODE=sequential)")
        
        logger.info(f"Streaming STT initialized with model: {stt_module.whisper_model is not None}")
        logger.info(f"Real-time chunk-based STT initialized")
        logger.info(f"Transcription mode: {TRANSCRIPTION_MODE}")
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
    vad_processor = get_vad_processor()
    pool_info = get_pool_info()
    return {
        "status": "running",
        "mode": MODE,
        "transcription_mode": TRANSCRIPTION_MODE,
        "tts_model": model_info.get("model", "unknown"),
        "tts_device": model_info.get("device", "unknown"),
        "available_tts_models": list_available_models(),
        "vad_enabled": vad_processor.is_available(),
        "parallel_whisper": {
            "enabled": TRANSCRIPTION_MODE == "parallel" and pool_info["initialized"],
            "workers": pool_info["workers"] if TRANSCRIPTION_MODE == "parallel" else 1,
            "target_workers": pool_info["target_workers"]
        },
        "endpoints": [
            "/transcribe", 
            "/transcribe-stream",
            "/chat", 
            "/speak", 
            "/chat-voice",
            "/chat-voice-stream",
            "/vad-transcribe",
            "/detect-speech",
            "/vad-chat-voice"
        ]
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


# Endpoint 5: VAD-enhanced transcription (cleans audio before transcribing)
@app.post("/vad-transcribe", response_model=TranscribeResponse)
async def vad_transcribe(audio: UploadFile = File(...)):
    """
    Transcribe audio with VAD preprocessing to remove silence.
    
    Args:
        audio: Audio file (WAV, MP3, WebM, etc.)
        
    Returns:
        Transcribed text
    """
    temp_audio = None
    cleaned_audio = None
    
    try:
        # Detect file extension
        file_ext = ".webm"
        if audio.content_type:
            logger.info(f"Received audio with content type: {audio.content_type}")
            if "wav" in audio.content_type or "wave" in audio.content_type:
                file_ext = ".wav"
            elif "mp3" in audio.content_type:
                file_ext = ".mp3"
            elif "webm" in audio.content_type:
                file_ext = ".webm"
        
        # Save uploaded file
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        content = await audio.read()
        logger.info(f"Received {len(content)} bytes of audio data")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Received empty audio file")
        
        temp_audio.write(content)
        temp_audio.flush()
        temp_audio.close()
        
        logger.info(f"Saved audio to: {temp_audio.name}")
        
        # Check if audio has speech
        has_voice, speech_duration = has_speech(temp_audio.name, threshold=0.5)
        logger.info(f"VAD check: has_speech={has_voice}, duration={speech_duration:.2f}s")
        
        if not has_voice or speech_duration < 0.3:
            raise HTTPException(status_code=400, detail="No speech detected in audio")
        
        # Clean audio to remove silence
        cleaned_audio = clean_audio(temp_audio.name)
        audio_to_transcribe = cleaned_audio if cleaned_audio else temp_audio.name
        
        logger.info(f"Transcribing cleaned audio: {audio_to_transcribe}")
        
        # Transcribe
        text = await transcribe_audio(audio_to_transcribe, MODE)
        
        return TranscribeResponse(text=text)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VAD transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup
        if temp_audio and os.path.exists(temp_audio.name):
            try:
                os.unlink(temp_audio.name)
            except:
                pass
        if cleaned_audio and cleaned_audio != temp_audio.name and os.path.exists(cleaned_audio):
            try:
                os.unlink(cleaned_audio)
            except:
                pass


# Endpoint 6: VAD speech detection (returns speech segments)
@app.post("/detect-speech")
async def detect_speech_segments(audio: UploadFile = File(...)):
    """
    Detect speech segments in audio using VAD.
    
    Args:
        audio: Audio file
        
    Returns:
        List of speech segments with timestamps
    """
    temp_audio = None
    
    try:
        # Save uploaded file
        file_ext = ".wav" if audio.content_type and "wav" in audio.content_type else ".webm"
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        content = await audio.read()
        temp_audio.write(content)
        temp_audio.flush()
        temp_audio.close()
        
        # Detect speech segments
        segments = detect_speech(temp_audio.name)
        
        # Check if speech was found
        has_voice, total_duration = has_speech(temp_audio.name)
        
        return {
            "has_speech": has_voice,
            "total_speech_duration": total_duration,
            "segments": segments,
            "segment_count": len(segments)
        }
        
    except Exception as e:
        logger.error(f"Speech detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        if temp_audio and os.path.exists(temp_audio.name):
            try:
                os.unlink(temp_audio.name)
            except:
                pass


# Endpoint 7: Complete VAD-enhanced voice chat
@app.post("/vad-chat-voice")
async def vad_chat_voice(audio: UploadFile = File(...)):
    """
    Complete voice chat pipeline with VAD enhancement:
    1. Detect and validate speech using VAD
    2. Clean audio by removing silence
    3. Transcribe cleaned audio to text
    4. Send text to LLM
    5. Convert LLM response to speech
    6. Return both text reply and audio
    
    Args:
        audio: User's audio file
        
    Returns:
        JSON with reply text + audio file
    """
    temp_audio = None
    cleaned_audio = None
    output_audio = None
    
    try:
        # Detect file extension
        file_ext = ".webm"
        if audio.content_type:
            logger.info(f"Received audio with content type: {audio.content_type}")
            if "wav" in audio.content_type or "wave" in audio.content_type:
                file_ext = ".wav"
            elif "mp3" in audio.content_type:
                file_ext = ".mp3"
            elif "webm" in audio.content_type:
                file_ext = ".webm"
        
        # Save uploaded audio
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        content = await audio.read()
        logger.info(f"Received {len(content)} bytes of audio data")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Received empty audio file")
        
        temp_audio.write(content)
        temp_audio.flush()
        temp_audio.close()
        
        logger.info(f"Saved audio to: {temp_audio.name}")
        
        # Step 1: VAD - Check if audio has speech
        logger.info("Step 1: VAD - Checking for speech...")
        has_voice, speech_duration = has_speech(temp_audio.name, threshold=0.5)
        logger.info(f"VAD result: has_speech={has_voice}, duration={speech_duration:.2f}s")
        
        if not has_voice or speech_duration < 0.3:
            raise HTTPException(
                status_code=400, 
                detail="No speech detected in audio. Please speak clearly and try again."
            )
        
        # Step 2: Clean audio (remove silence)
        logger.info("Step 2: Cleaning audio (removing silence)...")
        cleaned_audio = clean_audio(temp_audio.name)
        audio_to_transcribe = cleaned_audio if cleaned_audio else temp_audio.name
        logger.info(f"Audio cleaned: {audio_to_transcribe}")
        
        # Step 3: Transcribe cleaned audio
        logger.info("Step 3: Transcribing cleaned audio...")
        user_text = await transcribe_audio(audio_to_transcribe, MODE)
        logger.info(f"User said: {user_text}")
        
        if not user_text or len(user_text.strip()) < 2:
            raise HTTPException(
                status_code=400,
                detail="Could not transcribe speech. Please try again."
            )
        
        # Step 4: Get LLM response
        logger.info("Step 4: Getting LLM response...")
        reply_text = await chat_with_llm(user_text)
        logger.info(f"LLM replied: {reply_text}")
        
        # Step 5: Convert reply to speech
        logger.info("Step 5: Generating speech...")
        output_audio = await text_to_speech(reply_text, MODE)
        
        # Encode reply text for safe HTTP header transmission
        reply_text_encoded = base64.b64encode(reply_text.encode('utf-8')).decode('ascii')
        user_text_encoded = base64.b64encode(user_text.encode('utf-8')).decode('ascii')
        
        # Return both text and audio
        return FileResponse(
            output_audio,
            media_type="audio/wav",
            filename="reply.wav",
            headers={
                "Content-Disposition": "attachment; filename=reply.wav",
                "X-Reply-Text": reply_text_encoded,
                "X-User-Text": user_text_encoded,
                "X-Speech-Duration": str(speech_duration),
                "X-Reply-Text-Encoding": "base64",
                "X-VAD-Enabled": "true"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VAD voice chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup
        if temp_audio and os.path.exists(temp_audio.name):
            try:
                os.unlink(temp_audio.name)
            except:
                pass
        if cleaned_audio and cleaned_audio != temp_audio.name and os.path.exists(cleaned_audio):
            try:
                os.unlink(cleaned_audio)
            except:
                pass


# Endpoint 7: Streaming VAD Chat with Voice Cloning and Chunked TTS (SSE)
@app.post("/vad-chat-voice-stream")
async def vad_chat_voice_stream(
    audio: UploadFile = File(...),
    voice_mode: str = Form("real-time"),  # "real-time" or "inference"
    reference_voice_id: str = Form(None),  # Optional reference voice ID for inference mode
    allow_interruption: str = Form("true")  # "true" or "false" for VAD interruption
):
    """
    🚀 STREAMING conversation endpoint using Server-Sent Events (SSE).
    
    ⭐ FEATURES:
    1. Uses user's voice as reference for TTS cloning (real-time mode)
    2. Uses pre-recorded reference voice for TTS (inference mode)
    3. Streams transcription progressively  
    4. Chunks LLM response and streams TTS audio in 10-15 word pieces
    5. Sends word timestamps for real-time text highlighting
    6. Supports interruption detection via VAD
    
    Args:
        audio: Audio file containing user's speech
        voice_mode: "real-time" (use current audio) or "inference" (use reference voice)
        reference_voice_id: ID of reference voice to use (required for inference mode)
        allow_interruption: Whether to enable VAD-based interruption detection
        
    Returns:
        SSE stream with events:
        - vad_start/complete: Voice activity detection
        - transcription_complete: User's transcribed speech
        - llm_complete: AI's text response
        - tts_chunk: Audio chunk with text and word timestamps
        - interruption_detected: When user interrupts (if allow_interruption=true)
        - complete: Done
    """
    temp_audio_path = None
    cleaned_audio_path = None
    
    # Parse parameters
    voice_mode = voice_mode.lower()
    allow_interruption_bool = allow_interruption.lower() == "true"
    
    logger.info(f"🎙️ Voice mode: {voice_mode}, Allow interruption: {allow_interruption_bool}")
    
    async def generate_stream():
        nonlocal temp_audio_path, cleaned_audio_path
        
        try:
            # Detect file extension
            file_ext = ".webm"
            if audio.content_type:
                logger.info(f"📥 SSE Stream: Received audio type: {audio.content_type}")
                if "wav" in audio.content_type:
                    file_ext = ".wav"
                elif "mp3" in audio.content_type:
                    file_ext = ".mp3"
                elif "webm" in audio.content_type:
                    file_ext = ".webm"
            
            # Save uploaded audio
            temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
            content = await audio.read()
            logger.info(f"📊 Received {len(content)} bytes")
            
            if len(content) == 0:
                yield f"event: error\ndata: {json.dumps({'error': 'Empty audio file'})}\n\n"
                return
            
            temp_audio_file.write(content)
            temp_audio_file.flush()
            temp_audio_file.close()
            temp_audio_path = temp_audio_file.name
            
            # Step 1: VAD Check
            yield f"event: vad_start\ndata: {json.dumps({'message': 'Checking for speech...'})}\n\n"
            
            has_voice, speech_duration = has_speech(temp_audio_path, threshold=0.5)
            logger.info(f"🎤 VAD: speech={has_voice}, duration={speech_duration:.2f}s")
            
            if not has_voice or speech_duration < 0.3:
                yield f"event: error\ndata: {json.dumps({'error': 'No speech detected in audio'})}\n\n"
                return
            
            yield f"event: vad_complete\ndata: {json.dumps({'has_speech': True, 'duration': round(speech_duration, 2)})}\n\n"
            
            # Step 2: Clean Audio
            yield f"event: audio_processing\ndata: {json.dumps({'message': 'Cleaning audio...'})}\n\n"
            cleaned_audio_path = clean_audio(temp_audio_path)
            audio_to_use = cleaned_audio_path if cleaned_audio_path else temp_audio_path
            
            # Step 3: Transcription
            yield f"event: transcription_start\ndata: {json.dumps({'message': 'Transcribing your speech...'})}\n\n"
            
            user_text = await transcribe_audio(audio_to_use, MODE)
            logger.info(f"💬 User said: {user_text}")
            
            if not user_text or len(user_text.strip()) < 2:
                yield f"event: error\ndata: {json.dumps({'error': 'Could not transcribe speech'})}\n\n"
                return
            
            yield f"event: transcription_complete\ndata: {json.dumps({'text': user_text})}\n\n"
            
            # Step 4: LLM Response
            yield f"event: llm_start\ndata: {json.dumps({'message': 'Thinking...'})}\n\n"
            
            reply_text = await chat_with_llm(user_text)
            logger.info(f"🤖 LLM replied: {reply_text[:100]}...")
            
            # DEBUG: Check if LLM is echoing user input
            if reply_text.strip().lower() == user_text.strip().lower():
                logger.error(f"⚠️ BUG DETECTED: LLM echoed user input!")
                logger.error(f"User: {user_text}")
                logger.error(f"LLM:  {reply_text}")
            
            yield f"event: llm_complete\ndata: {json.dumps({'text': reply_text})}\n\n"
            
            # Step 5: Determine reference voice for TTS
            reference_voice_path = None
            
            if voice_mode == "inference" and reference_voice_id:
                # Use pre-recorded reference voice
                for ext in ['.wav', '.mp3']:
                    ref_path = os.path.join(REFERENCE_VOICE_DIR, f"{reference_voice_id}{ext}")
                    if os.path.exists(ref_path):
                        reference_voice_path = ref_path
                        logger.info(f"🎙️ Using inference voice: {reference_voice_path}")
                        break
                
                if not reference_voice_path:
                    yield f"event: error\ndata: {json.dumps({'error': 'Reference voice not found'})}\n\n"
                    return
            else:
                # Use real-time voice (current audio)
                reference_voice_path = audio_to_use
                logger.info(f"🎤 Using real-time voice: {reference_voice_path}")
            
            # Step 6: Chunk text for streaming TTS
            yield f"event: tts_start\ndata: {json.dumps({'message': 'Generating speech...', 'voice_mode': voice_mode})}\n\n"
            
            # Chunk text into 10-15 word pieces for smooth streaming
            chunks = chunk_text_by_words(reply_text, min_words=10, max_words=15)
            logger.info(f"📦 Split into {len(chunks)} audio chunks")
            
            # Get word timestamps for highlighting
            word_timestamps = get_word_timestamps(reply_text, chunks)
            
            # Step 7: Generate and stream TTS for each chunk
            for chunk_idx, (chunk_text, start_char, end_char) in enumerate(chunks):
                logger.info(f"🎵 Chunk {chunk_idx + 1}/{len(chunks)}: '{chunk_text[:40]}...'")
                
                try:
                    # Generate audio for this chunk using selected reference voice
                    chunk_audio_path = await text_to_speech(
                        chunk_text, 
                        MODE, 
                        reference_audio_path=reference_voice_path
                    )
                    
                    # Read audio file and encode as base64
                    with open(chunk_audio_path, 'rb') as f:
                        audio_data = f.read()
                        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    
                    # Get words in this chunk for highlighting
                    chunk_words = [
                        w for w in word_timestamps 
                        if w['chunk_index'] == chunk_idx
                    ]
                    
                    # Send chunk with audio and word info for highlighting
                    chunk_data = {
                        'chunk_index': chunk_idx,
                        'total_chunks': len(chunks),
                        'text': chunk_text,
                        'audio': audio_base64,
                        'start_char': start_char,
                        'end_char': end_char,
                        'words': chunk_words,
                        'audio_format': 'wav',
                        'allow_interruption': allow_interruption_bool  # Send interruption flag
                    }
                    
                    yield f"event: tts_chunk\ndata: {json.dumps(chunk_data)}\n\n"
                    
                    # Cleanup chunk audio
                    try:
                        os.unlink(chunk_audio_path)
                    except:
                        pass
                    
                    # Small delay for smoother streaming
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    logger.error(f"❌ Error generating chunk {chunk_idx}: {e}")
                    yield f"event: tts_error\ndata: {json.dumps({'chunk_index': chunk_idx, 'error': str(e)})}\n\n"
            
            # All done!
            yield f"event: complete\ndata: {json.dumps({'message': 'Conversation complete', 'chunks_sent': len(chunks)})}\n\n"
            logger.info("✅ Streaming conversation complete")
            
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        
        finally:
            # Cleanup temp files
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.unlink(temp_audio_path)
                except Exception as e:
                    logger.warning(f"Could not delete temp audio: {e}")
            if cleaned_audio_path and os.path.exists(cleaned_audio_path):
                try:
                    os.unlink(cleaned_audio_path)
                except Exception as e:
                    logger.warning(f"Could not delete cleaned audio: {e}")
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# Endpoint 8: Real-time streaming transcription
@app.post("/transcribe-stream")
async def transcribe_stream(audio: UploadFile = File(...)):
    """
    Transcribe audio with streaming/progressive updates.
    Returns Server-Sent Events (SSE) stream with partial transcriptions.
    
    Args:
        audio: Audio file (WAV, MP3, WebM, etc.)
        
    Returns:
        Server-Sent Events stream with transcription progress
    """
    temp_audio = None
    
    try:
        # Detect file extension
        file_ext = ".webm"
        if audio.content_type:
            logger.info(f"Received audio with content type: {audio.content_type}")
            if "wav" in audio.content_type or "wave" in audio.content_type:
                file_ext = ".wav"
            elif "mp3" in audio.content_type:
                file_ext = ".mp3"
            elif "webm" in audio.content_type:
                file_ext = ".webm"
        
        # Save uploaded file
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        content = await audio.read()
        logger.info(f"Received {len(content)} bytes of audio data for streaming transcription")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Received empty audio file")
        
        temp_audio.write(content)
        temp_audio.flush()
        temp_audio.close()
        
        logger.info(f"Saved audio to: {temp_audio.name}")
        
        # Create streaming response
        async def event_generator():
            try:
                async for result in transcribe_streaming(temp_audio.name, MODE):
                    # Format as Server-Sent Event
                    event_data = json.dumps(result)
                    yield f"data: {event_data}\n\n"
                
                # Send final completion event
                yield f"data: {json.dumps({'status': 'done'})}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming transcription error: {e}")
                error_event = json.dumps({
                    "status": "error",
                    "error": str(e)
                })
                yield f"data: {error_event}\n\n"
            
            finally:
                # Cleanup
                if temp_audio and os.path.exists(temp_audio.name):
                    try:
                        os.unlink(temp_audio.name)
                    except:
                        pass
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming transcription setup error: {e}")
        # Cleanup if error occurs before streaming starts
        if temp_audio and os.path.exists(temp_audio.name):
            try:
                os.unlink(temp_audio.name)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint 9: Real-time chunk-based voice chat
@app.post("/chat-voice-stream")
async def chat_voice_stream(audio: UploadFile = File(...)):
    """
    Complete voice chat pipeline with REAL-TIME chunk-based transcription:
    1. Process audio in chunks as it transcribes (no waiting for complete file)
    2. Stream each word/phrase as it's transcribed
    3. Send final text to LLM
    4. Convert response to speech
    5. Return audio
    
    Args:
        audio: User's audio file
        
    Returns:
        Server-Sent Events stream with chunk-by-chunk transcription
    """
    output_audio = None
    
    try:
        # Read audio content
        content = await audio.read()
        logger.info(f"Received {len(content)} bytes for chunk-based streaming transcription")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Received empty audio file")
        
        # Create streaming response
        async def event_generator():
            user_text = ""
            reply_text = ""
            output_audio = None  # Initialize here
            
            try:
                # Phase 1: Real-time chunk-based transcription
                yield f"data: {json.dumps({'phase': 'transcription', 'status': 'started'})}\n\n"
                
                # Use configured transcription mode (parallel or sequential)
                if TRANSCRIPTION_MODE == "parallel":
                    logger.info("Using TRUE parallel processing with multiple Whisper models")
                    async for result in transcribe_audio_parallel(content, sample_rate=16000, chunk_duration=1.5):
                        result['phase'] = 'transcription'
                        yield f"data: {json.dumps(result)}\n\n"
                        
                        if result.get('status') == 'complete' and not result.get('partial'):
                            user_text = result.get('text', '')
                else:
                    # Use SIMPLE sequential method (basic transcribe_audio from stt.py)
                    logger.info("Using simple sequential transcription (basic method)")
                    
                    # Save audio to temp file for basic transcription
                    import tempfile
                    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                    temp_audio.write(content)
                    temp_audio.flush()
                    temp_audio.close()
                    
                    try:
                        # Send starting status
                        yield f"data: {json.dumps({'phase': 'transcription', 'status': 'transcribing', 'text': '', 'partial': True})}\n\n"
                        
                        # Use basic transcribe_audio (simple, no streaming)
                        user_text = await transcribe_audio(temp_audio.name, MODE)
                        
                        # Send complete status
                        yield f"data: {json.dumps({'phase': 'transcription', 'status': 'complete', 'text': user_text, 'partial': False})}\n\n"
                        
                    finally:
                        # Clean up temp file
                        if os.path.exists(temp_audio.name):
                            os.unlink(temp_audio.name)
                
                if not user_text:
                    raise Exception("No transcription received")
                
                logger.info(f"User said: {user_text}")
                
                # Phase 2: LLM processing
                yield f"data: {json.dumps({'phase': 'llm', 'status': 'started', 'user_text': user_text})}\n\n"
                
                reply_text = await chat_with_llm(user_text)
                logger.info(f"LLM replied: {reply_text}")
                
                yield f"data: {json.dumps({'phase': 'llm', 'status': 'complete', 'text': reply_text})}\n\n"
                
                # Phase 3: TTS generation
                yield f"data: {json.dumps({'phase': 'tts', 'status': 'started'})}\n\n"
                
                output_audio = await text_to_speech(reply_text, MODE)
                
                # Encode audio file to base64
                with open(output_audio, 'rb') as f:
                    audio_data = f.read()
                audio_base64 = base64.b64encode(audio_data).decode('ascii')
                
                yield f"data: {json.dumps({'phase': 'tts', 'status': 'complete', 'audio': audio_base64})}\n\n"
                
                # Final completion
                yield f"data: {json.dumps({'status': 'done'})}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming chat error: {e}")
                error_event = json.dumps({
                    "status": "error",
                    "error": str(e)
                })
                yield f"data: {error_event}\n\n"
            
            finally:
                # Cleanup output audio after sending
                if output_audio and os.path.exists(output_audio):
                    try:
                        await asyncio.sleep(2)
                        os.unlink(output_audio)
                    except:
                        pass
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming chat setup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# REFERENCE VOICE MANAGEMENT ENDPOINTS
# ============================================

@app.post("/upload-reference-voice")
async def upload_reference_voice(audio: UploadFile = File(...)):
    """
    Upload a reference voice for inference mode.
    Cleans the audio and stores it for later use.
    
    Args:
        audio: Audio file containing reference voice
        
    Returns:
        JSON with reference_voice_id and file path
    """
    try:
        # Detect file extension
        file_ext = ".wav"
        if audio.content_type:
            logger.info(f"📥 Received reference voice: {audio.content_type}")
            if "wav" in audio.content_type:
                file_ext = ".wav"
            elif "mp3" in audio.content_type:
                file_ext = ".mp3"
            elif "webm" in audio.content_type:
                file_ext = ".webm"
        
        # Save uploaded audio temporarily
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        content = await audio.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        temp_audio.write(content)
        temp_audio.flush()
        temp_audio.close()
        
        # Check for speech
        has_voice, speech_duration = has_speech(temp_audio.name, threshold=0.5)
        logger.info(f"Reference voice VAD: has_speech={has_voice}, duration={speech_duration:.2f}s")
        
        if not has_voice or speech_duration < 0.5:
            os.unlink(temp_audio.name)
            raise HTTPException(
                status_code=400,
                detail="No clear speech detected. Please record at least 1 second of clear speech."
            )
        
        # Clean the audio
        cleaned_audio_path = clean_audio(temp_audio.name)
        audio_to_save = cleaned_audio_path if cleaned_audio_path else temp_audio.name
        
        # Generate unique ID and save to reference directory
        import time
        reference_id = f"ref_{int(time.time())}"
        reference_path = os.path.join(REFERENCE_VOICE_DIR, f"{reference_id}.wav")
        
        # Copy to reference directory
        import shutil
        shutil.copy2(audio_to_save, reference_path)
        
        logger.info(f"✅ Reference voice saved: {reference_path}")
        
        # Cleanup temp files
        try:
            os.unlink(temp_audio.name)
            if cleaned_audio_path and cleaned_audio_path != temp_audio.name:
                os.unlink(cleaned_audio_path)
        except:
            pass
        
        return JSONResponse({
            "success": True,
            "reference_voice_id": reference_id,
            "reference_path": reference_path,
            "duration": round(speech_duration, 2),
            "message": "Reference voice uploaded successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reference voice upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list-reference-voices")
async def list_reference_voices():
    """
    List all available reference voices.
    
    Returns:
        JSON array of reference voice files
    """
    try:
        voices = []
        for filename in os.listdir(REFERENCE_VOICE_DIR):
            if filename.endswith(('.wav', '.mp3')):
                filepath = os.path.join(REFERENCE_VOICE_DIR, filename)
                voices.append({
                    "id": filename.replace('.wav', '').replace('.mp3', ''),
                    "filename": filename,
                    "path": filepath,
                    "size": os.path.getsize(filepath)
                })
        
        return JSONResponse({"voices": voices})
        
    except Exception as e:
        logger.error(f"List reference voices error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete-reference-voice/{reference_id}")
async def delete_reference_voice(reference_id: str):
    """
    Delete a reference voice by ID.
    
    Args:
        reference_id: ID of the reference voice to delete
        
    Returns:
        JSON with success status
    """
    try:
        # Find and delete the file
        for ext in ['.wav', '.mp3']:
            filepath = os.path.join(REFERENCE_VOICE_DIR, f"{reference_id}{ext}")
            if os.path.exists(filepath):
                os.unlink(filepath)
                logger.info(f"🗑️ Deleted reference voice: {filepath}")
                return JSONResponse({
                    "success": True,
                    "message": f"Reference voice {reference_id} deleted"
                })
        
        raise HTTPException(status_code=404, detail="Reference voice not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete reference voice error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audio/reference_voices/{filename}")
async def serve_reference_voice(filename: str):
    """
    Serve a reference voice audio file.
    
    Args:
        filename: Name of the audio file
        
    Returns:
        Audio file response
    """
    try:
        filepath = os.path.join(REFERENCE_VOICE_DIR, filename)
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            filepath,
            media_type="audio/wav",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Serve reference voice error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


