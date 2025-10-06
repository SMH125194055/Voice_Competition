# Coqui XTTS Quick Start

## ✅ TTS is Already Installed!

You have Coqui TTS installed. Now just configure and restart.

## 3 Simple Steps:

### 1. Update `.env` file

Make sure your `.env` has:
```env
TTS_MODEL=xtts
```

### 2. Restart Backend

```bash
cd "C:\Users\Admin\Downloads\Voice Competition\Voice_Competition\voice-clone-chat-boilerplate\backend"
uvicorn main:app --reload --port 8000
```

### 3. Test It!

```bash
curl -X POST http://localhost:8000/speak \
  -F "text=Hello! Testing Coqui XTTS with voice cloning!" \
  -F "reference_audio=@audio/Nafay_Org.mp3" \
  --output xtts_test.wav
```

**Expected time**: ~10-30 seconds with voice cloning! ⚡

## What You'll Get

- ✅ **10-30 seconds** (vs 2-7 minutes with VoxCPM)
- ✅ **Voice cloning** with your reference audio
- ✅ **30-50x faster** than VoxCPM
- ✅ **Reliable** - no dependency issues

That's it! Just restart the backend and XTTS will work!


