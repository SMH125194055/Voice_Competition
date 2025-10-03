# 🎙️ Voice Clone Chat - Complete Setup Guide

## 🎯 What This Application Does

**Talk to AI and hear it respond in YOUR cloned voice!**

### Complete Pipeline:
1. ✅ **Record your voice** (3-10 seconds) as reference
2. ✅ **Ask a question** in audio
3. ✅ **AI transcribes** your question (Whisper)
4. ✅ **AI generates** intelligent response (GPT-3.5)
5. ✅ **AI speaks back** in YOUR cloned voice (ChatterBox)
6. ✅ **Save everything** - all conversations with all audio files

---

## 📁 Project Structure

```
Voice_Competition/voice-clone-chat-boilerplate/
├── backend/                    # FastAPI backend
│   ├── main.py                # Main API server
│   ├── utils/                 # Modular utilities
│   │   ├── stt.py            # Whisper STT
│   │   ├── llm.py            # GPT-3.5 Chat
│   │   └── tts.py            # ChatterBox TTS
│   ├── audio/                # Reference audio files
│   ├── requirements.txt      # Python dependencies
│   └── .env                  # Configuration (create this!)
│
└── frontend/                  # React frontend
    └── voice-ui/
        ├── src/
        │   ├── App.js        # Main app
        │   └── components/   # React components
        ├── package.json      # Node dependencies
        └── FRONTEND_GUIDE.md # Frontend docs
```

---

## 🚀 Complete Setup (15 Minutes)

### Prerequisites:
- ✅ Python 3.8+ installed
- ✅ Node.js 14+ installed
- ✅ OpenAI API key (get from https://platform.openai.com/api-keys)

---

## 📋 Step-by-Step Setup

### **PART 1: Backend Setup**

#### 1. Navigate to Backend
```bash
cd voice-clone-chat-boilerplate/backend
```

#### 2. Activate Virtual Environment
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

#### 3. Install Missing Dependencies (if needed)
```bash
pip install -r requirements.txt
```

#### 4. Create `.env` File
Create a file named `.env` in the `backend/` directory:

```env
MODE=local
OPENAI_API_KEY=sk-YOUR-OPENAI-KEY-HERE
OPENAI_API_BASE=https://api.openai.com/v1
VOICE_CLONE_AUDIO=audio/Nafay_Org.mp3
WHISPER_MODEL=base
```

**⚠️ IMPORTANT:** Replace `sk-YOUR-OPENAI-KEY-HERE` with your actual OpenAI API key!

#### 5. Start Backend Server
```bash
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

✅ **Backend is ready!** Keep this terminal open.

---

### **PART 2: Frontend Setup**

#### 1. Open New Terminal & Navigate to Frontend
```bash
cd voice-clone-chat-boilerplate/frontend/voice-ui
```

#### 2. Install Dependencies
```bash
npm install
```

#### 3. Start Frontend
```bash
npm start
```

Frontend will open at: **http://localhost:3000**

✅ **Frontend is ready!**

---

## 🎯 How to Use

### Step 1: Set Reference Voice (One Time)

**Option A: Record**
1. Click **"Record"** tab
2. Click **"Record Reference Voice"** button
3. Speak clearly for 3-10 seconds
4. Click **"Stop Recording"**
5. ✅ Reference voice is set!

**Option B: Upload**
1. Click **"Upload"** tab
2. Click **"Choose Audio File"**
3. Select your audio file (WAV, MP3, etc.)
4. ✅ Reference voice is set!

### Step 2: Ask a Question

1. Click **"Record Question"** button
2. Speak your question clearly
3. Click **"Stop Recording"**
4. Wait for processing:
   - 🎤 Transcribing... (2-5 sec)
   - 🤖 Getting AI response... (1-3 sec)
   - 🔊 Generating voice... (5-8 min on CPU, 30-60 sec on GPU)
5. ✅ See result in conversation history!

### Step 3: View History

1. Scroll down to **"Conversation History"**
2. Click on any conversation to expand
3. See all audio files:
   - 🎤 Your reference voice
   - ❓ Your question audio + text
   - 🤖 AI answer audio + text (in your voice!)
4. Download any audio file
5. Delete conversations you don't need

---

## ⚡ Performance Expectations

### On CPU (Current Setup):
- First load: ~1-2 minutes (loading models)
- Per conversation: **5-8 minutes**
  - Transcribe: 2-5 sec ⚡
  - LLM: 1-3 sec ⚡
  - TTS: 5-8 min 🐌 **(bottleneck!)**

### On GPU (Recommended):
- First load: ~1-2 minutes (loading models)
- Per conversation: **30-60 seconds**
  - Transcribe: 2-5 sec ⚡
  - LLM: 1-3 sec ⚡
  - TTS: 25-50 sec ⚡ **(10x faster!)**

---

## 🔧 Enable GPU (Recommended for Speed)

### Check if you have GPU:
```bash
python -c "import torch; print('GPU:', torch.cuda.is_available())"
```

### If False, Install GPU PyTorch:
```bash
# For CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**Restart backend server** - it will automatically use GPU!

---

## 💰 Cost Breakdown

### What's Free:
- ✅ Whisper STT (runs locally)
- ✅ ChatterBox TTS (runs locally)

### What Costs Money:
- 💰 GPT-3.5 API: ~$0.001-0.002 per conversation

### Total Cost:
- **Per conversation: ~$0.002** (0.2 cents)
- **100 conversations: ~$0.20**
- **Very affordable!** 💰

---

## 🎨 Features Breakdown

### ✅ Backend Features:
- Whisper STT (speech-to-text)
- GPT-3.5 LLM (intelligent responses)
- ChatterBox TTS (voice cloning)
- FastAPI REST API
- Local & API modes
- Modular architecture

### ✅ Frontend Features:
- Record/upload reference voice
- Change reference voice anytime
- Record questions with microphone
- Real-time progress indicators
- Conversation history (saved locally)
- Display all 3 audio files per conversation
- Download any audio file
- Delete conversations
- Beautiful, responsive UI
- Mobile-friendly

---

## 📊 Complete Data Flow

```
┌─────────────────────────────────────────────────────────┐
│ FRONTEND: User Interface                                │
│ - Record reference voice                                │
│ - Record question                                       │
│ - Display conversation history                          │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP Requests
                     ▼
┌─────────────────────────────────────────────────────────┐
│ BACKEND: FastAPI Server (http://localhost:8000)        │
│                                                          │
│  POST /transcribe → Whisper STT                         │
│  POST /chat → GPT-3.5 LLM                              │
│  POST /speak → ChatterBox TTS                          │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ STORAGE: Browser localStorage                           │
│ - All conversations                                     │
│ - All audio files (as blobs)                           │
│ - Persists across page refreshes                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

### Backend Issues:

**"Port 8000 already in use"**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

**"Module not found" errors**
```bash
pip install -r requirements.txt
```

**"FFmpeg not found"** (for Whisper)
```bash
# Windows
winget install ffmpeg

# Mac
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### Frontend Issues:

**"Cannot connect to backend"**
- Make sure backend is running at http://localhost:8000
- Check browser console for CORS errors
- Verify .env file has correct settings

**"Microphone not working"**
- Check browser permissions (allow microphone)
- Try different browser (Chrome recommended)
- Check system microphone settings

**"Audio not playing"**
- Check audio format (should be WAV)
- Try different browser
- Check system volume

---

## 📱 Browser Support

✅ **Recommended:**
- Chrome 90+
- Edge 90+
- Firefox 88+
- Safari 14+

❌ **Not Supported:**
- Internet Explorer (any version)
- Very old browsers

---

## 🎓 Technical Stack

### Backend:
- **Framework:** FastAPI
- **STT:** OpenAI Whisper (base model)
- **LLM:** GPT-3.5-Turbo (OpenAI API)
- **TTS:** ChatterBox (Resemble AI)
- **Language:** Python 3.8+

### Frontend:
- **Framework:** React 19
- **HTTP Client:** Axios
- **Audio:** Web Audio API, MediaRecorder
- **Storage:** Browser localStorage
- **Styling:** Custom CSS

---

## 🚀 Production Deployment

### Backend:
```bash
# Build
pip install -r requirements.txt

# Deploy to:
- Railway
- Render
- AWS EC2
- Google Cloud Run
- Heroku
```

### Frontend:
```bash
# Build
npm run build

# Deploy build/ folder to:
- Netlify
- Vercel
- GitHub Pages
- AWS S3 + CloudFront
```

---

## 📝 Environment Variables

### Backend `.env`:
```env
MODE=local                           # local or api
OPENAI_API_KEY=sk-...               # Your OpenAI API key
OPENAI_API_BASE=https://api.openai.com/v1
VOICE_CLONE_AUDIO=audio/Nafay_Org.mp3
WHISPER_MODEL=base                  # tiny, base, small, medium, large
```

---

## ✅ Checklist

Before using the app, make sure:

- [x] Python 3.8+ installed
- [x] Node.js 14+ installed
- [x] Virtual environment activated
- [x] Backend dependencies installed
- [x] Frontend dependencies installed
- [x] `.env` file created with OpenAI API key
- [x] Backend server running (port 8000)
- [x] Frontend server running (port 3000)
- [x] Microphone permissions granted in browser

---

## 🎉 You're All Set!

1. ✅ Backend running at http://localhost:8000
2. ✅ Frontend running at http://localhost:3000
3. ✅ Record your reference voice
4. ✅ Ask questions
5. ✅ Hear AI respond in your cloned voice!

**Enjoy your voice clone chat app!** 🎙️🤖

---

## 📞 Need Help?

- **Backend Issues:** Check `backend/TROUBLESHOOTING.md`
- **Frontend Issues:** Check `frontend/voice-ui/FRONTEND_GUIDE.md`
- **Kaggle Version:** Check `backend/KAGGLE_GUIDE.md`

**Happy voice cloning!** 🎉

