# 🎙️ Kaggle Voice Clone Chat - Complete Guide

## 📥 How to Upload and Run on Kaggle

### Step 1: Upload Notebook to Kaggle

1. **Go to Kaggle**: https://www.kaggle.com/
2. **Sign in** or create account (free)
3. **Click** "Code" in top menu
4. **Click** "New Notebook"
5. **Click** the 3 dots (menu) → "Import Notebook"
6. **Upload** the `voice_clone_chat_kaggle.ipynb` file

---

### Step 2: Enable GPU (CRITICAL!)

⚡ **This is REQUIRED for reasonable speed!**

1. Click **"Settings"** in the right sidebar
2. Under **"Accelerator"**, select **"GPU T4"** (free!)
3. Click **"Save"**
4. The notebook will restart with GPU

**Speed Comparison:**
- 🚀 With GPU: 30-60 seconds per response
- 🐌 Without GPU: 5-8 minutes per response

---

### Step 3: Get OpenRouter API Key

1. Go to: https://openrouter.ai/
2. **Sign up** (free account)
3. **Get API key**: https://openrouter.ai/keys
4. **Add credits**: https://openrouter.ai/credits (add $1-2)
5. **Copy your API key** (starts with `sk-or-v1-...`)

**Cost**: ~$0.005-0.01 per conversation (very cheap!)

---

### Step 4: Run the Notebook

1. **Cell 1**: Introduction (just read)
2. **Cell 2**: Click "Run" - Installs dependencies (5-10 minutes)
3. **Cell 3**: Click "Run" - Checks GPU availability
4. **Cell 4**: **PASTE YOUR API KEY**, then "Run"
5. **Cell 5**: Click "Run" - Loads Whisper model (2 minutes)
6. **Cell 6**: Click "Run" - Loads ChatterBox model (2-3 minutes)
7. **Cell 7**: Click "Run" - Defines functions
8. **Cell 8**: Click "Run" - **Launches Gradio interface!**

---

### Step 5: Use the Interface

After running Cell 8, you'll see a **public URL** like:
```
Running on public URL: https://xxxxx.gradio.live
```

1. **Click the link** to open the web interface
2. **Upload reference voice**: Record 3-10 seconds of your voice
3. **Upload question**: Record your question
4. **Click "Generate Response"**
5. **Wait 30-60 seconds** (with GPU)
6. **Listen** to AI response in your cloned voice!

---

## 🎯 Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. User uploads reference voice (YOUR voice sample)    │
│    Example: "Hello, my name is [Your Name]"            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. User asks question in audio                         │
│    Example: "What is the weather like today?"          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Whisper transcribes question to text                │
│    Output: "What is the weather like today?"           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. GPT-3.5 generates intelligent response              │
│    Output: "I don't have real-time weather data..."    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. ChatterBox clones YOUR voice                        │
│    - Analyzes reference voice characteristics           │
│    - Generates response in YOUR voice                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Output: Audio file with AI response in YOUR voice!  │
│    🎧 Listen and download                              │
└─────────────────────────────────────────────────────────┘
```

---

## 💡 Tips for Best Results

### For Reference Voice:
- ✅ **Clear speech**, no background noise
- ✅ **3-10 seconds** minimum
- ✅ Speak naturally in your normal voice
- ✅ Good quality recording (not phone call quality)
- ❌ Avoid: whispers, shouting, music in background

### For Questions:
- ✅ Speak clearly and at normal pace
- ✅ Any length is fine
- ✅ Ask anything! (general knowledge, math, stories, etc.)

---

## 🐛 Troubleshooting

### "GPU not enabled"
- Go to Settings → Accelerator → GPU T4 → Save
- Notebook will restart with GPU

### "API key error"
- Check your API key is correct in Cell 4
- Verify you have credits at https://openrouter.ai/credits
- Make sure key starts with `sk-or-v1-`

### "Model loading failed"
- Check internet connection
- Try running the cell again
- Kaggle sometimes has network issues, just retry

### "Very slow generation"
- Verify GPU is enabled (should see "Using device: cuda")
- First generation is always slower (warming up)
- Subsequent generations are faster

### "Audio quality poor"
- Use better quality reference audio
- Ensure reference is 3-10 seconds minimum
- Reduce background noise

---

## 📊 Performance & Cost

### Time (with GPU T4):
- **Model loading**: 5-7 minutes (one-time)
- **Per conversation**: 30-60 seconds
  - Transcribe: 2-5 sec
  - LLM: 1-3 sec
  - Voice clone: 25-50 sec

### Cost (OpenRouter):
- **Per conversation**: ~$0.005-0.01
- **100 conversations**: ~$0.50-1.00
- **Very affordable!** 💰

---

## 🎓 Models Used

1. **Whisper (base)** - OpenAI
   - Speech-to-Text transcription
   - ~75 MB model
   - Supports multiple languages

2. **GPT-3.5-Turbo** - OpenAI via OpenRouter
   - Intelligent conversation responses
   - API-based (no local model)

3. **ChatterBox** - Resemble AI
   - Voice cloning TTS
   - ~500 MB model
   - State-of-the-art voice cloning

---

## 🚀 Advanced Usage

### Change LLM Model

In Cell 7, find this line:
```python
model="openai/gpt-3.5-turbo",
```

Change to:
```python
model="anthropic/claude-2",  # Claude 2
# or
model="meta-llama/llama-2-70b-chat",  # Llama 2
# or
model="google/palm-2-codechat-bison",  # PaLM 2
```

See all models: https://openrouter.ai/models

### Adjust Voice Characteristics

In Cell 7, find this line:
```python
exaggeration=0.5
```

Change to:
- `0.0` - Flat, monotone
- `0.5` - Normal (default)
- `1.0` - Exaggerated, dramatic

### Use Smaller Whisper Model

In Cell 5, change:
```python
whisper_model = whisper.load_model("tiny", device=device)  # Faster, less accurate
```

---

## 📤 Sharing Your Notebook

After uploading to Kaggle:

1. **Make it public**: Click "Share" button
2. **Get link**: Copy notebook URL
3. **Share**: Anyone can view and run your notebook!

Example: `https://www.kaggle.com/username/voice-clone-chat`

---

## 🎉 You're All Set!

Follow the steps above and you'll have a working voice cloning chat system in ~15 minutes!

**Questions?** Check the troubleshooting section or Kaggle community forums.

**Have fun talking to AI in your own voice!** 🎙️🤖

