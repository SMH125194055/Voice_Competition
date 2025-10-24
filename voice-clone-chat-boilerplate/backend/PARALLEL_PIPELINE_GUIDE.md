# 🚀 Parallel Pipeline for Real-Time Avatar Generation

## Overview

This parallel pipeline achieves **near real-time avatar video generation** by running LLM, Voice Cloning, and Avatar Generation simultaneously using a producer-consumer pattern with queues.

### Architecture

```
┌─────────────┐     ┌────────────┐     ┌──────────────┐     ┌─────────────┐
│ LLM Worker  │────▶│ Text Queue │────▶│ Voice Worker │────▶│ Audio Queue │
└─────────────┘     └────────────┘     └──────────────┘     └─────────────┘
                                                                      │
                                                                      ▼
┌─────────────┐     ┌────────────┐     ┌───────────────┐
│   Frontend  │◀────│Video Queue │◀────│ Avatar Worker │
└─────────────┘     └────────────┘     └───────────────┘
```

### Key Features

- ✅ **Parallel Processing**: All components run simultaneously
- ✅ **Global SDK Pool**: Shared Ditto SDK across requests (eliminates 15s warmup per request)
- ✅ **Server-Sent Events**: Real-time streaming to frontend
- ✅ **Queue-Based Communication**: Non-blocking producer-consumer pattern
- ✅ **Optimized Latency**: First video typically within 8-10 seconds after initial warmup

## Performance Metrics

### First Request (Cold Start)
- **SDK Warmup**: ~15s (one-time, global)
- **LLM Response**: ~2s
- **Voice Cloning**: ~2s per chunk
- **Video Generation**: ~5s per chunk
- **Total First Video**: ~24s

### Subsequent Requests (Warm)
- **SDK Warmup**: 0s (reused)
- **LLM Response**: ~2s
- **Voice Cloning**: ~2s
- **Video Generation**: ~5s
- **Total First Video**: ~9s 🎯

### Multi-Chunk Response
- **Chunks Generated**: Parallel processing
- **Example**: 9 chunks generated for India/Pakistan question
- **Throughput**: ~5-6s per chunk

## API Endpoints

### 1. Generate Parallel Pipeline

**Endpoint**: `POST /api/parallel-pipeline/generate`

**Request Body**:
```json
{
  "question": "What are the differences between India and Pakistan?",
  "reference_image": "Avatar/References/ref_1761131562372.jpg",
  "reference_audio": "audio/reference_voices/ref_1761118578.wav",
  "emotion": 4,
  "pose": {},
  "gaze": true
}
```

**Response**: Server-Sent Events (SSE) stream

**Events**:
```javascript
// Event 1: Pipeline started
data: {"event": "started", "session_id": "abc123", "message": "Pipeline started"}

// Event 2: Video chunk ready
data: {
  "event": "video_chunk",
  "video_url": "/generated_videos/parallel/abc123/chunk_0000.mp4",
  "duration": 2.5,
  "chunk_idx": 0,
  "audio_chunk_idx": 0,
  "text": "The answer to 2 + 2 is 4.",
  "generation_time": 5.2,
  "total_elapsed": 9.1,
  "session_id": "abc123"
}

// Event 3: Pipeline complete
data: {"event": "complete", "total_videos": 3, "total_time": 25.4}

// Event 4: Error (if any)
data: {"event": "error", "message": "Error details"}
```

### 2. Check Pipeline Status

**Endpoint**: `GET /api/parallel-pipeline/status`

**Response**:
```json
{
  "status": "ready",
  "pipeline_type": "parallel_queues",
  "components": ["llm", "voice_cloner", "avatar_generator"],
  "mode": "real_time_streaming"
}
```

## Frontend Integration

### JavaScript/React Example

```javascript
async function generateParallelVideo(question) {
  const response = await fetch('/api/parallel-pipeline/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: question,
      reference_image: 'Avatar/References/ref_1761131562372.jpg',
      reference_audio: 'audio/reference_voices/ref_1761118578.wav'
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        switch (data.event) {
          case 'started':
            console.log('Pipeline started:', data.session_id);
            break;
          
          case 'video_chunk':
            console.log('Video ready:', data.video_url);
            // Play video in <video> element
            playVideoChunk(data.video_url);
            break;
          
          case 'complete':
            console.log('All videos generated:', data.total_videos);
            break;
          
          case 'error':
            console.error('Error:', data.message);
            break;
        }
      }
    }
  }
}

function playVideoChunk(videoUrl) {
  const video = document.getElementById('avatar-video');
  video.src = videoUrl;
  video.play();
}
```

### Vue.js Example

```vue
<template>
  <div>
    <button @click="startGeneration">Generate Avatar</button>
    <video ref="avatarVideo" autoplay></video>
    <div>Status: {{ status }}</div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      status: 'idle',
      videoQueue: []
    }
  },
  methods: {
    async startGeneration() {
      this.status = 'generating';
      
      const response = await fetch('/api/parallel-pipeline/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: this.userQuestion,
          reference_image: this.referenceImage,
          reference_audio: this.referenceAudio
        })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            this.handleEvent(data);
          }
        }
      }
    },

    handleEvent(data) {
      switch (data.event) {
        case 'video_chunk':
          this.videoQueue.push(data.video_url);
          if (!this.$refs.avatarVideo.src) {
            this.playNext();
          }
          break;
        
        case 'complete':
          this.status = 'complete';
          break;
      }
    },

    playNext() {
      if (this.videoQueue.length > 0) {
        const nextVideo = this.videoQueue.shift();
        this.$refs.avatarVideo.src = nextVideo;
        this.$refs.avatarVideo.onended = () => this.playNext();
      }
    }
  }
}
</script>
```

## Configuration

### Environment Variables

Add to `.env`:

```ini
# Avatar Model Selection
AVATAR_MODEL=ditto

# Avatar Device
AVATAR_DEVICE=cuda:1

# Parallel Pipeline Settings (automatically used when AVATAR_MODEL=ditto)
# These are hardcoded in parallel_pipeline.py but can be made configurable:
# - chunk_duration=2.0s
# - overlap_duration=0.3s
# - max_parallel_workers=3
```

## Testing

### Python Test Script

```bash
cd backend
source venv/bin/activate
python test_parallel_simple.py
```

### cURL Test

```bash
curl -N -X POST http://localhost:8000/api/parallel-pipeline/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is 2 plus 2?",
    "reference_image": "Avatar/References/ref_1761131562372.jpg",
    "reference_audio": "audio/reference_voices/ref_1761118578.wav"
  }'
```

## Troubleshooting

### Issue: No videos generated

**Solution**: Check backend logs for errors
```bash
tail -f /tmp/backend_*.log | grep -E "Worker|Pipeline|Error"
```

### Issue: First video takes too long

**Cause**: SDK warmup happens on first request

**Solution**: The global SDK pool warms up once and is reused. First request will be slower (~24s), but subsequent requests will be ~9s.

### Issue: Videos have gaps between chunks

**Current Status**: Single chunk per audio segment (no gaps within chunk)

**Future Enhancement**: Implement smooth transitions between chunks using overlap and fade

### Issue: Connection timeout

**Solution**: Increase timeout in client
```javascript
fetch(url, { signal: AbortSignal.timeout(300000) }) // 5 minutes
```

## Directory Structure

```
backend/
├── api/
│   └── parallel_pipeline.py          # Main parallel pipeline implementation
├── utils/
│   ├── optimized_streaming_avatar.py # Optimized Ditto with SDK pooling
│   └── ditto_avatar_generator.py     # Ditto wrapper
├── generated_videos/
│   └── parallel/
│       └── {session_id}/
│           ├── chunk_0000.mp4
│           ├── chunk_0001.mp4
│           └── ...
└── test_parallel_simple.py            # Test script
```

## Performance Optimization Tips

### 1. Pre-warm SDK Pool

The SDK pool is automatically initialized on first import. You can pre-warm it during application startup in `main.py`:

```python
@app.on_event("startup")
async def startup_event():
    from api.parallel_pipeline import get_global_avatar_generator
    get_global_avatar_generator()  # Pre-warm
```

### 2. Adjust Worker Count

Modify `max_parallel_workers` in `parallel_pipeline.py`:
```python
_global_avatar_generator = OptimizedStreamingAvatar(
    chunk_duration=2.0,
    overlap_duration=0.3,
    max_parallel_workers=4  # Increase for more parallelism
)
```

### 3. Reduce Chunk Duration

Smaller chunks = lower latency, but more chunks to process:
```python
_global_avatar_generator = OptimizedStreamingAvatar(
    chunk_duration=1.5,  # Smaller chunks
    overlap_duration=0.3,
    max_parallel_workers=3
)
```

## Comparison: Parallel vs Sequential

| Metric | Sequential Pipeline | Parallel Pipeline |
|--------|-------------------|-------------------|
| First Video | ~20s | ~9s (after warmup) |
| Processing | Blocking | Non-blocking |
| User Experience | Wait for complete response | Immediate streaming |
| Memory | Lower | Higher (queues) |
| Complexity | Simple | Moderate |

## Future Enhancements

- [ ] Implement smooth chunk transitions with overlapping
- [ ] Add chunk pre-buffering for gapless playback
- [ ] Support for long-form content (>2 minutes)
- [ ] Dynamic worker scaling based on load
- [ ] WebSocket support in addition to SSE
- [ ] Progress indicators for each stage
- [ ] Retry logic for failed chunks

## Support

For issues or questions, check:
1. Backend logs: `/tmp/backend_*.log`
2. Generated videos: `backend/generated_videos/parallel/`
3. Test scripts: `backend/test_parallel_simple.py`

## License

Same as parent project.
