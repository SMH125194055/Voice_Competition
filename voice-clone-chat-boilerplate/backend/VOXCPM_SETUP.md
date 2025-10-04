# VoxCPM Setup Guide

## Quick Start

Follow these steps to use VoxCPM as your TTS model.

### Step 1: Install VoxCPM Dependencies

#### Option A: Install from PyPI (if available)
```bash
cd backend
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

pip install voxcpm soundfile
```

#### Option B: Install from GitHub
```bash
cd backend
.\venv\Scripts\activate

pip install git+https://github.com/OpenBMB/VoxCPM.git soundfile
```

### Step 2: Verify VoxCPM Model Location

Your VoxCPM model should be in:
```
backend/VoxCPM-0.5B/
├── config.json
├── pytorch_model.bin
├── audiovae.pth
├── special_tokens_map.json
└── ... (other files)
```

If not, download from HuggingFace:
```bash
# Option 1: Use git-lfs
cd backend
git lfs install
git clone https://huggingface.co/openbmb/VoxCPM-0.5B

# Option 2: Use huggingface-cli
pip install huggingface-hub
huggingface-cli download openbmb/VoxCPM-0.5B --local-dir VoxCPM-0.5B
```

### Step 3: Update `.env` File

Create or edit `backend/.env`:

```env
MODE=local
OPENAI_API_KEY=your-key-here
OPENAI_API_BASE=https://openrouter.ai/api/v1
VOICE_CLONE_AUDIO=audio/Nafay_Org.mp3
WHISPER_MODEL=base

# ===== TTS Model Configuration =====
# Switch to VoxCPM
TTS_MODEL=voxcpm

# VoxCPM Settings
VOXCPM_MODEL_PATH=VoxCPM-0.5B
VOXCPM_CFG_VALUE=2.0
VOXCPM_INFERENCE_TIMESTEPS=10
VOXCPM_NORMALIZE=true
VOXCPM_DENOISE=true
VOXCPM_RETRY_BADCASE=true
```

### Step 4: Start Backend

```bash
cd backend
.\venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

### Step 5: Verify

Open http://localhost:8000/ in your browser. You should see:

```json
{
  "status": "running",
  "mode": "local",
  "tts_model": "voxcpm",
  "tts_device": "cuda",  // or "cpu"
  "available_tts_models": ["chatterbox", "voxcpm"],
  ...
}
```

If `tts_model` shows "voxcpm", you're ready to go!

## Troubleshooting

### Error: "No module named 'voxcpm'"

**Solution**:
```bash
cd backend
.\venv\Scripts\activate
pip install git+https://github.com/OpenBMB/VoxCPM.git
```

### Error: "Failed to load VoxCPM model"

**Check**:
1. Model files exist in `backend/VoxCPM-0.5B/`
2. Path in `.env` is correct: `VOXCPM_MODEL_PATH=VoxCPM-0.5B`
3. All required files are present:
   ```bash
   ls VoxCPM-0.5B/
   # Should show: config.json, pytorch_model.bin, audiovae.pth, etc.
   ```

### Error: "CUDA out of memory"

**Solutions**:
1. Use CPU instead (slower but works):
   - The backend will automatically use CPU if CUDA isn't available
   
2. Reduce memory usage:
   ```env
   VOXCPM_INFERENCE_TIMESTEPS=5  # Reduce from 10
   ```

3. Close other applications using GPU

### VoxCPM generates "unstoppable" audio

This is a known issue where the model generates audio that doesn't stop properly.

**Solution** (already enabled by default):
```env
VOXCPM_RETRY_BADCASE=true  # Auto-retry bad cases
```

If it still happens:
- Reduce `VOXCPM_CFG_VALUE` to 1.5-2.0
- Increase `inference_timesteps` to 15-20
- Use shorter text prompts

### Voice cloning not strong enough

**Solutions**:
1. **Increase CFG value**:
   ```env
   VOXCPM_CFG_VALUE=3.5  # Higher = stronger voice cloning
   ```

2. **Better reference audio**:
   - Use 5-10 seconds of clear speech
   - Avoid background noise
   - Single speaker only

3. **Increase quality**:
   ```env
   VOXCPM_INFERENCE_TIMESTEPS=20
   ```

### VoxCPM is slow on CPU

**Solutions**:

1. **Lower quality settings** (faster):
   ```env
   VOXCPM_INFERENCE_TIMESTEPS=5
   VOXCPM_CFG_VALUE=1.5
   VOXCPM_DENOISE=false
   ```

2. **Use GPU**: Much faster (10-20x speedup)

3. **Switch back to ChatterBox** (if needed):
   ```env
   TTS_MODEL=chatterbox
   ```

## Performance Comparison

### CPU (Intel i7/AMD Ryzen 7):
- **ChatterBox**: ~5-8 minutes per response
- **VoxCPM**: ~2-4 minutes per response
- **VoxCPM (fast settings)**: ~1-2 minutes

### GPU (NVIDIA RTX 3060+):
- **ChatterBox**: ~30-60 seconds
- **VoxCPM**: ~10-20 seconds
- **VoxCPM (fast settings)**: ~5-10 seconds

## Recommended Settings

### Balanced (Default):
```env
VOXCPM_CFG_VALUE=2.0
VOXCPM_INFERENCE_TIMESTEPS=10
VOXCPM_NORMALIZE=true
VOXCPM_DENOISE=true
```
- Good quality
- Reasonable speed
- Good voice cloning

### Fast Mode:
```env
VOXCPM_CFG_VALUE=1.5
VOXCPM_INFERENCE_TIMESTEPS=5
VOXCPM_NORMALIZE=true
VOXCPM_DENOISE=false
```
- 2x faster
- Slightly lower quality
- Weaker voice cloning

### Best Quality:
```env
VOXCPM_CFG_VALUE=2.5
VOXCPM_INFERENCE_TIMESTEPS=20
VOXCPM_NORMALIZE=true
VOXCPM_DENOISE=true
```
- Best quality
- Slower (2x slower)
- Stronger voice cloning

### Strong Voice Cloning:
```env
VOXCPM_CFG_VALUE=3.5
VOXCPM_INFERENCE_TIMESTEPS=15
VOXCPM_NORMALIZE=true
VOXCPM_DENOISE=true
```
- Very strong voice cloning
- May sound slightly robotic
- Good for distinctive voices

## Switching Between Models

To switch back to ChatterBox:
```env
TTS_MODEL=chatterbox
```

To switch to VoxCPM:
```env
TTS_MODEL=voxcpm
```

**Important**: Restart the backend after changing `TTS_MODEL`!

## Testing VoxCPM

### Test with curl:

```bash
# Simple test
curl -X POST http://localhost:8000/speak \
  -F "text=Hello, this is a test of VoxCPM voice synthesis" \
  --output test_voxcpm.wav

# With reference audio
curl -X POST http://localhost:8000/speak \
  -F "text=Hello, this is a test with voice cloning" \
  -F "reference_audio=@audio/Nafay_Org.mp3" \
  --output test_voxcpm_cloned.wav
```

### Test with Python:

```python
import requests

# Test speak endpoint
response = requests.post(
    "http://localhost:8000/speak",
    data={"text": "Hello from VoxCPM!"}
)

with open("test_voxcpm.wav", "wb") as f:
    f.write(response.content)

print("Generated: test_voxcpm.wav")
```

## FAQ

### Q: Can I use both ChatterBox and VoxCPM?
**A**: Not simultaneously. You need to restart the backend to switch models. The active model is loaded at startup.

### Q: Which model is better?
**A**: 
- **ChatterBox**: Better for natural, expressive voice cloning
- **VoxCPM**: Faster with good quality and expressiveness
- Try both and see which you prefer!

### Q: Can I use VoxCPM without voice cloning?
**A**: Yes! Just don't provide a reference audio:
```python
# No reference_audio parameter = default voice
response = requests.post(
    "http://localhost:8000/speak",
    data={"text": "Hello!"}
)
```

### Q: How much VRAM does VoxCPM need?
**A**: 
- **Minimum**: ~2GB
- **Recommended**: ~4GB
- **With batch processing**: ~6GB

### Q: Can I run VoxCPM on Mac M1/M2?
**A**: Yes! It will use MPS (Metal Performance Shaders) automatically if available.

## Summary

1. ✅ Install VoxCPM: `pip install git+https://github.com/OpenBMB/VoxCPM.git`
2. ✅ Download model to `backend/VoxCPM-0.5B/`
3. ✅ Set `TTS_MODEL=voxcpm` in `.env`
4. ✅ Configure parameters (or use defaults)
5. ✅ Restart backend
6. ✅ Test at http://localhost:8000/

For more details, see `TTS_MODEL_GUIDE.md`.

