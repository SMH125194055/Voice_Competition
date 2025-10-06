# Coqui XTTS Installation Fix Summary

## Problem
Coqui XTTS had compatibility issues with newer versions of PyTorch and Transformers.

## Solution Applied
We downgraded the following packages to compatible versions:

```bash
# 1. Reinstalled TTS (force reinstall)
pip install --upgrade --force-reinstall --no-cache-dir TTS

# 2. Downgraded transformers (due to BeamSearchScorer import error)
pip install "transformers>=4.33.0,<4.45.0"

# 3. Downgraded PyTorch (due to weights_only security change in 2.8)
pip install "torch>=2.1,<2.6" "torchaudio>=2.1,<2.6"
```

## Current Versions
- **TTS**: 0.22.0
- **Transformers**: 4.44.2 (downgraded from 4.57.0)
- **PyTorch**: 2.5.1 (downgraded from 2.8.0)
- **TorchAudio**: 2.5.1 (downgraded from 2.8.0)

## Next Steps

### 1. Test XTTS Loading
```bash
cd "C:\Users\Admin\Downloads\Voice Competition\Voice_Competition\voice-clone-chat-boilerplate\backend"
.\venv\Scripts\python.exe test_xtts.py
```

**Expected Output:**
```
[OK] TTS library imported successfully
[OK] XTTS model loaded successfully!
[OK] Generated audio with X samples
SUCCESS! XTTS is working properly!
```

### 2. Restart the Backend
```bash
uvicorn main:app --reload --port 8000
```

**Watch for this in startup logs:**
```
INFO: Initializing TTS with model: xtts
INFO: Loading Coqui XTTS model on cpu...
INFO: Coqui XTTS model loaded successfully
INFO: XTTS supports voice cloning with reference audio
```

### 3. Verify via API
Visit: http://localhost:8000/

**Expected Response:**
```json
{
  "status": "running",
  "mode": "local",
  "tts_model": "xtts",
  "tts_device": "cpu",
  "available_tts_models": ["chatterbox", "voxcpm", "rvc", "fast", "xtts"]
}
```

### 4. Test Voice Generation
```bash
curl -X POST http://localhost:8000/speak \
  -F "text=Hello! Testing Coqui XTTS with voice cloning!" \
  -F "reference_audio=@audio/Nafay_Org.mp3" \
  --output xtts_test.wav
```

**Expected time:** 10-30 seconds

## Why These Versions?

1. **Transformers 4.44.2**: 
   - TTS 0.22.0 imports `BeamSearchScorer` which was removed in transformers 4.45+
   
2. **PyTorch 2.5.1**:
   - PyTorch 2.6+ changed `torch.load()` default from `weights_only=False` to `True`
   - TTS checkpoints contain class definitions that fail with `weights_only=True`
   - Version 2.5.1 is the latest stable before this security change

## Alternative: Use FastTTS (No Voice Cloning)

If XTTS still has issues, you can use the fast model (edge-tts, no cloning):

**In `.env`:**
```env
TTS_MODEL=fast
FAST_TTS_VOICE=en-US-GuyNeural
```

**Speed:** 2-3 seconds per response (but no voice cloning)

## Known Conflicts (Can be ignored)

The following dependency warnings are expected and can be ignored:
- `chatterbox-tts` version conflicts (we're using XTTS instead)
- `rvc-python` numpy conflict (only matters if using RVC)
- `datasets` fsspec conflict (not used)
- `funasr` hydra-core conflict (not used)

These won't affect XTTS functionality.


