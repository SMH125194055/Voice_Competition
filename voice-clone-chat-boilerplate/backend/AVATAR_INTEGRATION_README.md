# Avatar Generation Integration

## 🎬 Overview

This integration adds **near real-time avatar video generation** to the voice cloning chat system using SadTalker. The system streams both audio and video responses with minimal latency.

## ✨ Features

1. **Streaming Architecture**: Audio chunks stream immediately while avatar generates in parallel
2. **Reference Picture Management**: Upload and manage reference pictures like reference voices
3. **Parallel Processing**: Voice cloning and avatar generation run simultaneously
4. **Fast Mode**: Optimized for speed (256x256, still mode)
5. **SSE Streaming**: Server-Sent Events for real-time updates
6. **Configurable**: Control via environment variables

## 🚀 Quick Start

### 1. Configuration

Edit your environment variables or use defaults in `avatar_config.py`:

```bash
# Enable avatar generation
AVATAR_ENABLED=true

# Model settings
AVATAR_MODEL=sadtalker
AVATAR_DEVICE=cuda  # or 'cpu'
AVATAR_SIZE=256     # 256 (fast) or 512 (quality)
AVATAR_ENHANCER=gfpgan  # or 'none' for faster processing

# Default reference image
AVATAR_DEFAULT_IMAGE=Avatar/References/Huzaifa.jpg

# Generation mode
AVATAR_MODE=fast  # or 'quality'
```

### 2. Start the Server

```bash
cd backend
source venv/bin/activate
python main.py
```

The avatar generator will initialize on startup.

### 3. Test the Integration

```bash
python test_avatar_integration.py
```

## 📡 API Endpoints

### Avatar Management

#### Upload Reference Picture
```http
POST /upload-reference-picture
Content-Type: multipart/form-data

image: <image file (JPEG/PNG)>
```

**Response:**
```json
{
  "success": true,
  "reference_picture_id": "ref_1729012345678",
  "reference_path": "/path/to/picture.jpg",
  "message": "Reference picture uploaded successfully"
}
```

#### List Reference Pictures
```http
GET /list-reference-pictures
```

**Response:**
```json
{
  "pictures": [
    {
      "id": "ref_1729012345678",
      "filename": "ref_1729012345678.jpg",
      "path": "/path/to/picture.jpg",
      "size": 204800,
      "width": 512,
      "height": 512
    }
  ]
}
```

#### Delete Reference Picture
```http
DELETE /delete-reference-picture/{reference_id}
```

### Avatar Generation

#### Streaming Voice + Avatar Chat
```http
POST /vad-chat-avatar-stream
Content-Type: multipart/form-data

audio: <audio file>
voice_mode: "real-time" | "inference"
reference_voice_id: <optional voice ID>
reference_picture_id: <optional picture ID>
enable_avatar: "true" | "false"
allow_interruption: "true" | "false"
```

**SSE Events:**

1. `vad_start` - Voice activity detection started
2. `vad_complete` - VAD complete, speech detected
3. `transcription_start` - Transcribing user speech
4. `transcription_complete` - User text ready
5. `llm_start` - AI thinking
6. `tts_chunk` - Audio chunk with text (streamed multiple times)
7. `llm_complete` - Full AI response ready
8. `avatar_start` - Avatar generation started
9. `avatar_complete` - Avatar video ready (base64 encoded MP4)
10. `complete` - All done

**TTS Chunk Format:**
```json
{
  "chunk_index": 0,
  "text": "Hello, how are you?",
  "audio": "<base64-encoded-wav>",
  "words": ["Hello,", "how", "are", "you?"],
  "audio_format": "wav",
  "allow_interruption": true
}
```

**Avatar Complete Format:**
```json
{
  "video": "<base64-encoded-mp4>",
  "format": "mp4"
}
```

## ⚡ Performance Optimization

### Current Implementation

1. **Streaming Audio First**: Users hear response immediately (chunks of 6 words)
2. **Parallel Avatar**: Avatar generates while audio streams
3. **Fast Settings**: 256x256 resolution, still mode, crop preprocessing
4. **Model Optimization**: Uses safetensors for faster loading

### Latency Breakdown

- **Audio chunks**: 1-2 seconds each (starts immediately)
- **Avatar generation**: 10-20 seconds (runs in background)
- **User experience**: Near real-time audio + video at end

### Tips for Lower Latency

1. **Use GPU**: Set `AVATAR_DEVICE=cuda` (5-10x faster)
2. **Lower Resolution**: Use `AVATAR_SIZE=256` instead of 512
3. **Disable Enhancer**: Set `AVATAR_ENHANCER=none` for 2-3x speedup
4. **Cache Reference Pictures**: Reuse uploaded pictures instead of default

## 🏗️ Architecture

```
User Audio Input
    ↓
VAD + Transcription
    ↓
LLM Processing
    ↓
    ├─→ Audio Chunks (Streaming) ────→ User hears immediately
    │
    └─→ Full Audio + Avatar (Parallel) ─→ Video at end
```

### File Structure

```
backend/
├── Avatar/
│   ├── References/          # Reference pictures
│   ├── SadTalker/          # SadTalker model
│   └── output/             # Generated videos
├── utils/
│   ├── avatar_generator.py # Avatar generation service
│   └── avatar_reference.py # Picture management
├── avatar_config.py        # Configuration
└── main.py                 # API endpoints
```

## 🔧 Troubleshooting

### Avatar Generation Fails

1. **Check CUDA availability**:
   ```python
   import torch
   print(torch.cuda.is_available())
   ```

2. **Check model files**:
   ```bash
   ls -la Avatar/SadTalker/checkpoints/
   ls -la Avatar/SadTalker/gfpgan/weights/
   ```

3. **Try CPU mode**:
   ```bash
   AVATAR_DEVICE=cpu
   ```

### Slow Performance

1. **Use smaller size**: `AVATAR_SIZE=256`
2. **Disable enhancer**: `AVATAR_ENHANCER=none`
3. **Check GPU memory**: `nvidia-smi`

### Memory Issues

1. **Reduce parallel workers**: Lower `WHISPER_WORKERS`
2. **Clear output directory**: Old videos accumulate
3. **Use CPU for avatar**: Frees GPU for other tasks

## 🎯 Frontend Integration

### Example JavaScript (SSE)

```javascript
const formData = new FormData();
formData.append('audio', audioBlob);
formData.append('voice_mode', 'real-time');
formData.append('enable_avatar', 'true');
formData.append('reference_picture_id', selectedPictureId);

const eventSource = new EventSource('/vad-chat-avatar-stream');

eventSource.addEventListener('tts_chunk', (event) => {
  const data = JSON.parse(event.data);
  // Play audio chunk immediately
  playAudioChunk(data.audio, data.audio_format);
  // Display text
  displayText(data.text);
});

eventSource.addEventListener('avatar_complete', (event) => {
  const data = JSON.parse(event.data);
  // Display video
  displayVideo(data.video, data.format);
});

eventSource.addEventListener('complete', () => {
  eventSource.close();
});
```

## 📊 Comparison: With vs Without Avatar

| Feature | Voice Only | Voice + Avatar |
|---------|-----------|----------------|
| First audio | ~1-2 sec | ~1-2 sec (same) |
| Complete response | ~4-6 sec | ~4-6 sec (same) |
| Avatar video | N/A | +10-20 sec |
| User experience | Audio only | Audio first, video follows |
| Total latency | 4-6 sec | 15-25 sec (avatar) |

**Key Point**: Audio streams immediately, avatar is a bonus feature that arrives after.

## 🚦 Status Monitoring

Check system status:

```bash
curl http://localhost:8000/
```

Response includes avatar status:

```json
{
  "status": "running",
  "avatar": {
    "enabled": true,
    "model": "sadtalker",
    "device": "cuda",
    "initialized": true
  }
}
```

## 📝 Notes

- Avatar generation uses the same voice cloning reference as audio
- First avatar generation may be slower (model loading)
- Subsequent generations are faster (models cached in memory)
- Videos are automatically cleaned up after sending
- Reference pictures are optimized on upload (max 1024x1024)

## 🎓 Advanced Usage

### Custom Avatar Settings

```python
from utils.avatar_generator import AvatarGenerator

generator = AvatarGenerator(
    checkpoint_dir="Avatar/SadTalker/checkpoints",
    config_dir="Avatar/SadTalker/src/config",
    device="cuda",
    size=512,  # Higher quality
    enhancer="gfpgan"
)

video_path = await generator.generate_avatar_video(
    audio_path="path/to/audio.wav",
    image_path="path/to/image.jpg",
    output_dir="output/",
    still_mode=False,  # More dynamic
    expression_scale=1.5  # More expressive
)
```

### Batch Processing

For multiple avatars, reuse the initialized generator to avoid reloading models.

## 🎉 Success!

Your avatar generation system is now integrated and ready to use! 

Start the server and enjoy near real-time voice cloning with avatar videos! 🚀


