# Quick Model Switch Guide

## TL;DR - Switch TTS Models in 3 Steps

### To Use ChatterBox:
```bash
# 1. Edit .env
echo "TTS_MODEL=chatterbox" >> .env

# 2. Restart backend
uvicorn main:app --reload --port 8000

# 3. Verify
curl http://localhost:8000/ | grep tts_model
# Should show: "tts_model": "chatterbox"
```

### To Use VoxCPM:
```bash
# 1. Install VoxCPM (first time only)
pip install git+https://github.com/OpenBMB/VoxCPM.git soundfile

# 2. Edit .env
echo "TTS_MODEL=voxcpm" >> .env

# 3. Restart backend
uvicorn main:app --reload --port 8000

# 4. Verify
curl http://localhost:8000/ | grep tts_model
# Should show: "tts_model": "voxcpm"
```

## Complete .env Examples

### Example 1: ChatterBox (Default)
```env
MODE=local
OPENAI_API_KEY=your-key
OPENAI_API_BASE=https://openrouter.ai/api/v1
VOICE_CLONE_AUDIO=audio/Nafay_Org.mp3
WHISPER_MODEL=base
TTS_MODEL=chatterbox
```

### Example 2: VoxCPM (Fast)
```env
MODE=local
OPENAI_API_KEY=your-key
OPENAI_API_BASE=https://openrouter.ai/api/v1
VOICE_CLONE_AUDIO=audio/Nafay_Org.mp3
WHISPER_MODEL=base

# VoxCPM Configuration
TTS_MODEL=voxcpm
VOXCPM_MODEL_PATH=VoxCPM-0.5B
VOXCPM_CFG_VALUE=2.0
VOXCPM_INFERENCE_TIMESTEPS=10
VOXCPM_NORMALIZE=true
VOXCPM_DENOISE=true
VOXCPM_RETRY_BADCASE=true
```

## What Each Model is Best For

| Use Case | Recommended Model | Why |
|----------|------------------|-----|
| Best quality | ChatterBox | Most natural voice cloning |
| Fastest generation | VoxCPM (fast settings) | 2-3x faster than ChatterBox |
| Strong expressiveness | VoxCPM | Highly expressive speech |
| GPU available | VoxCPM | Faster on GPU |
| CPU only | VoxCPM | Still faster than ChatterBox on CPU |
| Natural prosody | ChatterBox | Best for natural-sounding speech |

## Quick Performance Test

### Test ChatterBox Speed:
```bash
# .env: TTS_MODEL=chatterbox
time curl -X POST http://localhost:8000/speak \
  -F "text=This is a performance test" \
  --output test.wav
```

### Test VoxCPM Speed:
```bash
# .env: TTS_MODEL=voxcpm
time curl -X POST http://localhost:8000/speak \
  -F "text=This is a performance test" \
  --output test.wav
```

Compare the times!

## Troubleshooting in 30 Seconds

### Model not switching?
```bash
# 1. Check .env file
cat .env | grep TTS_MODEL

# 2. Restart backend (kill and restart)
pkill -f uvicorn
uvicorn main:app --reload --port 8000

# 3. Verify
curl http://localhost:8000/ | grep tts_model
```

### VoxCPM not working?
```bash
# Install it
pip install git+https://github.com/OpenBMB/VoxCPM.git

# Check model files exist
ls VoxCPM-0.5B/
# Should see: config.json, pytorch_model.bin, etc.
```

### Still stuck?
Check the logs when starting backend - they'll tell you which model loaded:
```
INFO: Loading ChatterBox TTS model on cpu...
# or
INFO: Loading VoxCPM TTS model from VoxCPM-0.5B on cpu...
```

## That's It!

**Switch models** = Edit 1 line in `.env` + Restart backend

No code changes. No complicated setup. Just configuration.

For detailed docs:
- **`TTS_MODEL_GUIDE.md`** - Full configuration guide
- **`VOXCPM_SETUP.md`** - VoxCPM installation
- **`MODULAR_TTS_SUMMARY.md`** - Architecture details





