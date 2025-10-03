# Voice Chat Backend

FastAPI backend for voice chat application with Speech-to-Text (Whisper), LLM (OpenRouter), and Text-to-Speech (ChatterBox) with voice cloning capabilities.

## Features

- **STT (Speech-to-Text)**: Whisper model (local or API)
- **LLM**: OpenRouter API for chat responses
- **TTS (Text-to-Speech)**: ChatterBox with voice cloning (local or API)
- **Modular Architecture**: Easy to switch between local and API modes

## Directory Structure

```
backend/
├── main.py                 # FastAPI application
├── utils/
│   ├── __init__.py
│   ├── stt.py             # Whisper STT module
│   ├── llm.py             # OpenRouter LLM module
│   └── tts.py             # ChatterBox TTS module
├── requirements.txt
├── env.template           # Environment variables template
└── audio/                 # Reference audio for voice cloning
```

## Setup

### 1. Create Virtual Environment (if not already activated)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `env.template` to `.env` and update with your values:

```env
MODE=local                                      # "local" or "api"
OPENAI_API_KEY=sk-your-openrouter-key-here    # Your OpenRouter API key
OPENAI_API_BASE=https://openrouter.ai/api/v1
VOICE_CLONE_AUDIO=audio/Nafay_Org.mp3         # Path to reference voice audio
WHISPER_MODEL=base                             # Whisper model size: tiny, base, small, medium, large
```

### 4. Run the Server

```bash
uvicorn main:app --reload --port 8000
```

Or:

```bash
python main.py
```

The server will start at `http://localhost:8000`

## API Endpoints

### 1. Health Check
```bash
GET /
```

### 2. Transcribe Audio to Text
```bash
POST /transcribe
Content-Type: multipart/form-data

# Example with curl
curl -X POST http://localhost:8000/transcribe \
  -F "audio=@test-audio.wav"

# Response
{
  "text": "transcribed text here"
}
```

### 3. Chat with LLM
```bash
POST /chat
Content-Type: application/json

# Example with curl
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'

# Response
{
  "reply": "I'm doing well, thank you! How can I help you today?"
}
```

### 4. Text to Speech
```bash
POST /speak
Content-Type: application/json

# Example with curl
curl -X POST http://localhost:8000/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test"}' \
  --output speech.wav

# Returns audio file (WAV)
```

### 5. Voice Chat (Full Pipeline)
```bash
POST /chat-voice
Content-Type: multipart/form-data

# Example with curl
curl -X POST http://localhost:8000/chat-voice \
  -F "audio=@user-audio.wav" \
  --output reply.wav

# This endpoint:
# 1. Transcribes the input audio
# 2. Sends the text to LLM
# 3. Converts LLM response to speech with cloned voice
# 4. Returns the audio file
# (Check X-Reply-Text header for the text response)
```

## Modes

### Local Mode (`MODE=local`)
- Whisper model runs locally (requires ~1-10GB RAM depending on model size)
- ChatterBox TTS runs locally with voice cloning
- Requires GPU for better performance (CPU works but slower)

### API Mode (`MODE=api`)
- Uses OpenAI Whisper API for transcription
- Uses OpenAI TTS API for speech synthesis
- Requires OPENAI_API_KEY

## Voice Cloning

To use voice cloning in local mode:

1. Place a reference audio file (WAV/MP3) in the `audio/` directory
2. Set `VOICE_CLONE_AUDIO` in `.env` to the file path
3. The TTS will clone the voice characteristics from this audio

## Testing

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# Test with audio files
curl -X POST http://localhost:8000/transcribe \
  -F "audio=@audio/test-english.wav"

curl -X POST http://localhost:8000/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a test"}' \
  --output test-output.wav
```

## Troubleshooting

### Whisper Model Not Loading
- Ensure you have enough RAM (2GB+ for base model)
- Try a smaller model: `WHISPER_MODEL=tiny`

### ChatterBox Model Not Loading
- Ensure PyTorch is installed correctly with GPU support
- Check CUDA/CUDNN if using GPU
- Try CPU mode (slower but works)

### API Errors
- Verify your `OPENAI_API_KEY` is correct
- Check OpenRouter credits/balance
- Ensure `OPENAI_API_BASE` is set correctly

## Dependencies

Main dependencies:
- FastAPI & Uvicorn
- OpenAI Python SDK
- Whisper (OpenAI)
- ChatterBox TTS
- PyTorch & Torchaudio

See `requirements.txt` for complete list.

## License

MIT


