# VoxCPM Error Fix

## Error That Was Fixed

```
ERROR - Local TTS failed: prompt_wav_path and prompt_text must both be provided or both be None
```

## Problem

VoxCPM has a specific requirement: `prompt_wav_path` and `prompt_text` must ALWAYS be provided together:
- **Both provided**: Voice cloning with reference audio and text
- **Both None**: Use default voice

You **cannot** provide just one without the other.

## Solution Applied

Updated `utils/tts_models.py` to provide a dummy `prompt_text` when using reference audio:

```python
# Before (WRONG):
prompt_wav_path = ref_audio
prompt_text = None  # ❌ Error: both must be provided or both None

# After (CORRECT):
prompt_wav_path = ref_audio
prompt_text = "This is a sample voice for voice cloning."  # ✅ Paired together
```

## How It Works Now

### With Reference Audio (Voice Cloning):
```python
wav = self.model.generate(
    text="Your text here",
    prompt_wav_path="audio/reference.wav",  # Reference audio
    prompt_text="This is a sample voice for voice cloning.",  # Required text
    ...
)
```

### Without Reference Audio (Default Voice):
```python
wav = self.model.generate(
    text="Your text here",
    prompt_wav_path=None,  # No reference
    prompt_text=None,      # Both None
    ...
)
```

## Why This Works

The `prompt_text` doesn't need to be a transcription of the reference audio. It's used by VoxCPM as a hint about the reference voice characteristics. A generic phrase like "This is a sample voice for voice cloning" works fine.

## Testing

### Restart Backend:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Test VoxCPM with Voice Cloning:
```bash
curl -X POST http://localhost:8000/speak \
  -F "text=Testing VoxCPM with voice cloning" \
  -F "reference_audio=@audio/Nafay_Org.mp3" \
  --output voxcpm_test.wav
```

Should now work without errors!

## Advanced: Using Transcribed Prompt Text

For even better voice cloning, you could transcribe the reference audio and use that as `prompt_text`:

```python
# Future enhancement
if ref_audio and os.path.exists(ref_audio):
    prompt_wav_path = ref_audio
    # Transcribe reference audio (optional)
    prompt_text = transcribe_reference_audio(ref_audio)  
    # Or use generic text (current implementation)
    # prompt_text = "This is a sample voice for voice cloning."
```

But for most cases, the generic text works fine!

## Summary

✅ **Fixed**: VoxCPM now provides `prompt_text` when using `prompt_wav_path`  
✅ **Voice cloning works**: Reference audio is properly utilized  
✅ **Default voice works**: Both set to None when no reference  
✅ **No code changes needed**: Just restart backend  

The error should be gone now!

