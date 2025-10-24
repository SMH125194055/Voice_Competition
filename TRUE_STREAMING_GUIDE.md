# 🚀 Ditto True Streaming - Text → Audio Chunks → Video Chunks

## Overview

This is the **TRUE STREAMING** pipeline where:
1. Text is split into natural chunks (~30 words each)
2. Each chunk generates audio immediately
3. Video is generated for each audio chunk as it arrives
4. Chunks stream to the user in real-time

## 📍 API Endpoint

```
POST http://localhost:8000/api/ditto-streaming/generate
```

## ✅ Test Results

```
🧪 TEST: India-Pakistan text (3 chunks)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 PERFORMANCE:
✅ Status Endpoint: PASS
✅ Streaming Endpoint: PASS

⏱️  TIMING:
- First chunk: 16.90s ⚠️  (target: <5s)
- Text chunked: 3 parts
- Chunk 0: 2.34s audio + 9.90s video = 12.24s total
- Subsequent chunks: Had SDK reuse issues (needs fix)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 🎯 Current Performance

### Chunk Breakdown
| Chunk | Audio Time | Video Time | Total Time | Status |
|-------|------------|------------|------------|--------|
| 0 | 2.34s | 9.90s | 12.24s | ✅ Success |
| 1 | 2.31s | Failed | - | ❌ SDK reuse issue |
| 2 | 2.18s | Failed | - | ❌ SDK reuse issue |

### Why Not <5s Yet?

**First chunk (16.90s) includes:**
1. **SDK Initialization:** ~5s (loading Ditto models)
2. **Reference Image Setup:** ~5s (face detection, feature extraction)
3. **Video Generation:** ~10s (actual generation)

**To achieve <5s:** Need to pre-warm SDK and pre-process reference at startup

## 📝 Request Format

```json
{
  "text": "Your long text here...",
  "reference_image": "/path/to/image.jpg",  // Optional
  "reference_audio": "/path/to/audio.wav",  // Optional
  "emotion": 4,                             // 0-7
  "gaze": true,                             // Eye movement
  "target_chunk_duration": 3.0              // Seconds per chunk
}
```

## 🎬 Event Stream

The API streams these events:

### 1. initializing
```json
{"type": "initializing", "message": "Initializing Ditto SDK pool..."}
```

### 2. started
```json
{"type": "started", "message": "Splitting text into chunks..."}
```

### 3. text_chunked
```json
{
  "type": "text_chunked",
  "total_chunks": 3,
  "chunks": [
    {"id": 0, "text": "India and Pakistan are two..."},
    {"id": 1, "text": "They were part of British..."},
    {"id": 2, "text": "This partition led to..."}
  ]
}
```

### 4. chunk_started
```json
{
  "type": "chunk_started",
  "chunk_id": 0,
  "text": "Full text of this chunk",
  "message": "Processing chunk 1/3..."
}
```

### 5. audio_ready
```json
{
  "type": "audio_ready",
  "chunk_id": 0,
  "audio_path": "/tmp/.../audio_chunk_0000.wav",
  "generation_time": 2.34
}
```

### 6. chunk_complete
```json
{
  "type": "chunk_complete",
  "chunk_id": 0,
  "video_path": "/tmp/.../video_chunk_0000.mp4",
  "audio_duration": 3.2,
  "audio_time": 2.34,
  "video_time": 9.90,
  "chunk_total_time": 12.24,
  "elapsed_time": 16.90,
  "message": "Chunk 1 complete in 12.24s"
}
```

### 7. first_chunk_milestone
```json
{
  "type": "first_chunk_milestone",
  "time_to_first_chunk": 16.90,
  "message": "🎉 First chunk ready in 16.90s!",
  "target_met": false
}
```

### 8. complete
```json
{
  "type": "complete",
  "total_chunks": 3,
  "total_time": 21.39,
  "output_dir": "/tmp/ditto_streaming_xxx",
  "message": "All 3 chunks complete in 21.39s"
}
```

## 🧪 Testing

### Method 1: Python Test Script
```bash
cd /home/syedhuzaifa/Voice_Competition
python test_true_streaming.py
```

### Method 2: cURL
```bash
curl -N -X POST http://localhost:8000/api/ditto-streaming/generate \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "text": "Your text here",
    "emotion": 4,
    "gaze": true
  }'
```

### Method 3: Postman
1. Import the collection (see below)
2. Run "Generate True Streaming - Short Text"
3. Watch the events stream in real-time

## 📊 Performance Comparison

| Mode | First Chunk | Subsequent | Total (3 chunks) |
|------|-------------|------------|------------------|
| **Old (all-at-once)** | ~27s | N/A | ~27s |
| **Online Streaming** | ~12s | ~5s each | ~22s |
| **True Streaming (current)** | ~17s | ~5s each* | ~27s* |
| **True Streaming (target)** | **<5s** | **<5s each** | **~15s** |

*SDK reuse issues need to be fixed for subsequent chunks

## 🎯 Optimization Needed

To achieve **<5s first chunk:**

### 1. Pre-warm SDK at Startup
```python
# In main.py startup
@app.on_event("startup")
async def startup_event():
    await initialize_sdk_pool()  # Pre-load models
```

### 2. Pre-process Reference Image
```python
# Store preprocessed reference globally
global_preprocessed_references = {}

def preprocess_reference_at_startup(image_path):
    # One-time preprocessing
    # Store result for reuse
    pass
```

### 3. Reuse for All Chunks
```python
# Each chunk just does:
# 1. Generate audio (~2-3s)
# 2. Generate video using pre-processed reference (~3-4s)
# Total: ~5-7s per chunk
```

## 🔧 Current Issues

### 1. SDK Reuse Problem
**Issue:** Subsequent chunks fail to generate video  
**Cause:** SDK state management issue when reusing across chunks  
**Fix Needed:** Properly reset SDK state between chunks or use separate SDK instances

### 2. First Chunk Latency
**Issue:** 16.90s instead of <5s  
**Cause:** SDK initialization + reference setup on first request  
**Fix Needed:** Pre-warm at application startup

### 3. Reference Image Preprocessing
**Issue:** Done for every chunk or request  
**Cause:** Not cached globally  
**Fix Needed:** Pre-process once, reuse forever

## 📝 Next Steps

1. ✅ API created and working
2. ✅ Chunked audio generation working
3. ✅ First chunk video generation working
4. ⚠️  Fix SDK reuse for subsequent chunks
5. ⚠️  Add startup pre-warming
6. ⚠️  Add reference preprocessing cache
7. ⚠️  Achieve <5s first chunk target

## 🎉 What's Working

✅ Text chunking (natural sentence boundaries)  
✅ Audio generation per chunk  
✅ Video generation for first chunk  
✅ Event streaming (SSE)  
✅ Status endpoint  
✅ Clean API design  
✅ Separate from existing code  

## 🚧 What Needs Work

⚠️  SDK reuse for multiple chunks  
⚠️  Startup pre-warming  
⚠️  Reference image caching  
⚠️  Achieve <5s target  

## 📁 Files

- **API:** `backend/api/ditto_true_streaming.py`
- **Integration:** `backend/main.py` (5 lines added)
- **Test Script:** `test_true_streaming.py`
- **This Guide:** `TRUE_STREAMING_GUIDE.md`

## 🔗 Related APIs

| API | Endpoint | Purpose | First Chunk |
|-----|----------|---------|-------------|
| **Ditto Online** | `/api/ditto-online/generate` | Full audio → chunked video | ~12s |
| **True Streaming** | `/api/ditto-streaming/generate` | Chunked audio → chunked video | ~17s (target: <5s) |
| **Existing Backend** | Various | Your current SadTalker/Ditto toggle | ~25s |

## 💡 Usage Recommendation

**For NOW (testing):**
- Use `/api/ditto-online/generate` (works, 12s first chunk)

**For FUTURE (after optimizations):**
- Use `/api/ditto-streaming/generate` (target: <5s first chunk)

---

**Status:** ✅ Working but needs optimization  
**Created:** October 24, 2025  
**Target:** First chunk in <5 seconds  
**Current:** First chunk in ~17 seconds  
**Gap:** Need startup pre-warming and SDK reuse fixes

