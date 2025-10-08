# 🚀 Quick Start - VAD Voice Agent

## Prerequisites Check

Before starting, ensure you have:
- ✅ Python 3.8+ installed
- ✅ Node.js 14+ and npm installed
- ✅ Microphone connected and working
- ✅ Internet connection (for LLM API)

## 1️⃣ Start Backend (Terminal 1)

```bash
# Navigate to backend
cd voice-clone-chat-boilerplate/backend

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install VAD dependencies (if not already installed)
pip install torch torchaudio pydub

# Start the server
python main.py
```

**Expected Output:**
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Silero VAD loaded successfully
INFO:     VAD model loaded on cpu
```

**Verify Backend:**
Open browser to `http://localhost:8000`

Should see:
```json
{
  "status": "running",
  "vad_enabled": true,
  "endpoints": ["/transcribe", "/chat", "/speak", "/chat-voice", "/vad-transcribe", "/detect-speech", "/vad-chat-voice"]
}
```

## 2️⃣ Start Frontend (Terminal 2)

```bash
# Navigate to frontend
cd voice-clone-chat-boilerplate/frontend/voice-ui

# Start development server
npm start
```

**Expected Output:**
```
Compiled successfully!
You can now view voice-ui in the browser.
  Local:            http://localhost:3000
```

## 3️⃣ Test the VAD Agent

### Step 1: Open Application
1. Browser should open automatically to `http://localhost:3000`
2. If not, manually open `http://localhost:3000`

### Step 2: Select VAD Mode
1. Look for buttons at top right
2. Click **"🎯 VAD Agent"** (should be selected by default)
3. Wait for status: **"Ready! Click Start to begin"**

### Step 3: First Test
1. Click **"Start Listening"** button
2. Wait for **"Listening for speech..."**
3. Say: **"Hello, can you hear me?"**
4. **Pause for 1-2 seconds**
5. System should automatically:
   - Detect speech ended
   - Show "Processing speech..."
   - Transcribe your speech
   - Get AI response
   - Speak the response

### Step 4: Verify Features

**✅ Automatic Speech Detection:**
- User orb (left) lights up blue when you speak
- No need to click stop
- Automatically detects pause

**✅ Visual Feedback:**
- Connection line animates during processing
- AI orb shows thinking (golden) then speaking (purple)
- Status messages update in real-time

**✅ Conversation Flow:**
- Messages appear in conversation history
- Timestamps included
- User messages (right, blue)
- AI messages (left, purple)

**✅ Audio Playback:**
- AI speaks response automatically
- Can mute with 🔊 button at top
- Speaking animation syncs with audio

### Step 5: Continue Conversation
1. After AI finishes, status returns to **"Listening for speech..."**
2. Just speak again - completely hands-free!
3. Try: **"Tell me a joke"**
4. Pause naturally
5. System processes automatically

## 🎯 Quick Test Phrases

Try these to test different scenarios:

1. **Short phrase:** "Hello"
2. **Question:** "What's the weather like?"
3. **Multi-sentence:** "I like pizza. What about you?"
4. **Long pause test:** Say "Testing..." then pause 3 seconds
5. **Continuous:** Ask multiple questions in sequence

## ✅ Verification Checklist

### Backend ✓
- [ ] Server starts without errors
- [ ] `http://localhost:8000` shows status
- [ ] `vad_enabled: true` in response
- [ ] Logs show "Silero VAD loaded successfully"

### Frontend ✓
- [ ] Application loads at `http://localhost:3000`
- [ ] Three mode buttons visible (VAD Agent, Voice Agent, History)
- [ ] VAD Agent selected by default
- [ ] Status shows "Ready! Click Start to begin"

### VAD Functionality ✓
- [ ] "Start Listening" button works
- [ ] Microphone permission granted
- [ ] VAD model loads (may take 5-10 seconds first time)
- [ ] Status changes to "Listening for speech..."
- [ ] User orb lights up when speaking
- [ ] Automatically detects speech end
- [ ] Processes and transcribes correctly

### Full Pipeline ✓
- [ ] Speech transcribed correctly
- [ ] AI generates relevant response
- [ ] AI voice plays automatically
- [ ] AI orb animates during speaking
- [ ] Conversation history updates
- [ ] Can continue conversation seamlessly

### Controls ✓
- [ ] Mute button works (🔊/🔇)
- [ ] Clear chat button works
- [ ] Can switch between modes
- [ ] Stop listening works

## 🐛 Common Issues & Solutions

### Issue: "VAD initialization failed"
**Solution:** 
- Refresh the page
- Clear browser cache
- Check browser console for errors

### Issue: "No speech detected in audio"
**Solution:**
- Speak louder
- Speak longer (at least 1 second)
- Check microphone is working
- Try different microphone

### Issue: Backend not responding
**Solution:**
```bash
# Check if backend is running
curl http://localhost:8000

# Restart backend
# Press Ctrl+C to stop
# Then: python main.py
```

### Issue: Microphone permission denied
**Solution:**
- Check browser settings
- Allow microphone access
- On Chrome: Settings → Privacy → Site Settings → Microphone
- Refresh page after granting permission

### Issue: VAD model loading takes forever
**Solution:**
- First load can take 10-30 seconds (downloads model)
- Check internet connection
- Model is cached after first load
- Check browser console for progress

### Issue: Audio not playing
**Solution:**
- Check if muted (🔇)
- Check browser volume
- Check system volume
- Open browser console for errors

## 📊 Testing Different Scenarios

### Test 1: Natural Conversation
```
You: "Hi, how are you?"
[Pause naturally]
AI: [Responds]

You: "Tell me something interesting"
[Pause naturally]
AI: [Responds]
```

### Test 2: Quick Responses
```
You: "Yes"
[Pause]
AI: [Responds]

You: "No"
[Pause]
AI: [Responds]
```

### Test 3: Long Statement
```
You: "I want to know about artificial intelligence, machine learning, and how they're changing the world."
[Pause]
AI: [Responds with detailed answer]
```

### Test 4: Multiple Questions
```
You: "What's your favorite color? And why?"
[Pause - VAD detects question end with pause]
AI: [Responds to both]
```

## 🎨 Visual Reference

**Idle State:**
```
👤 (You)  ————  🤖 (AI)
  Blue           Purple
  Static         Static
```

**You Speaking:**
```
👤 (You)  ————  🤖 (AI)
💙 Pulsing      Static
  Rings          Waiting
```

**AI Thinking:**
```
👤 (You)  ⚡⚡⚡  🤖 (AI)
  Static      ⚡    💛 Rotating
              ⚡      Golden
```

**AI Speaking:**
```
👤 (You)  ⚡⚡⚡  🔊 (AI)
  Static      ⚡    💜 Pulsing
              ⚡      Purple
```

## 🎉 Success Criteria

You've successfully implemented VAD when:

1. ✅ You can speak without clicking start/stop
2. ✅ System automatically detects when you finish
3. ✅ Visual feedback is smooth and responsive
4. ✅ Transcription is accurate
5. ✅ AI responds appropriately
6. ✅ Audio plays automatically
7. ✅ Can have continuous conversation
8. ✅ UI animations work correctly

## 🔄 Comparison Test

Try both modes to see the difference:

**Manual Mode (🎙️ Voice Agent):**
1. Click "Start Talking"
2. Speak
3. Click "Stop Recording"
4. Wait for processing

**VAD Mode (🎯 VAD Agent):**
1. Click "Start Listening"
2. Speak
3. Pause naturally
4. System auto-processes

**Winner:** VAD Mode for natural conversation! 🏆

## 📱 Next Steps

After successful testing:

1. **Adjust VAD Sensitivity** (if needed)
   - Edit `VADVoiceAgent.js`
   - Modify `positiveSpeechThreshold` and `negativeSpeechThreshold`

2. **Customize Appearance**
   - Edit `VADVoiceAgent.css`
   - Change colors, animations, layout

3. **Add Features**
   - Save conversations
   - Export transcripts
   - Multiple AI personalities

4. **Deploy**
   - Host backend on cloud server
   - Deploy frontend to Vercel/Netlify
   - Enable HTTPS for production

## 📞 Support

If you encounter issues:

1. **Check Logs:**
   - Backend: Terminal output
   - Frontend: Browser console (F12)

2. **Verify Setup:**
   - Backend URL: `http://localhost:8000`
   - Frontend URL: `http://localhost:3000`
   - API endpoints responding

3. **Test Components:**
   - Test microphone: Record in other apps
   - Test backend: Use curl/Postman
   - Test frontend: Check network tab

## 🎊 Congratulations!

You now have a fully functional Voice Activity Detection system integrated with your voice chat application!

**Enjoy natural, hands-free conversations with AI! 🎤✨**




