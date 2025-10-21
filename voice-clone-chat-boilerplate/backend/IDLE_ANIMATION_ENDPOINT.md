# 🎬 Idle Animation Generation Endpoint

## Overview
This endpoint generates a short (3-second) looping idle animation from a reference picture. The animation should show subtle movements like breathing, blinking, or slight head movements to make the avatar feel "alive" when not speaking.

---

## Endpoint Details

### Route
```
POST /generate-idle-animation
```

### Request Body
```json
{
  "picture_id": "ref_1760957800941",
  "duration": 3
}
```

**Parameters:**
- `picture_id` (string, required): Reference picture ID from database
- `duration` (int, optional): Duration in seconds, default = 3

### Response (Success)
```json
{
  "idle_video_url": "/avatars/idle/idle_1698765432.mp4",
  "duration": 3,
  "status": "success"
}
```

### Response (Error)
```json
{
  "error": "Picture not found",
  "status": "error"
}
```

---

## Implementation Suggestions

### Option 1: Using SadTalker (Recommended)
```python
from Avatar.SadTalker.src.generate_batch import get_facerender_data
import numpy as np

@app.post("/generate-idle-animation")
async def generate_idle_animation(request: dict):
    picture_id = request.get('picture_id')
    duration = request.get('duration', 3)
    
    # Get reference picture path
    picture_path = get_reference_picture_path(picture_id)
    
    # Generate idle coefficients (no audio, just default pose)
    # Use neutral pose with minimal variation
    fps = 12
    num_frames = duration * fps  # 3 seconds * 12 fps = 36 frames
    
    # Create subtle movement pattern
    idle_coeffs = generate_idle_coefficients(
        source_image=picture_path,
        num_frames=num_frames,
        movement_type='gentle',  # breathing + blinking
        fps=fps
    )
    
    # Render video
    idle_video_path = render_idle_video(
        coeffs=idle_coeffs,
        source_image=picture_path,
        fps=fps
    )
    
    return {
        "idle_video_url": f"/avatars/idle/{os.path.basename(idle_video_path)}",
        "duration": duration,
        "status": "success"
    }
```

### Option 2: Pre-rendered Template (Fast)
```python
@app.post("/generate-idle-animation")
async def generate_idle_animation(request: dict):
    picture_id = request.get('picture_id')
    
    # Use existing idle generation logic
    # (Similar to first chunk generation but no audio)
    
    # Generate with silence audio or default pose
    idle_video = await generate_avatar_video(
        picture_id=picture_id,
        audio_data=generate_silence(duration=3),  # 3 sec silence
        preprocess='crop',
        still_mode=False  # Allow movement
    )
    
    return {
        "idle_video_url": idle_video['video_url'],
        "duration": 3,
        "status": "success"
    }
```

### Option 3: Use Existing Avatar Generation
```python
@app.post("/generate-idle-animation")
async def generate_idle_animation(request: dict):
    """
    Quick implementation: Use existing avatar generation
    with a neutral audio (silence or soft breathing sound)
    """
    picture_id = request.get('picture_id')
    duration = request.get('duration', 3)
    
    # Generate silent audio (needed for SadTalker)
    silence_audio = generate_silent_audio(duration_seconds=duration)
    
    # Save silence audio temporarily
    temp_audio_path = f"/tmp/silence_{time.time()}.wav"
    save_audio(silence_audio, temp_audio_path)
    
    # Use existing inference_sadtalker function
    idle_video_path = inference_sadtalker(
        source_image=get_picture_path(picture_id),
        driven_audio=temp_audio_path,
        preprocess='crop',
        still_mode=False,
        expression_scale=0.3,  # Subtle expressions
        fps=12
    )
    
    # Clean up temp audio
    os.remove(temp_audio_path)
    
    return {
        "idle_video_url": f"/avatars/idle/{os.path.basename(idle_video_path)}",
        "duration": duration,
        "status": "success"
    }

def generate_silent_audio(duration_seconds=3, sample_rate=16000):
    """Generate silent audio for SadTalker"""
    import numpy as np
    import soundfile as sf
    
    # Create silence
    num_samples = int(duration_seconds * sample_rate)
    silence = np.zeros(num_samples, dtype=np.float32)
    
    return silence
```

---

## Integration with Frontend

The frontend already has the complete integration code:

```javascript
// Generate idle animation
const generateIdleAnimation = async () => {
  setIsGeneratingIdle(true);
  setStatus('Generating idle animation...');
  
  try {
    const response = await fetch(`${API_BASE_URL}/generate-idle-animation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        picture_id: referencePictureId,
        duration: 3
      })
    });
    
    if (response.ok) {
      const data = await response.json();
      const idleUrl = `${API_BASE_URL}${data.idle_video_url}?t=${Date.now()}`;
      setIdleAvatarUrl(idleUrl);
      
      // Play immediately
      avatarVideoRef.current.src = idleUrl;
      avatarVideoRef.current.loop = true;
      avatarVideoRef.current.play();
      
      setStatus('Idle animation ready!');
    }
  } catch (err) {
    console.error('Failed:', err);
    setError('Failed to generate idle animation');
  } finally {
    setIsGeneratingIdle(false);
  }
};
```

---

## File Storage

### Directory Structure
```
backend/
  outputs/
    idle_animations/
      idle_1698765432_ref_1760957800941.mp4
      idle_1698765433_ref_1760957800941.mp4
```

### Serving Static Files
```python
# Add to main.py
from fastapi.staticfiles import StaticFiles

app.mount("/avatars/idle", StaticFiles(directory="outputs/idle_animations"), name="idle_animations")
```

---

## Optimization Tips

### Cache Idle Animations
```python
# Check if idle animation already exists
idle_cache_path = f"outputs/idle_animations/idle_{picture_id}.mp4"
if os.path.exists(idle_cache_path):
    # Return cached version
    return {
        "idle_video_url": f"/avatars/idle/idle_{picture_id}.mp4",
        "duration": 3,
        "status": "cached"
    }
```

### Background Generation
```python
from fastapi import BackgroundTasks

@app.post("/generate-idle-animation")
async def generate_idle_animation(
    request: dict, 
    background_tasks: BackgroundTasks
):
    # Return immediately with status
    task_id = str(uuid.uuid4())
    
    # Generate in background
    background_tasks.add_task(
        generate_idle_video_task,
        task_id,
        request['picture_id']
    )
    
    return {
        "task_id": task_id,
        "status": "generating"
    }

# Add status check endpoint
@app.get("/idle-animation-status/{task_id}")
async def check_idle_status(task_id: str):
    # Check generation status
    if task_id in completed_tasks:
        return {
            "status": "complete",
            "idle_video_url": completed_tasks[task_id]
        }
    return {"status": "generating"}
```

---

## Testing

### Test with curl
```bash
curl -X POST http://localhost:8000/generate-idle-animation \
  -H "Content-Type: application/json" \
  -d '{"picture_id": "ref_1760957800941", "duration": 3}'
```

### Expected Response
```json
{
  "idle_video_url": "/avatars/idle/idle_1698765432.mp4",
  "duration": 3,
  "status": "success"
}
```

### Test Video Access
```bash
curl http://localhost:8000/avatars/idle/idle_1698765432.mp4 --output test_idle.mp4
```

---

## Error Handling

### Handle Common Errors
```python
@app.post("/generate-idle-animation")
async def generate_idle_animation(request: dict):
    try:
        picture_id = request.get('picture_id')
        
        # Validate picture exists
        if not picture_exists(picture_id):
            raise HTTPException(
                status_code=404,
                detail="Reference picture not found"
            )
        
        # Validate duration
        duration = min(max(request.get('duration', 3), 1), 10)  # 1-10 sec
        
        # Generate...
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Picture not found")
    except Exception as e:
        logger.error(f"Idle generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Performance Considerations

### Generation Time
- **SadTalker**: ~5-10 seconds for 3-second video
- **Pre-rendered**: Instant (if cached)
- **Background task**: User doesn't wait

### Memory Usage
- ~500MB RAM for generation
- ~2-5MB per output video
- Clean up old idle videos periodically

### Optimization
```python
# Delete old idle animations (keep last 50)
def cleanup_old_idle_animations():
    idle_dir = "outputs/idle_animations"
    files = sorted(
        glob.glob(f"{idle_dir}/*.mp4"),
        key=os.path.getmtime,
        reverse=True
    )
    
    # Keep last 50, delete rest
    for old_file in files[50:]:
        os.remove(old_file)
```

---

## Summary

**Quick Implementation (Option 3 Recommended):**

1. Create endpoint: `POST /generate-idle-animation`
2. Generate 3-second silent audio
3. Use existing `inference_sadtalker()` function
4. Return video URL
5. Frontend already handles the rest

**Time to implement:** ~30 minutes

**Result:** Professional idle animation that adds life to the AI avatar!

---

Last Updated: October 21, 2025

