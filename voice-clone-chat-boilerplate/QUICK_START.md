# 🚀 Quick Start Guide - Real-Time Voice Agent

## ⚡ Get Started in 3 Steps

### Step 1: Start Backend (Terminal 1)
```bash
cd voice-clone-chat-boilerplate/backend

# Activate virtual environment (if not already)
.\venv\Scripts\activate

# Start server
uvicorn main:app --reload --port 8000
```

**Wait for this message:**
```
INFO: Coqui XTTS model loaded successfully
INFO: Application startup complete
```

⏱️ **Takes**: ~40-60 seconds (XTTS model loading)

---

### Step 2: Start Frontend (Terminal 2)
```bash
cd voice-clone-chat-boilerplate/frontend/voice-ui

# Start React app
npm start
```

**Browser opens automatically**: http://localhost:3000/

⏱️ **Takes**: ~10-15 seconds

---

### Step 3: Try It!

1. **Click "Start Talking"** 🎤
2. **Speak your question** (e.g., "What is artificial intelligence?")
3. **Watch the magic:**
   - ✅ Auto-stops when you pause
   - ✅ Transcribes your speech
   - ✅ Gets AI response
   - ✅ Speaks back in YOUR voice!

---

## 🎯 What You'll See

### Voice Agent View (Default)
- **Animated voice orb** - Changes color based on state
- **Audio visualization** - Bars that react to your voice
- **Real-time status** - "Listening...", "Processing...", etc.
- **Chat history** - All your conversations

### History View (Switch views)
- **Previous conversations** - Full history from before
- **Reference voice management** - Change reference audio
- **Manual controls** - Record, send, play

---

## ✨ Cool Features to Try

### 1. Voice Activity Detection
- **No button holding!** Just speak and pause
- **Auto-stops** after 1.5 seconds of silence
- **Visual feedback** - Orb turns red when detecting speech

### 2. Voice Cloning
- **Your voice** is used as reference automatically
- **AI speaks like you** - Unique feature!
- **No setup needed** - Works from first question

### 3. Real-Time Feedback
- **Live transcription** appears as you speak
- **Status updates** at every step
- **Smooth animations** for professional feel

### 4. Chat History
- **All messages saved** - User and AI
- **Timestamps** for each message
- **Scrollable** - Easy to review

---

## 🎨 UI States

| You'll See | What It Means |
|------------|---------------|
| 💬 White orb | Ready to listen |
| 🎤 Green orb | Listening for speech |
| 🎤 Red orb + pulse | Detecting your voice! |
| 🔄 Orange + spinner | Processing your request |
| 🔊 Orange orb | AI speaking |

---

## ⏱️ Expected Timing

**Full Interaction:**
1. **Recording**: 3-5 seconds (depends on your question length)
2. **Transcription**: 2-3 seconds
3. **LLM Response**: 1-2 seconds
4. **Voice Generation**: 10-30 seconds (with cloning)
5. **TOTAL**: ~15-40 seconds

**Want it faster?**
Switch to Edge-TTS (no cloning, but 2-3s generation):
```env
# In backend/.env
TTS_MODEL=fast
```

---

## 🐛 Quick Fixes

### "Microphone access denied"
→ Click the 🔒 lock icon in browser address bar → Allow microphone

### "Recording too short"
→ Speak for at least 2 seconds, don't release too quickly

### "Backend not running"
→ Check Terminal 1 shows "Application startup complete"

### "Nothing happens"
→ Check browser console (F12) for errors

---

## 🎯 Test Questions to Try

**Short & Sweet:**
- "What is AI?"
- "Tell me a joke"
- "What's the weather like?"

**Longer Conversations:**
- "Explain quantum computing in simple terms"
- "What are the benefits of meditation?"
- "How does photosynthesis work?"

**Follow-ups:**
- Ask a question, then ask "Can you explain that differently?"
- Build on previous responses

---

## 📱 Mobile Testing

Works on mobile browsers!
1. Open http://localhost:3000/ on your phone
2. Make sure phone and computer are on same network
3. Use computer's local IP instead of localhost

**Example:**
```
http://192.168.1.100:3000
```

---

## ⚙️ Configuration

### Switch TTS Model
Edit `backend/.env`:
```env
# For voice cloning (slow but uses your voice)
TTS_MODEL=xtts

# For speed (fast but generic voice)
TTS_MODEL=fast
```

Restart backend after changing.

### Change Voice (Fast Mode)
```env
TTS_MODEL=fast
FAST_TTS_VOICE=en-US-AriaNeural  # Female
# or
FAST_TTS_VOICE=en-US-GuyNeural   # Male
```

---

## 🎉 You're Ready!

That's it! You now have a working real-time voice agent with:
- ✅ Automatic voice detection
- ✅ Real-time transcription
- ✅ AI responses
- ✅ Voice cloning (speaks in YOUR voice!)
- ✅ Beautiful, animated UI
- ✅ Chat history

**Have fun talking to your AI assistant!** 🚀

---

## 📚 More Info

- **Full Documentation**: See `REALTIME_VOICE_AGENT_COMPLETE.md`
- **Troubleshooting**: Check the troubleshooting section in docs
- **Advanced Features**: Coming soon!

---

## 💡 Pro Tips

1. **Speak clearly** for best transcription
2. **Pause naturally** to let VAD detect silence
3. **Good microphone** = better results
4. **Quiet environment** = clearer recordings
5. **First response takes longer** (models warming up)
6. **Subsequent responses faster** (models cached)

Enjoy! 🎤✨

