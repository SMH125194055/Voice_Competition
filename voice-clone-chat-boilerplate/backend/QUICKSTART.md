# Quick Start Guide

## 1. Setup Environment

### Create `.env` file
Copy the template and update with your credentials:

```bash
copy env.template .env    # Windows
# or
cp env.template .env      # Linux/Mac
```

Edit `.env` and add your OpenRouter API key:
```env
MODE=local
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_API_BASE=https://openrouter.ai/api/v1
VOICE_CLONE_AUDIO=audio/Nafay_Org.mp3
WHISPER_MODEL=base
```

### Install Dependencies

```bash
# Activate virtual environment if not already activated
venv\Scripts\activate        # Windows
# or
source venv/bin/activate     # Linux/Mac

# Install packages
pip install -r requirements.txt
```

> **Note**: Installation may take 5-10 minutes due to PyTorch and model dependencies.

## 2. Run the Server

```bash
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

## 3. Test the API

### Option A: Quick Test with curl

```bash
# Test health check
curl http://localhost:8000/

# Test chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello, tell me a joke\"}"
```

### Option B: Run Test Suite

```bash
python test_api.py
```

### Option C: Interactive API Docs

Open your browser and visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 4. Common Issues

### Issue: Whisper model download is slow
**Solution**: First run will download the model (~100MB for base). Be patient or use a smaller model:
```env
WHISPER_MODEL=tiny
```

### Issue: ChatterBox model not loading
**Solution**: 
1. Check if ChatterBox is properly installed in `Chatterbox-gitclone/`
2. Try API mode first to test other functionality:
```env
MODE=api
```

### Issue: OpenRouter API errors
**Solution**: Verify your API key is correct and has credits at https://openrouter.ai

### Issue: Out of memory
**Solution**: Use smaller models or API mode:
```env
WHISPER_MODEL=tiny
MODE=api
```

## 5. Mode Comparison

| Feature | Local Mode | API Mode |
|---------|-----------|----------|
| **Setup** | Complex (models need to download) | Simple (just API key) |
| **Cost** | Free (after setup) | Pay per use |
| **Speed** | Fast with GPU, slow with CPU | Depends on API |
| **Privacy** | Data stays local | Data sent to API |
| **Voice Clone** | Yes (custom voice) | Limited |

## 6. Next Steps

- Test all endpoints with the test script
- Customize the voice clone by changing `VOICE_CLONE_AUDIO`
- Integrate with the frontend (React app in `frontend/voice-ui/`)
- Add conversation history and memory
- Implement user authentication
- Add error handling and retries

## Need Help?

Check the full README.md for detailed documentation.


