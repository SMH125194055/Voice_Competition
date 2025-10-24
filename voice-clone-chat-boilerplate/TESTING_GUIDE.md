# 🧪 Parallel Pipeline Testing Guide

## ✅ System Status

### Backend
- **Status**: ✅ Running
- **Port**: 8000
- **URL**: http://localhost:8000
- **Check**: `curl http://localhost:8000/api/parallel-pipeline/status`

### Frontend
- **Status**: ✅ Running
- **Port**: 3000
- **URL**: http://localhost:3000
- **Mode**: Parallel Pipeline (default)

## 🎯 Quick Start Testing

### 1. Browser Test (Recommended)

1. **Open Browser**:
   ```
   http://localhost:3000
   ```

2. **You should see**:
   - Mode switcher buttons at top right
   - "⚡ Parallel Pipeline" button highlighted in green
   - Avatar video player (large section)
   - Status indicator
   - Microphone controls

3. **Allow Microphone Access**:
   - Browser will prompt for permission
   - Click "Allow"

4. **Click "🎤 Start"**:
   - Status will show "Listening..."
   - Speak a question (e.g., "What is 2 plus 2?")
   - Stop speaking and wait 1-2 seconds

5. **Watch the Pipeline**:
   - Status changes: "Recording..." → "Processing..." → "Pipeline running..."
   - Metrics display appears showing:
     - First Video time
     - Number of videos
     - Session ID
   - Video starts playing automatically

6. **Expected Performance**:
   - **First request**: ~24s (includes 15s SDK warmup)
   - **Subsequent requests**: ~9s 🎯
   - **Videos**: Smooth playback, no gaps

### 2. Command Line Test

```bash
cd /home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend
source venv/bin/activate
python test_parallel_simple.py
```

**Expected Output**:
```
🧪 Testing Parallel Pipeline
   Question: What are the differences between India and Pakistan?
   Target: First video <5 seconds

📡 Connecting to pipeline...
✅ Connected (status: 200)

───────────────────────────────────────────────────────────
[  0.00s] 🚀 Pipeline started (session: abc123)
[  9.15s] 🎉 FIRST VIDEO READY!
[  9.15s] 📹 Video 1: /generated_videos/parallel/abc123/chunk_0000.mp4
               Duration: 2.50s, Gen Time: 5.12s

[25.43s] ✅ Pipeline Complete!
───────────────────────────────────────────────────────────

📊 RESULTS:
   Total Videos: 3
   First Video: 9.15s
   Total Time: 25.43s
```

### 3. cURL Test

```bash
curl -N -X POST http://localhost:8000/api/parallel-pipeline/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is 2 plus 2?",
    "reference_image": "Avatar/References/ref_1761131562372.jpg",
    "reference_audio": "audio/reference_voices/ref_1761118578.wav"
  }'
```

**Expected Output** (SSE stream):
```
data: {"event": "started", "session_id": "abc123", "message": "Pipeline started"}

data: {"event": "video_chunk", "video_url": "/generated_videos/parallel/abc123/chunk_0000.mp4", ...}

data: {"event": "complete", "total_videos": 1, "total_time": 9.2}
```

## 📊 Test Scenarios

### Scenario 1: Simple Question
**Input**: "What is 2 plus 2?"
**Expected**:
- 1 video chunk
- ~9s total (after warmup)
- Clear audio and video sync

### Scenario 2: Medium Response
**Input**: "Explain photosynthesis"
**Expected**:
- 2-3 video chunks
- ~15-20s total
- Smooth playback

### Scenario 3: Long Response
**Input**: "What are the differences between India and Pakistan?"
**Expected**:
- 7-9 video chunks
- ~40-50s total
- Multiple videos in queue

### Scenario 4: Back-to-Back Requests
1. Ask first question
2. Wait for completion
3. Immediately ask second question
**Expected**:
- First request: ~24s
- Second request: ~9s (no warmup)
- Third request: ~9s (consistent performance)

## 🔍 Verification Checklist

### Backend Verification

- [ ] Backend responds to status check:
  ```bash
  curl http://localhost:8000/api/parallel-pipeline/status
  ```

- [ ] Backend logs show worker initialization:
  ```bash
  tail -f /tmp/backend_*.log | grep "Worker"
  ```
  Expected: "LLM Worker Started", "Voice Worker Started", "Avatar Worker Started"

- [ ] SDK pool initializes:
  ```bash
  tail -f /tmp/backend_*.log | grep "SDK"
  ```
  Expected: "SDK pool ready"

- [ ] Videos are generated:
  ```bash
  ls -lh backend/generated_videos/parallel/*/chunk_*.mp4
  ```
  Should show .mp4 files with sizes ~150-200KB each

### Frontend Verification

- [ ] Frontend loads without errors:
  ```bash
  curl -s http://localhost:3000 | grep "root"
  ```

- [ ] Parallel Pipeline button is visible and highlighted

- [ ] Microphone permission granted

- [ ] Video player visible

- [ ] Status updates in real-time

- [ ] Metrics display appears after first video

- [ ] Videos play automatically

- [ ] No JavaScript errors in browser console (F12)

### Performance Verification

- [ ] First video arrives within 10s (after warmup)
- [ ] Subsequent videos arrive within 5-6s each
- [ ] No gaps between video chunks within same response
- [ ] CPU usage reasonable (<80% per core)
- [ ] Memory stable (no leaks)
- [ ] GPU utilization high during generation

## 🐛 Troubleshooting

### Issue: Frontend shows blank page

**Check**:
```bash
tail -50 /tmp/frontend.log
```

**Common causes**:
- npm dependencies not installed
- Port 3000 already in use
- Build errors

**Solution**:
```bash
cd frontend/voice-ui
npm install
npm start
```

### Issue: Backend not responding

**Check**:
```bash
ps aux | grep uvicorn
curl http://localhost:8000/api/parallel-pipeline/status
```

**Solution**:
```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Issue: No videos generated

**Check logs**:
```bash
tail -100 /tmp/backend_*.log | grep -E "Error|Traceback|Worker"
```

**Common causes**:
- SDK not initialized
- TTS not initialized
- Missing reference files
- GPU memory full

**Solution**:
```bash
# Restart backend
pkill -f uvicorn
# Clear GPU memory if needed
# Restart backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Issue: Videos have no audio

**Check**:
```bash
ffprobe backend/generated_videos/parallel/{session_id}/chunk_0000.mp4
```

**Expected**: Should show both video and audio streams

**Solution**: Ensure FFmpeg is installed and working

### Issue: First video takes >20s

**Cause**: SDK warmup happening

**Expected**: This is normal for first request. Subsequent requests should be ~9s.

**Verify**:
```bash
tail -f /tmp/backend_*.log | grep "SDK pool"
```

Should show "SDK pool ready" only once at startup.

### Issue: Browser microphone not working

**Check**:
- HTTPS or localhost (required for microphone)
- Browser permissions
- Microphone hardware connected

**Solution**:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for permission errors
4. Click lock icon in address bar
5. Allow microphone access

## 📈 Performance Monitoring

### Real-time Monitoring

Terminal 1 (Backend logs):
```bash
tail -f /tmp/backend_*.log | grep -E "Worker|Pipeline|Video|SDK"
```

Terminal 2 (Resource usage):
```bash
watch -n 1 'nvidia-smi && echo "---" && ps aux | grep -E "uvicorn|python" | grep -v grep | head -5'
```

Terminal 3 (Generated videos):
```bash
watch -n 2 'find backend/generated_videos/parallel -name "*.mp4" -mmin -1 -ls | tail -10'
```

### Metrics to Track

1. **First Video Latency**: Time from request to first video
   - Target: <10s (after warmup)
   - Good: 8-12s
   - Needs optimization: >15s

2. **Throughput**: Videos per second
   - Target: 1 video per 5-6s
   - Good: 0.15-0.20 videos/s
   - Needs optimization: <0.10 videos/s

3. **Memory Usage**:
   - Target: <8GB GPU, <4GB RAM
   - Good: 6-10GB GPU, 2-6GB RAM
   - Needs optimization: >12GB GPU

4. **CPU Usage**:
   - Target: <80% per core
   - Good: 40-70%
   - Needs optimization: >90%

## 🎬 Video Quality Check

Play generated video:
```bash
ffplay backend/generated_videos/parallel/{session_id}/chunk_0000.mp4
```

**Check**:
- [ ] Video resolution: 256x256 (or 512x512)
- [ ] Frame rate: 25 FPS
- [ ] Audio sync: Lips match speech
- [ ] Audio quality: Clear, no distortion
- [ ] Video quality: Smooth, no artifacts
- [ ] Duration: Matches text length (~2-3s per sentence)

## 📊 Load Testing

### Single User Test
```bash
for i in {1..5}; do
  echo "Request $i"
  time curl -N -X POST http://localhost:8000/api/parallel-pipeline/generate \
    -H "Content-Type: application/json" \
    -d '{"question": "What is 2 plus 2?"}' \
    2>&1 | head -20
  echo "---"
done
```

**Expected**: Each request after first should be ~9s

### Concurrent Users Test
```bash
# Run 3 requests simultaneously
for i in {1..3}; do
  (
    echo "User $i starting"
    curl -N -X POST http://localhost:8000/api/parallel-pipeline/generate \
      -H "Content-Type: application/json" \
      -d "{\"question\": \"What is $i plus $i?\"}" \
      > /tmp/user_$i.log 2>&1
    echo "User $i done"
  ) &
done
wait
echo "All users done"
```

**Check**:
```bash
grep -E "event|error" /tmp/user_*.log
```

**Expected**: All requests complete successfully (may be slower due to shared resources)

## ✅ Acceptance Criteria

System is working correctly if:

- ✅ Backend starts without errors
- ✅ Frontend loads and shows Parallel Pipeline UI
- ✅ First video arrives within 10s (after warmup)
- ✅ Subsequent videos arrive within 6s
- ✅ Videos have synchronized audio
- ✅ Video quality is acceptable
- ✅ No memory leaks (stable over time)
- ✅ Multiple requests work consecutively
- ✅ Error messages are clear
- ✅ Browser console shows no errors

## 📝 Test Log Template

Use this to document your testing:

```
Date: _______________
Tester: _______________

Backend Status: [ ] Running [ ] Not Running
Frontend Status: [ ] Running [ ] Not Running

Test 1: Simple Question
Question: "What is 2 plus 2?"
First Video Time: _____s
Total Time: _____s
Videos Generated: _____
Result: [ ] Pass [ ] Fail
Notes: _________________________

Test 2: Medium Response
Question: "Explain photosynthesis"
First Video Time: _____s
Total Time: _____s
Videos Generated: _____
Result: [ ] Pass [ ] Fail
Notes: _________________________

Test 3: Long Response
Question: "What are the differences between India and Pakistan?"
First Video Time: _____s
Total Time: _____s
Videos Generated: _____
Result: [ ] Pass [ ] Fail
Notes: _________________________

Performance Metrics:
- Average First Video: _____s
- Average Total Time: _____s
- GPU Memory Usage: _____GB
- CPU Usage: _____%

Issues Found:
1. _________________________
2. _________________________

Overall Assessment: [ ] Pass [ ] Fail
```

## 🎉 Success Indicators

You'll know it's working when:

1. You open http://localhost:3000
2. Click "Start" and speak a question
3. Within 10 seconds, you see a video of the avatar responding
4. The avatar's lips sync with the speech
5. The response is clear and natural
6. Metrics show first video time <10s

---

**Happy Testing!** 🚀

For issues or questions, check:
- Backend logs: `/tmp/backend_*.log`
- Frontend logs: `/tmp/frontend.log`
- Generated videos: `backend/generated_videos/parallel/`
- Documentation: `PARALLEL_PIPELINE_GUIDE.md`

