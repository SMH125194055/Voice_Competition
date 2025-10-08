# WebM Recording Issues - Complete Fix & Guide

## The Problem

You're getting this FFmpeg error:
```
[matroska,webm @ ...] EBML header parsing failed
Error opening input: Invalid data found when processing input
```

This means the WebM audio file is **corrupted** - it doesn't have a valid WebM container header.

## Root Causes

### 1. Recording Too Short (Most Common) ⏱️
- WebM format needs time to:
  - Initialize the audio encoder
  - Write EBML (container) headers
  - Write Segment headers
  - Write Track information
  - Write at least one Cluster (audio data)
- Minimum: **~300-500ms** just for headers
- **Safe minimum: 1.5 seconds** to ensure valid file

### 2. Browser Not Flushing Data
- `MediaRecorder` might buffer data
- Without explicit `timeslice`, data might not be written properly
- We use `start(100)` to force data flush every 100ms

### 3. Microphone Issues
- No audio captured = invalid WebM
- Muted microphone = headers only, no data
- Wrong input device selected

## Complete Solution Implemented

### 1. Real-Time Recording Duration Display ⏲️

**What**: Button now shows live timer while recording
```javascript
// Button text updates every 100ms
🎤 Recording... 0.3s
🎤 Recording... 0.8s
🎤 Recording... 1.5s ✓ (safe to release)
```

**Why**: Gives you visual feedback to know when it's safe to release

### 2. Minimum Duration: 1 Second (1000ms)

**What**: Recording must be at least 1 second
```javascript
if (recordingDuration < 1000) {
  setStatus('⚠️ Too short! Hold for at least 1.5 seconds');
  return; // Don't send to backend
}
```

**Why**: Ensures WebM container is fully formed

### 3. Minimum File Size: 2000 Bytes

**What**: Audio blob must be at least 2KB
```javascript
if (audioBlob.size < 2000) {
  setStatus('⚠️ Recording failed - no audio captured');
  return; // Don't send to backend
}
```

**Why**: 
- Valid WebM headers: ~200-500 bytes
- Minimum audio data: ~1500 bytes
- Total: ~2000 bytes minimum

### 4. Enhanced Debug Logging

**What**: Console shows detailed recording info
```javascript
console.log(`Received chunk: ${event.data.size} bytes`);
console.log(`Recording complete: ${duration}ms, Blob: ${size} bytes, Chunks: ${count}`);
```

**Why**: Helps diagnose issues - you can see exactly what's happening

### 5. Data Request Every 100ms

**What**: Force MediaRecorder to flush data regularly
```javascript
mediaRecorderRef.current.start(100); // Request data every 100ms
```

**Why**: 
- Ensures `ondataavailable` fires regularly
- Prevents buffering issues
- Creates proper WebM structure with multiple chunks

## How to Use

### Step 1: Restart Frontend
```bash
cd frontend/voice-ui
# If already running, press Ctrl+C first
npm start
```

The app should auto-reload in your browser.

### Step 2: Setup Your Voice (Once)
1. Click "🎙️ Setup My Voice (5s)"
2. Speak clearly for 5 seconds
3. Click "OK" when done

### Step 3: Record Your Question

**IMPORTANT: Hold the button for at least 1.5-2 seconds!**

1. **PRESS AND HOLD** the "🎤 Hold to Talk" button
2. **WATCH THE TIMER**: It will show "🎤 Recording... 0.3s", "0.8s", "1.2s", etc.
3. **SPEAK YOUR QUESTION**: "What is the weather today?"
4. **WAIT FOR 1.5+ SECONDS** (watch the timer!)
5. **RELEASE** when done

### Example Timeline:
```
0.0s - Press button, start speaking
0.3s - Still recording (too short!)
0.8s - Still recording (too short!)
1.2s - Safe to release now ✓
1.5s - Better - more audio captured ✓✓
2.0s - Ideal for full question ✓✓✓
```

## Troubleshooting

### ❌ Still Getting "EBML header parsing failed"

**Check Browser Console** (Press F12):

#### Expected (Good):
```
Received chunk: 4523 bytes
Received chunk: 4234 bytes
Received chunk: 4156 bytes
Recording complete: 2300ms, Blob size: 23456 bytes, Chunks: 23
```
- Duration: > 1000ms ✓
- Blob size: > 2000 bytes ✓
- Multiple chunks: > 10 ✓

#### Problem Signs:
```
Recording complete: 800ms, Blob size: 245 bytes, Chunks: 2
```
- Duration too short (< 1000ms) ❌
- Blob too small (< 2000 bytes) ❌
- Too few chunks (< 5) ❌

**Solution**: Hold the button **longer** (2-3 seconds)

### ❌ "Recording failed - no audio captured"

**Possible Causes**:

1. **Microphone Muted**
   - Check: System tray icon (Windows)
   - Check: System Settings → Sound → Input
   - Test: Record in Windows Voice Recorder app

2. **Wrong Input Device**
   - Open: chrome://settings/content/microphone
   - Select: Correct microphone
   - Test: Allow microphone access

3. **No Permission**
   - Browser asks permission on first use
   - If denied: chrome://settings/content/microphone
   - Reset permissions for localhost

4. **Microphone Not Working**
   - Test: Windows Settings → Sound → Test your microphone
   - Check: Device Manager → Audio inputs
   - Try: Different USB port (if USB mic)

### ❌ Recording Shows 0 Chunks

**Console Shows**:
```
Recording complete: 1500ms, Blob size: 0 bytes, Chunks: 0
```

**Causes**:
- MediaRecorder failed to initialize
- Browser compatibility issue
- Codec not supported

**Solutions**:

1. **Update Browser**:
   - Chrome: Latest version (recommended)
   - Edge: Latest version (recommended)
   - Firefox: May have WebM issues on Windows

2. **Check Supported Formats**:
   ```javascript
   // Paste in browser console
   console.log(MediaRecorder.isTypeSupported('audio/webm'));
   // Should show: true
   ```

3. **Try Different Browser**:
   - Chrome usually has best WebM support
   - Edge (Chromium) also works well
   - Avoid older browsers

## Backend Verification

Check backend terminal logs:

### ✓ Good Recording:
```
INFO: Received audio with content type: audio/webm;codecs=opus
INFO: Received 23456 bytes of audio data
INFO: Saved audio to: C:\...\tmpxxxxx.webm
INFO: Transcribing audio file: ...
INFO: Transcription result: What is the weather today?
```

### ❌ Bad Recording:
```
INFO: Received 245 bytes of audio data
ERROR: Failed to load audio: EBML header parsing failed
```

## Pro Tips

### 1. Practice the Timing ⏱️
- First few tries, aim for 2-3 seconds
- Watch the timer to get a feel for the duration
- Once comfortable, can go shorter (but always > 1.5s)

### 2. Use Full Sentences 📝
- Instead of: "Weather?" (too short)
- Say: "What is the weather today?" (better)
- Or: "Can you tell me what the weather is like today?" (ideal)

### 3. Check Visual Feedback 👀
- Voice orb pulses when listening
- Status shows "🎤 Recording..."
- Button shows live timer
- Release only when timer shows > 1.5s

### 4. Microphone Testing 🎙️
Before recording:
1. Windows: Test in Settings → Sound
2. Online: Use https://mictests.com
3. Ensure input level shows when speaking

### 5. Browser Console is Your Friend 🔍
- Keep it open (F12)
- Watch for errors
- Check chunk sizes
- Verify blob sizes

## Technical Details

### Valid WebM File Structure:
```
EBML Header (30-50 bytes)
  ├─ EBML magic number (0x1A45DFA3)
  ├─ Version info
  └─ DocType: "webm"

Segment (rest of file)
  ├─ SeekHead (optional)
  ├─ SegmentInfo (~20-40 bytes)
  │   ├─ TimecodeScale
  │   └─ Duration
  ├─ Tracks (~100-200 bytes)
  │   └─ TrackEntry
  │       ├─ TrackType: Audio
  │       ├─ Codec: Opus
  │       └─ SampleRate, Channels
  └─ Cluster (audio data, variable size)
      ├─ Timecode
      └─ SimpleBlock(s) - actual audio samples
```

**Minimum for valid file**: ~300-500 bytes (headers only, no audio)
**Minimum for usable file**: ~2000 bytes (headers + actual audio)

### Why 100ms Timeslice Works:
```javascript
mediaRecorder.start(100); // Request data every 100ms

// Timeline:
// 0ms:   Recording starts
// 100ms: ondataavailable fires → chunk 1
// 200ms: ondataavailable fires → chunk 2
// 300ms: ondataavailable fires → chunk 3
// ...
// 1500ms: ondataavailable fires → chunk 15
// Stop:  ondataavailable fires → final chunk
```

Result: 
- Multiple small chunks instead of one large chunk
- Each chunk is properly formed
- WebM container is incrementally built
- More reliable across browsers

## Summary

### ✅ DO:
- Hold button for **2-3 seconds** (safe duration)
- Watch the **timer** on the button
- Speak **full sentences**
- Wait for **1.5+ seconds** minimum
- Check **browser console** for debugging

### ❌ DON'T:
- Tap the button quickly (< 1 second)
- Release before timer shows 1.5s
- Speak without checking microphone works
- Use outdated browser
- Ignore error messages in console

### 🎯 Goal:
- Timer shows: **1.5s+** when releasing
- Console shows: **> 2000 bytes, > 10 chunks**
- Backend receives: **valid WebM file**
- Whisper transcribes: **your question correctly**

---

**Still having issues?** Share:
1. Browser console logs (recording complete line)
2. Backend terminal error
3. Browser version
4. How long you held the button

This will help diagnose the specific issue!





