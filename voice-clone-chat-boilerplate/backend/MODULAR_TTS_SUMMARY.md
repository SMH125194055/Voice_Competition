# Modular TTS System - Implementation Summary

## What Was Changed

The backend has been refactored to support **multiple TTS models** with easy configuration switching.

### Key Changes:

1. **Created `utils/tts_models.py`** - New modular TTS architecture
   - Base class `TTSModelBase` for all TTS models
   - `ChatterBoxTTS` implementation
   - `VoxCPMTTS` implementation
   - `TTSModelFactory` for creating model instances
   - Easy extension for future models

2. **Updated `utils/tts.py`** - Main TTS interface
   - Uses factory pattern to load models
   - Reads `TTS_MODEL` from environment
   - Model-agnostic API
   - Added `get_current_model_info()` and `list_available_models()`

3. **Updated `main.py`** - FastAPI application
   - Added model info to health check endpoint
   - Shows current TTS model and device
   - Lists all available models

4. **Updated `env.template`** - Configuration template
   - Added `TTS_MODEL` option (chatterbox/voxcpm)
   - Added VoxCPM-specific parameters
   - Clear documentation of options

5. **Updated `requirements.txt`** - Dependencies
   - Added comment for VoxCPM installation

6. **Created Documentation**:
   - `TTS_MODEL_GUIDE.md` - Complete guide for model configuration
   - `VOXCPM_SETUP.md` - VoxCPM-specific setup instructions
   - `MODULAR_TTS_SUMMARY.md` - This file

## Architecture Overview

```
┌─────────────────────────────────────────┐
│           FastAPI Backend               │
│         (main.py)                       │
└─────────────┬───────────────────────────┘
              │
              ├─ initialize_tts()
              ├─ text_to_speech()
              └─ get_current_model_info()
              │
┌─────────────▼───────────────────────────┐
│         utils/tts.py                    │
│   (Main TTS Interface)                  │
│   - Reads TTS_MODEL from .env           │
│   - Uses factory to create model        │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│       utils/tts_models.py               │
│   (TTS Model Implementations)           │
├─────────────────────────────────────────┤
│  TTSModelBase (Abstract)                │
│    ├─ load_model()                      │
│    ├─ generate()                        │
│    └─ get_sample_rate()                 │
├─────────────────────────────────────────┤
│  ChatterBoxTTS                          │
│    └─ Implements ChatterBox logic       │
├─────────────────────────────────────────┤
│  VoxCPMTTS                              │
│    └─ Implements VoxCPM logic           │
├─────────────────────────────────────────┤
│  TTSModelFactory                        │
│    └─ Creates model instances           │
└─────────────────────────────────────────┘
```

## How It Works

### 1. Configuration (`.env` file):
```env
TTS_MODEL=voxcpm  # or chatterbox
```

### 2. Initialization (on backend startup):
```python
# main.py
initialize_tts(MODE, VOICE_CLONE_AUDIO)
  ↓
# utils/tts.py
model_name = os.getenv("TTS_MODEL", "chatterbox")
tts_model = TTSModelFactory.create_model(model_name, ...)
tts_model.load_model()
```

### 3. Generation (when user requests audio):
```python
# main.py
await text_to_speech(text, MODE, reference_audio)
  ↓
# utils/tts.py
wav, sample_rate = tts_model.generate(text, reference_audio)
save_audio(wav, sample_rate)
```

## Benefits

### ✅ **Easy Model Switching**
Change one line in `.env` file, restart backend. No code changes needed.

### ✅ **Model-Specific Configuration**
Each model can have its own parameters (e.g., VoxCPM's CFG value, timesteps).

### ✅ **Extensible**
Adding a new TTS model is straightforward:
1. Create a class inheriting from `TTSModelBase`
2. Implement `load_model()`, `generate()`, `get_sample_rate()`
3. Register in `TTSModelFactory`

### ✅ **Backward Compatible**
Existing code continues to work. Default is ChatterBox if `TTS_MODEL` not specified.

### ✅ **Clean Separation**
- Business logic (main.py) doesn't know about specific models
- Model implementations are isolated
- Easy to test and maintain

## Usage Examples

### Check Current Model:
```bash
curl http://localhost:8000/
```

Response:
```json
{
  "status": "running",
  "mode": "local",
  "tts_model": "voxcpm",
  "tts_device": "cuda",
  "available_tts_models": ["chatterbox", "voxcpm"],
  "endpoints": [...]
}
```

### Switch to VoxCPM:
```env
# .env file
TTS_MODEL=voxcpm
VOXCPM_MODEL_PATH=VoxCPM-0.5B
VOXCPM_CFG_VALUE=2.0
VOXCPM_INFERENCE_TIMESTEPS=10
```

Restart backend:
```bash
uvicorn main:app --reload --port 8000
```

### Switch to ChatterBox:
```env
# .env file
TTS_MODEL=chatterbox
```

Restart backend.

## Adding a New Model (Example)

Let's say you want to add "CoquiTTS":

### Step 1: Create Model Class

Edit `utils/tts_models.py`:

```python
class CoquiTTS(TTSModelBase):
    """Coqui TTS implementation."""
    
    def load_model(self):
        from TTS.api import TTS
        self.model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
        logger.info("Coqui TTS loaded")
    
    def generate(self, text: str, reference_audio_path: Optional[str] = None) -> tuple:
        # Generate with Coqui
        wav = self.model.tts(text, speaker_wav=reference_audio_path)
        return torch.tensor(wav), 22050
    
    def get_sample_rate(self) -> int:
        return 22050
```

### Step 2: Register in Factory

In same file:

```python
class TTSModelFactory:
    _models = {
        "chatterbox": ChatterBoxTTS,
        "voxcpm": VoxCPMTTS,
        "coqui": CoquiTTS,  # ← Add this
    }
```

### Step 3: Use It

```env
TTS_MODEL=coqui
```

That's it! No changes to main.py or other files needed.

## Migration from Old System

### Old Code (utils/tts.py):
```python
chatterbox_model = ChatterboxTTS.from_pretrained(device=device)
wav = chatterbox_model.generate(text, audio_prompt_path=ref_audio)
```

### New Code (utils/tts.py):
```python
tts_model = TTSModelFactory.create_model(model_name, ...)
tts_model.load_model()
wav, sample_rate = tts_model.generate(text, ref_audio)
```

The interface is abstracted - same code works for any model!

## File Structure

```
backend/
├── main.py                      # FastAPI app (updated)
├── .env                         # Config file (add TTS_MODEL)
├── env.template                 # Template (updated)
├── requirements.txt             # Dependencies (updated)
├── utils/
│   ├── __init__.py             # Exports (updated)
│   ├── tts.py                  # Main TTS interface (refactored)
│   ├── tts_models.py           # NEW: Model implementations
│   ├── stt.py                  # Unchanged
│   └── llm.py                  # Unchanged
├── TTS_MODEL_GUIDE.md          # NEW: Complete guide
├── VOXCPM_SETUP.md             # NEW: VoxCPM setup
└── MODULAR_TTS_SUMMARY.md      # NEW: This file
```

## Testing

### 1. Test ChatterBox:
```bash
# .env
TTS_MODEL=chatterbox

# Start backend
uvicorn main:app --reload --port 8000

# Test
curl -X POST http://localhost:8000/speak \
  -F "text=Hello from ChatterBox" \
  --output chatterbox_test.wav
```

### 2. Test VoxCPM:
```bash
# .env
TTS_MODEL=voxcpm

# Restart backend
uvicorn main:app --reload --port 8000

# Test
curl -X POST http://localhost:8000/speak \
  -F "text=Hello from VoxCPM" \
  --output voxcpm_test.wav
```

### 3. Test Model Info:
```bash
curl http://localhost:8000/
# Should show current TTS model and available models
```

## Common Issues

### Issue: "Unknown TTS model: xxx"
**Cause**: Invalid `TTS_MODEL` in `.env`  
**Fix**: Use `chatterbox` or `voxcpm`

### Issue: Model not loading
**Cause**: Dependencies not installed  
**Fix**: 
- ChatterBox: Already cloned in `Chatterbox-gitclone/`
- VoxCPM: `pip install git+https://github.com/OpenBMB/VoxCPM.git`

### Issue: Wrong model loaded
**Cause**: `.env` not updated or backend not restarted  
**Fix**: Update `.env` and restart backend

## Performance Comparison

| Model | CPU Time | GPU Time | Quality | Voice Clone |
|-------|----------|----------|---------|-------------|
| ChatterBox | 5-8 min | 30-60s | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| VoxCPM | 2-4 min | 10-20s | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| VoxCPM (fast) | 1-2 min | 5-10s | ⭐⭐⭐⭐ | ⭐⭐⭐ |

## Future Enhancements

Possible additions:
1. **Model Caching**: Keep multiple models in memory
2. **Dynamic Switching**: Change model per request
3. **Model Ensembling**: Use multiple models together
4. **Streaming Generation**: Generate audio in chunks
5. **More Models**: Bark, StyleTTS, XTTS, etc.

The architecture is designed to support all of these!

## Summary

✅ **Modular architecture** with factory pattern  
✅ **Easy configuration** via `.env` file  
✅ **Multiple models** supported (ChatterBox, VoxCPM)  
✅ **Extensible design** for adding new models  
✅ **Backward compatible** with existing code  
✅ **Well documented** with guides and examples  

Just change `TTS_MODEL` in `.env` and restart!

For detailed setup instructions:
- See `TTS_MODEL_GUIDE.md` for complete configuration guide
- See `VOXCPM_SETUP.md` for VoxCPM-specific setup

