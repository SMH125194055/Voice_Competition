# TTS Model Configuration Guide

## Overview

The backend now supports **multiple TTS models** with easy switching via configuration. This modular design allows you to:
- Switch between different TTS models (ChatterBox, VoxCPM, etc.)
- Add new TTS models easily
- Configure model-specific parameters
- Use different models for different use cases

## Currently Supported Models

### 1. **ChatterBox** (Default)
- **Description**: High-quality multilingual TTS with voice cloning
- **Speed**: Slower (5-8 minutes on CPU)
- **Quality**: Excellent
- **Voice Cloning**: Yes, with reference audio
- **Best For**: High-quality voice cloning with natural prosody

### 2. **VoxCPM**
- **Description**: Fast, expressive TTS model from ModelBest
- **Speed**: Faster than ChatterBox
- **Quality**: Excellent with expressive speech
- **Voice Cloning**: Yes, with prompt audio
- **Best For**: Faster generation with controllable expressiveness

## Configuration

### Step 1: Update `.env` File

Create or edit your `.env` file in the `backend/` directory:

```env
MODE=local
OPENAI_API_KEY=sk-xxxxxxx
OPENAI_API_BASE=https://openrouter.ai/api/v1
VOICE_CLONE_AUDIO=audio/Nafay_Org.mp3
WHISPER_MODEL=base

# TTS Model Selection
# Options: chatterbox, voxcpm
TTS_MODEL=chatterbox

# VoxCPM specific settings (only used if TTS_MODEL=voxcpm)
VOXCPM_MODEL_PATH=VoxCPM-0.5B
VOXCPM_CFG_VALUE=2.0
VOXCPM_INFERENCE_TIMESTEPS=10
VOXCPM_NORMALIZE=true
VOXCPM_DENOISE=true
VOXCPM_RETRY_BADCASE=true
```

### Step 2: Switch Models

To use **ChatterBox** (default):
```env
TTS_MODEL=chatterbox
```

To use **VoxCPM**:
```env
TTS_MODEL=voxcpm
```

### Step 3: Restart Backend

After changing the TTS model, restart the backend:
```bash
cd backend
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

uvicorn main:app --reload --port 8000
```

## VoxCPM Installation

### If VoxCPM is not installed:

1. **Install VoxCPM package**:
   ```bash
   pip install git+https://github.com/OpenBMB/VoxCPM.git
   # or
   pip install voxcpm
   ```

2. **Download VoxCPM model**:
   The model should be in `backend/VoxCPM-0.5B/` directory, or you can specify a different path:
   ```env
   VOXCPM_MODEL_PATH=path/to/your/VoxCPM-0.5B
   ```

3. **Or use HuggingFace**:
   ```env
   VOXCPM_MODEL_PATH=openbmb/VoxCPM-0.5B
   ```
   The model will be downloaded automatically from HuggingFace on first use.

## VoxCPM Parameters Explained

### `VOXCPM_CFG_VALUE` (default: 2.0)
- **Range**: 1.0 - 5.0
- **Lower (1.0-2.0)**: More diverse, natural speech
- **Higher (3.0-5.0)**: Better adherence to prompt voice, but may sound less natural
- **Recommended**: Start with 2.0, increase if voice cloning isn't strong enough

### `VOXCPM_INFERENCE_TIMESTEPS` (default: 10)
- **Range**: 5 - 50
- **Lower (5-10)**: Faster generation, slightly lower quality
- **Higher (20-50)**: Better quality, slower generation
- **Recommended**: 10 for balanced speed/quality, 20 for best quality

### `VOXCPM_NORMALIZE` (default: true)
- **true**: Apply text normalization (converts "Dr." to "Doctor", etc.)
- **false**: Use text as-is
- **Recommended**: true for most use cases

### `VOXCPM_DENOISE` (default: true)
- **true**: Apply denoising to generated audio
- **false**: No post-processing
- **Recommended**: true for cleaner audio

### `VOXCPM_RETRY_BADCASE` (default: true)
- **true**: Automatically retry if generation fails or produces bad output
- **false**: No retry
- **Recommended**: true to handle edge cases

## Comparing Models

| Feature | ChatterBox | VoxCPM |
|---------|-----------|---------|
| **Speed (CPU)** | ~5-8 min | ~2-4 min |
| **Speed (GPU)** | ~30-60 sec | ~10-20 sec |
| **Quality** | Excellent | Excellent |
| **Voice Cloning** | Yes | Yes |
| **Expressiveness** | High | Very High |
| **Configuration** | Simple | More options |
| **Memory Usage** | ~4GB | ~2GB |
| **Best For** | Natural voice cloning | Fast, expressive speech |

## Checking Current Model

Visit http://localhost:8000/ to see which model is currently loaded:

```json
{
  "status": "running",
  "mode": "local",
  "tts_model": "chatterbox",
  "tts_device": "cpu",
  "available_tts_models": ["chatterbox", "voxcpm"],
  "endpoints": [...]
}
```

## Performance Tips

### For ChatterBox:
1. **Use GPU**: Set device to CUDA for 10-15x speedup
2. **Shorter text**: Break long responses into chunks
3. **Pre-warm**: First generation is slower

### For VoxCPM:
1. **Lower timesteps**: Use 5-8 for faster generation
2. **Reduce CFG**: Lower to 1.5 for faster (less accurate voice cloning)
3. **Disable denoise**: Set to false for slight speedup
4. **Use GPU**: Significant speedup on CUDA

## Troubleshooting

### Error: "Unknown TTS model: xxx"
**Solution**: Check `TTS_MODEL` in `.env` file. Must be one of: `chatterbox`, `voxcpm`

### Error: "Failed to load VoxCPM model"
**Solutions**:
1. Install VoxCPM: `pip install voxcpm`
2. Check model path in `.env`
3. Download model from HuggingFace: https://huggingface.co/openbmb/VoxCPM-0.5B

### Error: "VoxCPM generates unstoppable audio"
**Solution**: This is a known issue. Enable `VOXCPM_RETRY_BADCASE=true` to auto-retry

### ChatterBox is too slow
**Solutions**:
1. Switch to VoxCPM: `TTS_MODEL=voxcpm`
2. Use GPU if available
3. Use API mode instead

### VoxCPM voice cloning not strong enough
**Solutions**:
1. Increase `VOXCPM_CFG_VALUE` to 3.0 or 3.5
2. Use longer reference audio (5-10 seconds)
3. Ensure reference audio is clear and high quality

## Adding Your Own TTS Model

The architecture is extensible! To add a new model:

### 1. Create Model Class

Edit `backend/utils/tts_models.py`:

```python
class MyCustomTTS(TTSModelBase):
    """Your custom TTS implementation."""
    
    def load_model(self):
        """Load your model here."""
        # Your initialization code
        pass
    
    def generate(self, text: str, reference_audio_path: Optional[str] = None) -> tuple:
        """Generate speech."""
        # Your generation code
        # Return (audio_tensor, sample_rate)
        pass
    
    def get_sample_rate(self) -> int:
        """Return sample rate."""
        return 16000
```

### 2. Register Model

In `tts_models.py`, add to factory:

```python
class TTSModelFactory:
    _models = {
        "chatterbox": ChatterBoxTTS,
        "voxcpm": VoxCPMTTS,
        "mycustom": MyCustomTTS,  # Add your model
    }
```

### 3. Use in Configuration

```env
TTS_MODEL=mycustom
```

## Example Configurations

### Fast Response (Lower Quality)
```env
TTS_MODEL=voxcpm
VOXCPM_CFG_VALUE=1.5
VOXCPM_INFERENCE_TIMESTEPS=5
VOXCPM_DENOISE=false
```

### Best Quality (Slower)
```env
TTS_MODEL=voxcpm
VOXCPM_CFG_VALUE=2.5
VOXCPM_INFERENCE_TIMESTEPS=20
VOXCPM_DENOISE=true
```

### Strong Voice Cloning
```env
TTS_MODEL=voxcpm
VOXCPM_CFG_VALUE=3.5
VOXCPM_INFERENCE_TIMESTEPS=15
```

### Balanced (Recommended)
```env
TTS_MODEL=voxcpm
VOXCPM_CFG_VALUE=2.0
VOXCPM_INFERENCE_TIMESTEPS=10
VOXCPM_NORMALIZE=true
VOXCPM_DENOISE=true
```

## API Reference

### Check Current Model
```python
from utils import get_current_model_info

info = get_current_model_info()
# Returns: {"model": "voxcpm", "device": "cuda", "sample_rate": 16000, "status": "ready"}
```

### List Available Models
```python
from utils import list_available_models

models = list_available_models()
# Returns: ["chatterbox", "voxcpm"]
```

## Summary

✅ **Easy switching** between TTS models via `.env` file  
✅ **Model-specific configuration** for fine-tuning  
✅ **Extensible architecture** for adding new models  
✅ **No code changes** required to switch models  
✅ **Backward compatible** with existing setup  

Just change `TTS_MODEL` in your `.env` file and restart the backend!

