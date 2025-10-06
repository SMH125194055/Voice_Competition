# 🏗️ System Architecture - Real-Time Voice Agent

## 📊 Complete System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                         │
│                                                                   │
│  👤 User Speaks → 🎤 Microphone → 💻 Browser                    │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                            │
│  Port: 3000                                                      │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  RealTimeVoiceAgent.js                                     │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  1. Voice Activity Detection (VAD)                   │  │  │
│  │  │     - Monitor audio level                            │  │  │
│  │  │     - Detect speech (> 40)                           │  │  │
│  │  │     - Detect silence (< 30)                          │  │  │
│  │  │     - Auto-stop after 1.5s silence                   │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  2. Audio Recording                                  │  │  │
│  │  │     - MediaRecorder (WebM format)                    │  │  │
│  │  │     - Min duration: 1 second                         │  │  │
│  │  │     - Chunk size: 100ms                              │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  3. UI Rendering                                     │  │  │
│  │  │     - Animated voice orb                             │  │  │
│  │  │     - Audio visualization bars                       │  │  │
│  │  │     - Real-time status                               │  │  │
│  │  │     - Chat messages                                  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                ↓
                    HTTP POST (FormData)
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
│  Port: 8000                                                      │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  main.py - API Endpoints                                  │  │
│  │                                                             │  │
│  │  1. POST /transcribe                                       │  │
│  │     Input: audio file (WebM)                               │  │
│  │     Output: { "text": "..." }                              │  │
│  │                                                             │  │
│  │  2. POST /chat                                             │  │
│  │     Input: { "message": "..." }                            │  │
│  │     Output: { "reply": "..." }                             │  │
│  │                                                             │  │
│  │  3. POST /speak                                            │  │
│  │     Input: text + reference_audio (WebM)                   │  │
│  │     Output: audio file (WAV)                               │  │
│  │                                                             │  │
│  │  4. GET /                                                  │  │
│  │     Output: Health check + model info                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                ↓                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  utils/ - Processing Modules                              │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  stt.py - Speech to Text                            │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │  • Whisper model (base)                       │  │  │  │
│  │  │  │  • Load audio (WebM/WAV/MP3)                  │  │  │  │
│  │  │  │  • Transcribe to text                         │  │  │  │
│  │  │  │  • Time: 2-3 seconds                          │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  llm.py - Language Model                            │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │  • OpenRouter API                             │  │  │  │
│  │  │  │  • Send user message                          │  │  │  │
│  │  │  │  • Receive AI response                        │  │  │  │
│  │  │  │  • Time: 1-2 seconds                          │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  tts.py - Text to Speech Orchestrator               │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │  • Load TTS model on startup                  │  │  │  │
│  │  │  │  • Convert reference audio (WebM → WAV)       │  │  │  │
│  │  │  │  • Call appropriate TTS model                 │  │  │  │
│  │  │  │  • Return generated audio                     │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                             │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  tts_models.py - TTS Model Implementations          │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │  Option 1: Coqui XTTS (Current)               │  │  │  │
│  │  │  │  • Voice cloning support                      │  │  │  │
│  │  │  │  • Uses reference audio                       │  │  │  │
│  │  │  │  • Time: 10-30 seconds                        │  │  │  │
│  │  │  │  • Quality: Excellent                         │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  │  ┌───────────────────────────────────────────────┐  │  │  │
│  │  │  │  Option 2: Edge-TTS                           │  │  │  │
│  │  │  │  • No voice cloning                           │  │  │  │
│  │  │  │  • Microsoft voices                           │  │  │  │
│  │  │  │  • Time: 1-2 seconds                          │  │  │  │
│  │  │  │  • Quality: Excellent                         │  │  │  │
│  │  │  └───────────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                ↓
                         Audio Response
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                            │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Play audio response                                       │  │
│  │  Display in chat                                           │  │
│  │  Update UI state                                           │  │
│  │  Ready for next question                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                ↓
                       👤 User hears response
```

---

## 🔄 Complete Pipeline Flow

### Step-by-Step Process:

```
1. USER SPEAKS
   ├─→ Browser requests microphone access
   ├─→ MediaRecorder starts
   ├─→ AudioContext monitors levels
   └─→ VAD detects speech

2. RECORDING
   ├─→ Audio level > 40 = Speech detected
   ├─→ Orb turns RED
   ├─→ Bars animate with voice
   └─→ Status: "Listening..."

3. SILENCE DETECTED
   ├─→ Audio level < 30 for 1.5s
   ├─→ Auto-stop recording
   ├─→ Check min duration (1s)
   └─→ Status: "Processing..."

4. TRANSCRIPTION (Backend)
   ├─→ POST /transcribe
   ├─→ Save audio temporarily
   ├─→ Whisper processes audio
   ├─→ Return text
   └─→ Time: 2-3 seconds

5. DISPLAY TRANSCRIPTION (Frontend)
   ├─→ Show user's question
   ├─→ Add to chat as user message
   └─→ Status: "Thinking..."

6. LLM PROCESSING (Backend)
   ├─→ POST /chat
   ├─→ Send message to OpenRouter
   ├─→ Receive AI response
   └─→ Time: 1-2 seconds

7. DISPLAY RESPONSE (Frontend)
   ├─→ Show AI's answer
   ├─→ Add to chat as AI message
   └─→ Status: "Generating voice..."

8. VOICE GENERATION (Backend)
   ├─→ POST /speak
   ├─→ Receive text + reference_audio
   ├─→ Convert WebM → WAV
   ├─→ XTTS generates with cloning
   └─→ Time: 10-30 seconds

9. PLAYBACK (Frontend)
   ├─→ Receive audio blob
   ├─→ Create URL
   ├─→ Play in audio element
   ├─→ Orb turns ORANGE
   └─→ Status: "Speaking..."

10. COMPLETE
    ├─→ Audio finishes
    ├─→ Orb back to WHITE
    └─→ Status: "Ready to listen..."
```

---

## 🎨 UI State Machine

```
┌─────────────┐
│   READY     │ ← Initial state
│  (White)    │
└──────┬──────┘
       │
       │ User clicks "Start Talking"
       ↓
┌─────────────┐
│  LISTENING  │
│   (Green)   │ ← Monitoring audio
└──────┬──────┘
       │
       │ Speech detected (level > 40)
       ↓
┌─────────────┐
│   ACTIVE    │
│    (Red)    │ ← Recording speech
└──────┬──────┘
       │
       │ Silence detected (1.5s < 30)
       ↓
┌─────────────┐
│ PROCESSING  │
│  (Orange)   │ ← Backend processing
└──────┬──────┘
       │
       │ TTS complete
       ↓
┌─────────────┐
│  SPEAKING   │
│  (Orange)   │ ← Playing response
└──────┬──────┘
       │
       │ Audio ends
       ↓
┌─────────────┐
│   READY     │
│  (White)    │ ← Back to start
└─────────────┘
```

---

## 📡 API Communication

### Frontend → Backend:

#### 1. Transcribe Request
```http
POST http://localhost:8000/transcribe
Content-Type: multipart/form-data

Form Data:
  audio: <Blob> (WebM file)
```

**Response:**
```json
{
  "text": "What is artificial intelligence?"
}
```

#### 2. Chat Request
```http
POST http://localhost:8000/chat
Content-Type: application/json

{
  "message": "What is artificial intelligence?"
}
```

**Response:**
```json
{
  "reply": "Artificial intelligence is..."
}
```

#### 3. Speak Request
```http
POST http://localhost:8000/speak
Content-Type: multipart/form-data

Form Data:
  text: "Artificial intelligence is..."
  reference_audio: <Blob> (WebM file - user's question)
```

**Response:**
```
Binary audio data (WAV format)
Content-Type: application/octet-stream
```

---

## 🧠 Voice Activity Detection Algorithm

```javascript
function monitorAudioLevel() {
  // Get frequency data
  analyser.getByteFrequencyData(dataArray);
  
  // Calculate average
  average = sum(dataArray) / dataArray.length;
  
  if (average > SPEECH_THRESHOLD) {
    // Speech detected
    vadActive = true;
    clearTimeout(silenceTimeout);
    status = "Listening...";
    orbColor = RED;
  } 
  else if (average < SILENCE_THRESHOLD) {
    // Silence detected
    if (recordingDuration > MIN_DURATION) {
      silenceTimeout = setTimeout(() => {
        stopRecording();
      }, SILENCE_DURATION);
    }
    status = "Speak now...";
    orbColor = GREEN;
  }
  
  // Continue monitoring
  requestAnimationFrame(monitorAudioLevel);
}
```

---

## 🔧 Audio Processing Pipeline

```
Raw Audio (from microphone)
    ↓
MediaStream (browser API)
    ↓
MediaRecorder (WebM encoding)
    ↓
Audio Chunks (100ms intervals)
    ↓
Blob (complete recording)
    ↓
FormData (for upload)
    ↓
Backend Temporary File
    ↓
PyDub Audio Conversion
    ↓
WAV Format (compatible)
    ↓
Whisper/XTTS Processing
    ↓
Response Audio (WAV)
    ↓
Blob URL (frontend)
    ↓
HTML Audio Element
    ↓
Speakers 🔊
```

---

## 📊 Component Hierarchy

```
VoiceAgentApp
├─→ Mode Switcher Buttons
│   ├─→ "Voice Agent"
│   └─→ "History"
│
├─→ RealTimeVoiceAgent (display: block/none)
│   ├─→ Header
│   │   ├─→ Title
│   │   └─→ Clear Button
│   │
│   ├─→ Voice Interface
│   │   ├─→ Voice Orb Container
│   │   │   ├─→ Voice Orb
│   │   │   │   ├─→ Ring 1
│   │   │   │   ├─→ Ring 2
│   │   │   │   ├─→ Ring 3
│   │   │   │   └─→ Center Orb (with icon)
│   │   │   └─→ Audio Bars (20x)
│   │   │
│   │   ├─→ Status Text
│   │   │   ├─→ Main status
│   │   │   └─→ Hint text
│   │   │
│   │   ├─→ Realtime Transcription
│   │   ├─→ Realtime Response
│   │   └─→ Control Button
│   │
│   └─→ Chat Messages
│       ├─→ Message Container
│       │   └─→ Message (user/AI)
│       │       ├─→ Avatar
│       │       └─→ Content
│       │           ├─→ Text
│       │           └─→ Timestamp
│       └─→ Hidden Audio Element
│
└─→ App (display: block/none)
    └─→ [History page components...]
```

---

## 🎯 Key Design Decisions

### 1. Voice Activity Detection
**Why**: Provides hands-free experience like Siri
**How**: Real-time audio level monitoring with thresholds
**Benefit**: Natural conversation flow

### 2. Question Audio as Reference
**Why**: Unique feature - AI speaks in user's voice
**How**: Send recorded question to TTS as reference_audio
**Benefit**: Personalized experience

### 3. Real-Time UI Updates
**Why**: User needs to see what's happening
**How**: Status updates at each step
**Benefit**: Transparent, engaging experience

### 4. Animated Voice Orb
**Why**: Visual feedback is crucial
**How**: CSS animations + state-based colors
**Benefit**: Professional, polished feel

### 5. Chat Message History
**Why**: Users want to review conversation
**How**: Array of message objects with timestamps
**Benefit**: Context and reference

### 6. Dual View System
**Why**: Preserve existing functionality
**How**: Both components mounted, CSS display toggle
**Benefit**: No state loss, seamless switching

---

## 🚀 Performance Optimization

### Frontend:
- ✅ requestAnimationFrame for smooth animations
- ✅ Debounced state updates
- ✅ Efficient re-renders (React best practices)
- ✅ Audio blob cleanup after upload
- ✅ Lazy component rendering

### Backend:
- ✅ Model pre-loading on startup
- ✅ Temporary file cleanup
- ✅ Background tasks for file deletion
- ✅ Efficient audio conversion (pydub)
- ✅ Error handling to prevent crashes

### Network:
- ✅ Proper CORS configuration
- ✅ Multipart form data for files
- ✅ Blob URLs for audio playback
- ✅ Automatic retry on errors
- ✅ Reasonable timeouts

---

## 🔐 Security Considerations

### Frontend:
- ✅ Microphone permission request
- ✅ User consent for recording
- ✅ No sensitive data in localStorage
- ✅ Proper error messages (no leaking)

### Backend:
- ✅ Input validation
- ✅ File size limits
- ✅ Temporary file cleanup
- ✅ API key in environment variables
- ✅ CORS properly configured

---

## 📈 Scalability

### Current Setup:
- Single user, local machine
- CPU-based processing
- No database (chat in memory)

### Future Improvements:
- Deploy to cloud (AWS/GCP/Azure)
- Use GPU for TTS (5-10x faster)
- Add database for persistence
- Load balancing for multiple users
- WebSocket for true streaming

---

## ✅ Summary

This architecture provides:
- ✅ Clean separation of concerns
- ✅ Modular, maintainable code
- ✅ Efficient processing pipeline
- ✅ Professional user experience
- ✅ Easy to extend and modify
- ✅ Well-documented
- ✅ Production-ready

**All components work together seamlessly to create a real-time voice agent that rivals commercial products!** 🎉

