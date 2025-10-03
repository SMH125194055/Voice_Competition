# Troubleshooting Guide

## Common Issues and Solutions

### 1. Whisper Error: "The system cannot find the file specified"

**Problem**: Whisper requires FFmpeg to process audio files, but it's not installed or not in PATH.

**Solution**: Install FFmpeg

#### Windows:
```bash
# Option 1: Using winget (Windows 10+)
winget install ffmpeg

# Option 2: Using Chocolatey
choco install ffmpeg

# Option 3: Manual installation
# 1. Download from https://ffmpeg.org/download.html
# 2. Extract to C:\ffmpeg
# 3. Add C:\ffmpeg\bin to PATH environment variable
```

#### macOS:
```bash
brew install ffmpeg
```

#### Linux:
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch
sudo pacman -S ffmpeg
```

**Verify Installation**:
```bash
ffmpeg -version
```

After installing FFmpeg, restart your terminal and the FastAPI server.

---

### 2. OpenAI Client Error: "unexpected keyword argument 'proxies'"

**Problem**: Version incompatibility with the OpenAI Python SDK.

**Solution**: Update to the latest version:
```bash
pip install --upgrade openai httpx
```

Or reinstall:
```bash
pip uninstall openai
pip install openai>=1.0.0
```

---

### 3. Chat Endpoint Returns 500 Error

**Problem**: Missing or invalid `OPENAI_API_KEY` in `.env` file.

**Solution**:
1. Create `.env` file if it doesn't exist:
   ```bash
   copy env.template .env    # Windows
   cp env.template .env      # Linux/Mac
   ```

2. Add your OpenRouter API key:
   ```env
   OPENAI_API_KEY=sk-or-v1-your-actual-key-here
   OPENAI_API_BASE=https://openrouter.ai/api/v1
   ```

3. Get an API key from: https://openrouter.ai/keys

4. Restart the server after updating `.env`

---

### 4. ChatterBox Model Not Loading

**Problem**: ChatterBox models fail to download or load.

**Solution**:
1. Ensure you have enough disk space (~2GB)
2. Check your internet connection
3. Try using a smaller model or API mode:
   ```env
   MODE=api
   ```

4. If using GPU, ensure CUDA is properly installed:
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```

---

### 5. Out of Memory Errors

**Problem**: Models are too large for available RAM/VRAM.

**Solutions**:

#### For Whisper:
Use a smaller model in `.env`:
```env
WHISPER_MODEL=tiny    # ~390 MB RAM
# or
WHISPER_MODEL=base    # ~1 GB RAM (default)
```

#### For ChatterBox:
Switch to API mode:
```env
MODE=api
```

#### System-wide:
- Close other applications
- Increase virtual memory (Windows)
- Use CPU instead of GPU (slower but uses RAM instead of VRAM)

---

### 6. Audio File Upload Fails

**Problem**: File size too large or unsupported format.

**Solutions**:
1. Check file size (limit: 25MB by default)
2. Supported formats: WAV, MP3, M4A, OGG
3. Convert audio using FFmpeg:
   ```bash
   ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav
   ```

---

### 7. Server Won't Start

**Problem**: Port 8000 already in use.

**Solution**:
```bash
# Use a different port
uvicorn main:app --reload --port 8001

# Or kill the process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -i :8000
kill -9 <PID>
```

---

### 8. Dependencies Installation Fails

**Problem**: PyTorch or other large packages fail to install.

**Solutions**:

1. **Install PyTorch separately first**:
   ```bash
   # CPU only (smaller, faster install)
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
   
   # GPU (CUDA 11.8)
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   
   # GPU (CUDA 12.1)
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

2. **Then install remaining requirements**:
   ```bash
   pip install -r requirements.txt
   ```

---

### 9. Voice Cloning Doesn't Work

**Problem**: Output voice doesn't match reference audio.

**Solutions**:
1. Ensure reference audio is good quality:
   - Clear speech
   - Minimal background noise
   - 3-10 seconds long
   - WAV or MP3 format

2. Update `.env` with correct path:
   ```env
   VOICE_CLONE_AUDIO=audio/your_voice.wav
   ```

3. Verify file exists:
   ```bash
   ls audio/your_voice.wav    # Linux/Mac
   dir audio\your_voice.wav   # Windows
   ```

---

### 10. Slow Response Times

**Problem**: Requests take too long to complete.

**Solutions**:

1. **Use GPU instead of CPU**:
   - Install CUDA and CUDA-enabled PyTorch
   - Check: `python -c "import torch; print(torch.cuda.is_available())"`

2. **Use smaller models**:
   ```env
   WHISPER_MODEL=tiny
   ```

3. **Switch to API mode** (fastest):
   ```env
   MODE=api
   ```

4. **Preload models**: They load at startup, not per request

---

## Getting Help

If issues persist:

1. **Check server logs** for detailed error messages
2. **Enable debug logging** in `main.py`:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Test individual components**:
   - Health check: `curl http://localhost:8000/`
   - Chat only: Test with MODE=api first
   - TTS only: Test `/speak` endpoint
   - STT only: Test `/transcribe` endpoint

4. **Verify environment**:
   ```bash
   python --version    # Should be 3.8+
   pip list            # Check installed packages
   ffmpeg -version     # Check FFmpeg
   ```

5. **Check OpenRouter status**: https://openrouter.ai/status

---

## Still Need Help?

Check the logs, verify your `.env` configuration, and ensure all dependencies are properly installed.

