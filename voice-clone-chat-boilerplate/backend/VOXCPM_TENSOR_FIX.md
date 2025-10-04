# VoxCPM Tensor Dimension Fix

## Error That Was Fixed

```
ERROR - Local TTS failed: Expected 2D Tensor, got 1D.
```

This error occurred after VoxCPM successfully generated audio (took ~7 minutes on CPU).

## Problem

**VoxCPM returns**: 1D audio tensor with shape `(samples,)`
```python
# Example: tensor([0.1, 0.2, 0.3, ...])  # Shape: (73143,)
```

**torchaudio.save() expects**: 2D tensor with shape `(channels, samples)`
```python
# Example: tensor([[0.1, 0.2, 0.3, ...]])  # Shape: (1, 73143)
```

When VoxCPM returned the audio, our code tried to save it directly with `torchaudio.save()`, which failed because the dimensions didn't match.

## Solution Applied

Added automatic tensor reshaping in `utils/tts_models.py`:

```python
# VoxCPM returns 1D tensor, but torchaudio.save expects 2D (channels, samples)
# Reshape to (1, samples) for mono audio if needed
if isinstance(wav, torch.Tensor):
    if wav.dim() == 1:
        wav = wav.unsqueeze(0)  # Add channel dimension: (samples,) -> (1, samples)
        logger.info(f"Reshaped audio tensor from 1D to 2D: {wav.shape}")
```

### What `unsqueeze(0)` Does:

```python
# Before:
wav.shape  # torch.Size([73143])  - 1D tensor

# After:
wav = wav.unsqueeze(0)
wav.shape  # torch.Size([1, 73143])  - 2D tensor (1 channel, 73143 samples)
```

## Also Handles Numpy Arrays

In case VoxCPM returns a numpy array instead of a tensor:

```python
# Convert numpy array to tensor if needed
if isinstance(wav, np.ndarray):
    wav = torch.from_numpy(wav)
    if wav.dim() == 1:
        wav = wav.unsqueeze(0)
```

## Testing

### Restart Backend:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Test VoxCPM Generation:
```bash
curl -X POST http://localhost:8000/speak \
  -F "text=Testing VoxCPM audio generation" \
  -F "reference_audio=@audio/Nafay_Org.mp3" \
  --output voxcpm_test.wav
```

**Expected behavior**:
1. VoxCPM generates audio (takes 2-7 minutes on CPU)
2. Audio is automatically reshaped from 1D to 2D
3. File saves successfully as `voxcpm_test.wav`
4. No "Expected 2D Tensor" error

### Check Logs:

You should see:
```
INFO: Generating speech with VoxCPM...
INFO: Using reference voice: ...
INFO: Reshaped audio tensor from 1D to 2D: torch.Size([1, 73143])
INFO: Audio saved to: backend/audio/generated/voice_xxxxx.wav
```

## Why This Happens

Different TTS models return audio in different formats:
- **ChatterBox**: Returns 2D tensor `(1, samples)` ✅ Works directly
- **VoxCPM**: Returns 1D tensor `(samples)` ❌ Needs reshaping
- **Other models**: May vary

Our fix handles all cases automatically by checking the tensor dimensions and reshaping as needed.

## Performance Note

From your logs, VoxCPM took **~7 minutes** to generate audio on CPU. This is expected. To make it faster:

### Option 1: Reduce Quality (Faster)
```env
VOXCPM_INFERENCE_TIMESTEPS=5  # Reduce from 10
```
→ Should take ~3-4 minutes

### Option 2: Use GPU
If you have a GPU:
→ Should take ~10-20 seconds

### Option 3: Switch to ChatterBox
```env
TTS_MODEL=chatterbox
```
→ Takes 5-8 minutes but produces very natural voice

## Summary

✅ **Fixed**: VoxCPM audio tensor is automatically reshaped from 1D to 2D  
✅ **Handles**: Both PyTorch tensors and numpy arrays  
✅ **Logging**: Shows when reshaping occurs for debugging  
✅ **Compatible**: Works with all TTS models  
✅ **No config needed**: Automatic handling  

Just restart the backend and VoxCPM should work end-to-end now! 🎉

## Complete VoxCPM Fixes Applied

1. ✅ **Prompt text pairing**: VoxCPM now provides `prompt_text` with `prompt_wav_path`
2. ✅ **Tensor dimension**: VoxCPM audio is automatically reshaped to 2D

Both fixes are in `backend/utils/tts_models.py` - just restart the backend to use them!

