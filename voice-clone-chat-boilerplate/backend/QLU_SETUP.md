# Qlu AI Integration Setup

This document describes the migration from OpenRouter to Qlu AI library for LLM integration.

## What Changed

### 1. **LLM Library**
- **Before**: Used OpenRouter API with OpenAI client
- **After**: Using Qlu AI library (`qutils`) for LLM integration

### 2. **Updated Files**

#### `requirements.txt`
- Added: `git+https://github.com/dnnaeinc/ai-Qlu2-library@development`
- All dependencies have been captured with exact versions from your virtual environment

#### `utils/llm.py`
- Completely rewritten to use `qutils.llm.asynchronous.invoke()` instead of OpenAI client
- Added support for Qlu-specific environment variables
- Added token usage logging
- Default model changed to: `openai/gpt-4.1-mini-2025-04-14`
- Added parameters:
  - `temperature` (default: 0.7)
  - `max_tokens` (default: 4096)

#### `.env` (newly created)
```bash
MODE=local
VOICE_CLONE_AUDIO=audio/Nafay_Org.mp3
WHISPER_MODEL=base

# Qlu AI Configuration
LLM_ENVIRONMENT=local
QLU_API_KEY=qlu_llm_key_CI4rnPXsJLtkZjv8:Zo6TRrTbhO668AzxqHrMiM-QOIGRdX2rAzYDYDK8uBk
LLM_PROXY_GATEWAY_URL=https://ai-api-llm-620091903831.us-central1.run.app/

# LLM Model Configuration
LLM_MODEL=openai/gpt-4.1-mini-2025-04-14
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096

# TTS Model Configuration
TTS_MODEL=fast
```

#### `env.template`
- Removed OpenRouter configuration (OPENAI_API_KEY, OPENAI_API_BASE)
- Added Qlu AI configuration variables
- Added LLM model configuration options

## Environment Variables

### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `QLU_API_KEY` | Your Qlu API key | `qlu_llm_key_CI4rnPXsJLtkZjv8:...` |
| `LLM_ENVIRONMENT` | Environment setting | `local` |
| `LLM_PROXY_GATEWAY_URL` | Qlu gateway URL | `https://ai-api-llm-620091903831.us-central1.run.app/` |

### Optional Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_MODEL` | Model to use | `openai/gpt-4.1-mini-2025-04-14` |
| `LLM_TEMPERATURE` | Response randomness (0-1) | `0.7` |
| `LLM_MAX_TOKENS` | Max response tokens | `4096` |

## How to Use

### 1. Install Dependencies
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Install/update packages
pip install -r requirements.txt
```

### 2. Configure Environment
- The `.env` file has been created with your Qlu credentials
- Modify if needed for different environments

### 3. Run the Backend
```bash
uvicorn main:app --reload --port 8000
```

### 4. Test the Integration
The `/chat` endpoint now uses Qlu AI:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

## API Changes

### `chat_with_llm()` Function
**New Signature:**
```python
async def chat_with_llm(
    message: str,
    model: str = "openai/gpt-4.1-mini-2025-04-14",
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> str
```

**Key Changes:**
- Now uses `qutils.llm.invoke()` internally
- Reads `QLU_API_KEY` instead of `OPENAI_API_KEY`
- Returns token usage information in logs
- Adds default system prompt for voice assistant if none provided

## Features

### Token Usage Tracking
The integration now logs token usage for each LLM call:
```
Token usage - Input: 45, Output: 123, Total: 168
```

### Error Handling
- Validates `QLU_API_KEY` is present
- Provides detailed error messages
- Logs all API interactions

### Default System Prompt
If no system prompt is provided, uses:
> "You are a helpful voice assistant. Provide clear, concise, and natural responses suitable for speech synthesis."

## Troubleshooting

### Error: "QLU_API_KEY not set in environment"
**Solution:** Ensure `.env` file exists in backend folder with correct credentials

### Error: "User not found" (401)
**Solution:** Verify your `QLU_API_KEY` is correct and has not expired

### Import Error: "No module named 'qutils'"
**Solution:** Reinstall the Qlu library:
```bash
pip install git+https://github.com/dnnaeinc/ai-Qlu2-library@development
```

## Migration Complete ✅

Your backend is now configured to use Qlu AI instead of OpenRouter. The error you were seeing (`Error code: 401 - {'error': {'message': 'User not found.'}}`) should be resolved with the correct Qlu API key.

## Next Steps

1. **Restart your backend server** to load the new configuration
2. **Test the `/chat` endpoint** to verify Qlu integration works
3. **Monitor token usage** in logs to track API usage
4. **Adjust model parameters** (temperature, max_tokens) if needed for your use case

