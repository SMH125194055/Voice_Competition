# 🔧 Transcription Mode Configuration

## Overview

You can now switch between **parallel** and **sequential** transcription modes using environment variables!

## Configuration Options

### 1. Parallel Mode (Default) ⚡

**Best for**: Speed, multi-core systems, sufficient RAM

```bash
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=3
```

**Features:**
- ✅ 3x faster transcription
- ✅ Multiple Whisper model instances
- ✅ TRUE parallel processing
- ⚠️ Uses more RAM (~4.5 GB for 3 workers with base model)

**Memory Usage:**
- 2 workers: ~3 GB
- 3 workers: ~4.5 GB (recommended)
- 4 workers: ~6 GB

### 2. Sequential Mode 🔄

**Best for**: Low RAM systems, single-core, memory-constrained environments

```bash
TRANSCRIPTION_MODE=sequential
```

**Features:**
- ✅ Low memory usage (~1.5 GB with base model)
- ✅ Stable and reliable
- ✅ Progressive updates
- ⚠️ Slower (3x slower than parallel)

## How to Configure

### Method 1: Create .env file (Recommended)

Create `voice-clone-chat-boilerplate/backend/.env`:

```bash
# Transcription Configuration
# ============================

# Mode: "parallel" or "sequential"
TRANSCRIPTION_MODE=parallel

# Number of parallel workers (only used in parallel mode)
WHISPER_WORKERS=3

# Whisper model size
WHISPER_MODEL=base

# Other settings
MODE=local
```

### Method 2: Set Environment Variables

**Windows (PowerShell):**
```powershell
$env:TRANSCRIPTION_MODE="parallel"
$env:WHISPER_WORKERS="3"
python main.py
```

**Linux/Mac:**
```bash
export TRANSCRIPTION_MODE=parallel
export WHISPER_WORKERS=3
python main.py
```

### Method 3: Inline

```bash
# Windows PowerShell
$env:TRANSCRIPTION_MODE="sequential"; python main.py

# Linux/Mac
TRANSCRIPTION_MODE=sequential python main.py
```

## Quick Switching

### Switch to Parallel (Fast)

```bash
# 1. Edit backend/.env
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=3

# 2. Restart backend
cd voice-clone-chat-boilerplate/backend
python main.py
```

### Switch to Sequential (Low Memory)

```bash
# 1. Edit backend/.env
TRANSCRIPTION_MODE=sequential

# 2. Restart backend
cd voice-clone-chat-boilerplate/backend
python main.py
```

## Verification

### Check Current Mode

Visit: `http://localhost:8000/`

**Parallel Mode:**
```json
{
  "status": "running",
  "transcription_mode": "parallel",
  "parallel_whisper": {
    "enabled": true,
    "workers": 3
  }
}
```

**Sequential Mode:**
```json
{
  "status": "running",
  "transcription_mode": "sequential",
  "parallel_whisper": {
    "enabled": false,
    "workers": 1
  }
}
```

### Check Startup Logs

**Parallel Mode:**
```
INFO: Transcription mode: parallel
INFO: Initializing 3 parallel Whisper workers...
INFO: Loaded Whisper model 1/3
INFO: Loaded Whisper model 2/3
INFO: Loaded Whisper model 3/3
INFO: ✅ Parallel processing STT initialized with 3 workers
```

**Sequential Mode:**
```
INFO: Transcription mode: sequential
INFO: Sequential processing mode enabled (TRANSCRIPTION_MODE=sequential)
```

### Check During Transcription

**Parallel Mode:**
```
INFO: Using TRUE parallel processing with multiple Whisper models
INFO: 🚀 Processing 7 chunks with 3 parallel workers
INFO: ✅ Chunk 2 transcribed by model 2: 'Hello'
INFO: ✅ Chunk 1 transcribed by model 1: 'Hi'
```

**Sequential Mode:**
```
INFO: Using sequential processing with single Whisper model
INFO: Processing 7 chunks sequentially (Whisper not thread-safe)
INFO: Chunk 1/7 completed: 'Hello'
INFO: Chunk 2/7 completed: 'how are'
```

## Performance Comparison

### 10-Second Audio

| Mode | Processing Time | Memory | CPU Usage |
|------|----------------|---------|-----------|
| **Parallel (3 workers)** | 4-5 seconds | ~4.5 GB | High (300%) |
| **Sequential** | 10-14 seconds | ~1.5 GB | Normal (100%) |

### When to Use Each

**Use Parallel When:**
- ✅ You have 8+ GB RAM
- ✅ You need fastest transcription
- ✅ You have multi-core CPU
- ✅ Speed is priority over memory

**Use Sequential When:**
- ✅ You have limited RAM (< 8 GB)
- ✅ Memory is constrained
- ✅ Single-core or low-power system
- ✅ Stability over speed

## Advanced Configuration

### Optimize Parallel Mode

```bash
# For high-end systems (16+ GB RAM)
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=4
WHISPER_MODEL=small

# For normal systems (8-16 GB RAM)
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=3
WHISPER_MODEL=base

# For low-end systems (6-8 GB RAM)
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=2
WHISPER_MODEL=tiny
```

### Optimize Sequential Mode

```bash
# For accuracy
TRANSCRIPTION_MODE=sequential
WHISPER_MODEL=base

# For speed (fastest sequential)
TRANSCRIPTION_MODE=sequential
WHISPER_MODEL=tiny

# For balance
TRANSCRIPTION_MODE=sequential
WHISPER_MODEL=base
```

## Troubleshooting

### Issue: Backend Crashes in Parallel Mode

**Solution**: Switch to sequential or reduce workers
```bash
# Option 1: Sequential
TRANSCRIPTION_MODE=sequential

# Option 2: Fewer workers
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=2
```

### Issue: Too Slow in Sequential Mode

**Solution**: Switch to parallel (if RAM allows)
```bash
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=3
WHISPER_MODEL=tiny  # Faster model
```

### Issue: Mode Not Changing

**Solution**: Restart backend after changing .env
1. Stop backend (Ctrl+C)
2. Verify .env changes saved
3. Start backend again
4. Check `http://localhost:8000/` for new mode

## Example .env Files

### For Development (Speed Priority)

```bash
# backend/.env
MODE=local
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=3
WHISPER_MODEL=base
```

### For Low-RAM Systems

```bash
# backend/.env
MODE=local
TRANSCRIPTION_MODE=sequential
WHISPER_MODEL=tiny
```

### For Production (Balanced)

```bash
# backend/.env
MODE=local
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=2
WHISPER_MODEL=base
```

### For GPU Systems

```bash
# backend/.env
MODE=local
TRANSCRIPTION_MODE=parallel
WHISPER_WORKERS=1  # GPU memory limited
WHISPER_MODEL=base
```

## Summary

| Feature | Parallel | Sequential |
|---------|----------|------------|
| **Speed** | ⚡⚡⚡ (4-5s) | 🐢 (10-14s) |
| **Memory** | High (~4.5GB) | Low (~1.5GB) |
| **CPU Usage** | High (300%) | Normal (100%) |
| **Complexity** | Medium | Low |
| **Recommended For** | Development, Production | Low-RAM, Testing |

---

## Quick Commands

```bash
# Create .env file
cd voice-clone-chat-boilerplate/backend
echo "TRANSCRIPTION_MODE=parallel" > .env
echo "WHISPER_WORKERS=3" >> .env

# Test parallel mode
python main.py

# Switch to sequential
echo "TRANSCRIPTION_MODE=sequential" > .env
python main.py
```

---

**Now you have full control over transcription performance! 🚀**

Choose the mode that best fits your system and requirements.




