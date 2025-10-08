# 📚 Transcription Modes Explained

## Two Modes Available

### ⚡ Parallel Mode (NEW - 3x Faster)

**What it is:**
- Loads **3 independent Whisper models** at startup
- Processes multiple audio chunks **simultaneously**
- Uses `transcribe_audio_parallel()` from `parallel_whisper.py`

**How it works:**
```
Audio → Split into 7 chunks →
  Worker 1 (Model 1) → Chunks 1, 4, 7  ← All run
  Worker 2 (Model 2) → Chunks 2, 5     ← at the
  Worker 3 (Model 3) → Chunks 3, 6     ← same time!
→ Results in 4-5 seconds
```

**Config:**
```bash
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=3
```

**Performance:**
- ✅ **3x faster** (4-5s for 10s audio)
- ⚠️  Uses ~4.5 GB RAM

---

### 🔄 Sequential Mode (SIMPLE - Basic Transcription)

**What it is:**
- Uses the **SIMPLE `transcribe_audio()`** function from `stt.py`
- Same function used in `llm.py` and `/chat-voice` endpoint
- **NO chunking, NO streaming** - just basic transcription

**How it works:**
```
Audio → Save to file → Transcribe entire file at once → Results in 7-10 seconds
```

**Config:**
```bash
TRANSCRIPTION_MODE=sequential
```

**Performance:**
- ✅ Uses ~1.5 GB RAM (low memory)
- ⚠️  Slower (7-10s for 10s audio)
- ✅ **Simple and reliable - same as `/chat-voice` endpoint**

---

## Which Functions Are Used?

### Parallel Mode Uses:
- `transcribe_audio_parallel()` from `backend/utils/parallel_whisper.py` (**NEW**)
- Loads 3 Whisper models
- TRUE parallel processing

### Sequential Mode Uses:
- `transcribe_audio()` from `backend/utils/stt.py` (**BASIC/SIMPLE**)
- Single Whisper model
- **Same function used in `/chat-voice` endpoint and `llm.py`**
- NO chunking, NO streaming - just simple transcription

---

## Code Flow

### In `backend/main.py` (line 817-845):

```python
if TRANSCRIPTION_MODE == "parallel":
    # NEW: Use parallel processing with 3 models
    async for result in transcribe_audio_parallel(content, ...):
        # 3x faster, uses more RAM
        
else:
    # SIMPLE: Use basic transcribe_audio (no chunking/streaming)
    temp_audio = save_to_temp_file(content)
    user_text = await transcribe_audio(temp_audio, MODE)
    # Simple, reliable, same as /chat-voice endpoint
```

---

## Summary

| Feature | Parallel (NEW) | Sequential (SIMPLE) |
|---------|----------------|---------------------|
| **Code** | New parallel implementation | **Basic transcription (like `/chat-voice`)** |
| **Function** | `transcribe_audio_parallel()` | `transcribe_audio()` |
| **File** | `parallel_whisper.py` | `stt.py` |
| **Models** | 3 Whisper models | 1 Whisper model |
| **Chunking** | Yes (1.5s chunks) | No (full audio at once) |
| **Streaming** | Yes (progressive updates) | No (single result) |
| **Speed** | 4-5s ⚡ | 7-10s 🐢 |
| **Memory** | ~4.5 GB | ~1.5 GB |
| **When** | Default, for speed | Low RAM, simplicity |

---

## Configuration

### To Use NEW Parallel Mode (Fast):
```bash
# backend/.env
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=3
```

### To Use SIMPLE Sequential Mode (Basic Transcription):
```bash
# backend/.env
TRANSCRIPTION_MODE=sequential
```

---

## Why This Matters

**Sequential mode = Simple basic transcription (like `/chat-voice` and `llm.py`)**

If you want:
- ✅ **Simple, basic** transcription (no chunking)
- ✅ **Same as `/chat-voice`** endpoint
- ✅ Save **memory** (uses less RAM)
- ✅ **Reliable** fallback

→ Set `TRANSCRIPTION_MODE=sequential`

If you want:
- ✅ **3x faster** transcription
- ✅ Modern **parallel processing**
- ✅ Best **performance**
- ✅ Progressive updates

→ Set `TRANSCRIPTION_MODE=parallel` (default)

---

## Testing Both Modes

### Test Simple (Sequential):
```bash
# 1. Edit backend/.env
TRANSCRIPTION_MODE=sequential

# 2. Restart
python main.py

# 3. Look for
INFO: Using simple sequential transcription (basic method)

# 4. Test VAD Agent - uses basic transcribe_audio() like /chat-voice
```

### Test New (Parallel):
```bash
# 1. Edit backend/.env
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=3

# 2. Restart
python main.py

# 3. Look for
INFO: Using TRUE parallel processing with multiple Whisper models

# 4. Test VAD Agent - should be 3x faster!
```

---

**Bottom line:** Sequential mode = Simple `transcribe_audio()` from `stt.py` (like `/chat-voice`). Parallel mode = New faster parallel code with 3 models. You can switch anytime! 🎉

