# 🎨 Voice Clone Chat - Frontend Guide

## ✅ Complete React Frontend with All Features

### Features Implemented:

✅ **Reference Voice Management**
- Record or upload reference voice (3-10 seconds)
- Preview reference audio
- Change reference voice anytime

✅ **Voice Question Recording**
- Record questions with microphone
- Real-time recording timer
- Preview before sending

✅ **Complete Pipeline Integration**
- User speaks → Transcribe (Whisper)
- Transcribed text → LLM (GPT-3.5)
- LLM response → Voice Clone (ChatterBox)
- Display result with all audio files

✅ **Conversation History**
- Save all conversations locally (localStorage)
- Display reference voice, question audio, answer audio
- Show transcribed text and AI response text
- Download any audio file
- Delete individual conversations
- Clear all history

✅ **Beautiful UI**
- Modern gradient design
- Responsive layout (mobile-friendly)
- Loading states and error handling
- Step-by-step progress indicators

---

## 🚀 Quick Setup

### Step 1: Navigate to Frontend

```bash
cd voice-clone-chat-boilerplate/frontend/voice-ui
```

### Step 2: Install Dependencies

```bash
npm install
```

### Step 3: Start Backend First!

**IMPORTANT:** Backend must be running at `http://localhost:8000`

```bash
# In another terminal, go to backend directory
cd ../../backend
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Start backend
uvicorn main:app --reload --port 8000
```

### Step 4: Start Frontend

```bash
npm start
```

Frontend will open at: http://localhost:3000

---

## 🎯 How to Use

### 1. Set Reference Voice
- **Option A:** Click "Record" and record 3-10 seconds of your voice
- **Option B:** Click "Upload" and choose an audio file
- Click "Stop Recording" when done
- Your reference voice is now set! ✅

### 2. Ask a Question
- Click "Record Question" button
- Speak your question clearly
- Click "Stop Recording"
- Processing begins automatically:
  - 🎤 Transcribing...
  - 🤖 Getting AI response...
  - 🔊 Generating cloned voice... (5-8 min on CPU, 30-60 sec on GPU)

### 3. View Results
- Conversation appears in history
- Click to expand and see:
  - Reference voice audio
  - Question audio + transcribed text
  - Answer audio + AI response text
- Download any audio file
- Delete conversations you don't need

---

## 📊 Pipeline Flow (As You Described)

```
┌─────────────────────────────────────────────────────────┐
│ 1. User Records Reference Voice (once)                 │
│    → Saved in state + shown in UI                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2a. User Speaks Question                                │
│     → Recorded audio sent to /transcribe endpoint       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2b. Transcribe → Text                                   │
│     Backend: Whisper STT                                │
│     Output: "What is your name?"                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2c. Text → LLM                                          │
│     Backend: GPT-3.5 via /chat endpoint                 │
│     Output: "I'm an AI assistant..."                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2d. LLM Text → Cloned Voice                            │
│     Backend: ChatterBox TTS with reference voice        │
│     Output: Audio file in YOUR voice                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Save & Display Everything                            │
│    ✅ Reference voice audio (shown for each conv)       │
│    ✅ Question audio + text                             │
│    ✅ Answer audio + text                               │
│    ✅ Saved to localStorage (persists on refresh)       │
└─────────────────────────────────────────────────────────┘
```

---

## 🎨 UI Components Breakdown

### **App.js** (Main Container)
- Manages global state
- Handles API calls to backend
- Coordinates all components
- Saves/loads from localStorage

### **ReferenceVoiceManager.js**
- Record or upload reference voice
- Switch between modes
- Preview current reference
- Change reference voice

### **AudioRecorder.js**
- Reusable recording component
- Shows recording timer
- Preview recorded audio
- Used for both reference and questions

### **ConversationHistory.js**
- Displays all past conversations
- Expandable cards
- Shows all 3 audio files per conversation
- Download buttons for each audio
- Delete individual conversations

---

## 💾 Data Storage

### LocalStorage Structure:

```javascript
{
  "voiceConversations": [
    {
      "id": 1696234567890,
      "timestamp": "2024-10-03T10:30:00.000Z",
      "referenceAudioUrl": "blob:http://localhost:3000/...",
      "questionAudioUrl": "blob:http://localhost:3000/...",
      "questionText": "What is your name?",
      "answerText": "I'm an AI assistant...",
      "answerAudioUrl": "blob:http://localhost:3000/...",
      "answerAudioBlob": Blob
    }
  ]
}
```

**Persists across:**
- Page refreshes ✅
- Browser restarts ✅
- But cleared if you clear browser data

---

## 🔧 Backend Integration

### API Endpoints Used:

1. **POST /transcribe**
   - Sends: Question audio file
   - Returns: `{ "text": "..." }`

2. **POST /chat**
   - Sends: `{ "message": "..." }`
   - Returns: `{ "reply": "..." }`

3. **POST /speak**
   - Sends: `{ "text": "..." }`
   - Returns: Audio file (blob)

### CORS Configuration:

Your backend already has CORS enabled:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    ...
)
```

---

## ⚡ Performance Notes

### First Generation:
- Takes 5-8 minutes on CPU (ChatterBox TTS)
- Shows progress: "Generating voice (this may take 5-8 minutes)..."
- Loading spinner visible

### Subsequent Generations:
- Similar time (each generation is independent)
- Models stay loaded in backend

### With GPU:
- Only 30-60 seconds per generation!
- Much better user experience

---

## 🐛 Troubleshooting

### "Failed to process voice chat"
- Check backend is running at http://localhost:8000
- Check browser console for errors
- Verify .env file has API key

### "Could not access microphone"
- Browser needs microphone permissions
- Check browser address bar for mic icon
- Allow microphone access

### "Audio not playing"
- Check audio format (should be WAV)
- Try different browser (Chrome recommended)
- Check browser console for errors

### "Conversations not saving"
- Check browser's localStorage is enabled
- Check console for errors
- Try incognito mode (localStorage might be disabled)

---

## 🎓 Code Structure

```
frontend/voice-ui/src/
├── App.js                              # Main app logic
├── App.css                             # Main styles
├── components/
│   ├── AudioRecorder.js                # Recording component
│   ├── AudioRecorder.css
│   ├── ReferenceVoiceManager.js        # Reference voice UI
│   ├── ReferenceVoiceManager.css
│   ├── ConversationHistory.js          # History display
│   └── ConversationHistory.css
└── index.js                            # React entry point
```

---

## 🚀 Development

### Run in Development Mode:
```bash
npm start
```

### Build for Production:
```bash
npm run build
```

Output in: `build/` directory

### Deploy:
```bash
# Deploy build folder to any static host:
# - Netlify
# - Vercel
# - GitHub Pages
# - AWS S3
```

---

## 📱 Mobile Support

✅ **Fully Responsive!**
- Works on phones and tablets
- Optimized touch interactions
- Responsive audio players
- Mobile-friendly buttons

---

## 🎨 Customization

### Change Colors:

In `App.css`:
```css
/* Main gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Change to your colors */
background: linear-gradient(135deg, #FF6B6B 0%, #4ECDC4 100%);
```

### Change API URL:

In `App.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000';
// Change to your deployed backend URL
```

---

## ✅ All Requirements Met!

✅ User records reference voice (can change it)
✅ User speaks question → converted to text
✅ Text passed to LLM → generates answer text  
✅ Answer text passed to ChatterBox with reference voice
✅ All audio files saved (reference, question, answer)
✅ Previous conversations displayed in history
✅ Each conversation shows all 3 audio files
✅ Saved locally (localStorage)
✅ Download any audio file
✅ Beautiful, modern UI

**Ready to use!** 🎉

---

## 🎯 Next Steps

1. Start backend: `uvicorn main:app --reload --port 8000`
2. Start frontend: `npm start`
3. Record your reference voice
4. Ask a question
5. Wait for AI response in your cloned voice!

**Have fun cloning your voice!** 🎙️🤖

