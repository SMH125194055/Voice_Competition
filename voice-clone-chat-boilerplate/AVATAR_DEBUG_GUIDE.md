# 🐛 Avatar Debug Guide

## Changes Made

### 1. Fixed Video Element (Frontend)
- ✅ Set `muted={true}` (TTS audio plays separately)
- ✅ Added `autoPlay` attribute
- ✅ Added `onLoadedData` and `onError` event handlers
- ✅ Added extensive console logging

### 2. Enhanced Debugging
- ✅ Base64 decoding logs
- ✅ Blob creation logs
- ✅ Video URL creation logs
- ✅ Video element state logs

## How to Test

### 1. Open Browser Console (F12)

### 2. Start a Conversation
- Enable Avatar in settings
- Upload/select reference picture
- Click Start and speak

### 3. Watch for These Console Messages

**Avatar Generation Start:**
```
🎬 Avatar generation started in parallel...
```

**Avatar Video Ready:**
```
✅ Avatar video ready! Size: XXXXX bytes (base64)
🔄 Converting base64 to blob...
✅ Base64 decoded, length: XXXXX
✅ Blob created, size: XXXXX bytes, type: video/mp4
✅ Video URL created: blob:http://...
✅ Avatar state updated with video URL
🎬 Setting video element src...
🎬 Avatar video element configured
```

**Video Loading:**
```
🎬 Avatar video loaded and ready
```

**Audio Playback:**
```
🔊 Audio playing
🎬 Avatar video playing with audio
```

## Common Issues & Solutions

### Issue 1: "Avatar video ref not available yet"
**Symptom:** `⚠️ Avatar video ref not available yet` in console
**Cause:** Video element not rendered when avatar data arrives
**Solution:** This is normal, video will appear on next render

### Issue 2: "Avatar video autoplay may be blocked"
**Symptom:** `⚠️ Avatar video autoplay may be blocked` in console
**Cause:** Browser autoplay policy
**Solution:** User interaction (clicking Start) should allow it

### Issue 3: "Avatar video error"
**Symptom:** `❌ Avatar video error` in console
**Cause:** Invalid video blob or codec issue
**Solution:** Check if video file is valid MP4

### Issue 4: No Avatar Visible
**Possible Causes:**
1. `avatarVideoUrl` state not set
2. Video element not rendering
3. CSS z-index issue
4. Blob URL invalid

**Debug Steps:**
1. Check console for avatar logs
2. Check React DevTools for `avatarVideoUrl` state
3. Inspect element to see if `<video>` tag exists
4. Check Network tab for `avatar_complete` event

## Expected Behavior

1. **User speaks** → "🎤 Listening..."
2. **Processing** → "📝 Transcribing..."
3. **LLM Response** → "🤖 Thinking..."
4. **Audio Starts** → "🔊 Speaking (1/5)..."
5. **Avatar Generating** → `🎬` emoji shows (background)
6. **Avatar Ready** → Video replaces 🤖 emoji
7. **Playback** → Video plays with audio chunks

## Debugging Commands

### In Browser Console:
```javascript
// Check if avatar state is set
console.log('Avatar URL:', document.querySelector('.avatar-video')?.src);

// Check if video element exists
console.log('Video element:', document.querySelector('.avatar-video'));

// Check video ready state
const video = document.querySelector('.avatar-video');
if (video) {
  console.log('Ready state:', video.readyState);
  console.log('Paused:', video.paused);
  console.log('Current time:', video.currentTime);
  console.log('Duration:', video.duration);
}

// Force play
document.querySelector('.avatar-video')?.play();
```

## What Should You See

### In the UI:
1. Settings panel with "Avatar Generation" toggle
2. Reference Picture upload button
3. During generation: 🎬 emoji in AI circle
4. When ready: Video in AI circle (circular, 200x200px)
5. Video should be looping and synced with audio

### In Console:
- Lots of avatar-related logs
- No errors about video loading
- "Avatar video playing with audio" messages

## Still Not Working?

### Check These Files:
1. `VADVoiceAgent.js` - Frontend component
2. `main.py` - Backend avatar generation
3. `avatar_config.py` - Avatar settings

### Verify:
1. Backend is sending avatar_complete event
2. Event contains `video` field with base64 data
3. Frontend is receiving the event
4. Base64 is being decoded correctly
5. Blob is being created
6. Video element is rendering
7. Video src is being set

### Network Tab:
1. Check `/vad-chat-avatar-stream` response
2. Look for `avatar_complete` event
3. Verify it has `video` data (very large base64 string)

---

**If you see all the console logs but no video, the issue is likely in the React rendering or CSS. Check React DevTools!**

**If you don't see avatar logs, the backend might not be sending the data properly.**

**Last updated:** October 15, 2025


