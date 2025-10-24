# 🚀 COMPLETE INSTALLATION GUIDE

## Quick Setup for New Machine

---

## 📋 Prerequisites

### System Requirements:
- **OS**: Ubuntu 20.04+ (or compatible Linux)
- **GPU**: NVIDIA GPU with 8GB+ VRAM
- **Storage**: 15GB+ free space
- **RAM**: 16GB+ recommended
- **Python**: 3.12.3
- **CUDA**: 12.1+
- **Node.js**: 18+

---

## STEP 1: Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install build essentials
sudo apt install -y build-essential git wget curl

# Install FFmpeg (REQUIRED for video processing)
sudo apt install -y ffmpeg

# Verify FFmpeg
ffmpeg -version
```

---

## STEP 2: Install Python 3.12.3

```bash
# Add deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.12
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Install pip for Python 3.12
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Verify installation
python3.12 --version  # Should show: Python 3.12.3
```

---

## STEP 3: Install CUDA 12.1+

```bash
# Check current CUDA version
nvidia-smi

# If CUDA not installed or version < 12.1:
# Visit: https://developer.nvidia.com/cuda-downloads
# Download and install CUDA 12.1 or higher

# Verify CUDA
nvcc --version
```

---

## STEP 4: Setup Backend

### 4.1 Navigate to Backend Directory

```bash
cd /path/to/Voice_Competition/voice-clone-chat-boilerplate/backend
```

### 4.2 Create Virtual Environment

```bash
# Create venv with Python 3.12
python3.12 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 4.3 Install PyTorch with CUDA

```bash
# IMPORTANT: Install PyTorch FIRST with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify PyTorch CUDA
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"

# Should output:
# CUDA available: True
# CUDA version: 12.1
```

### 4.4 Install All Backend Requirements

```bash
# Install from requirements.txt
pip install -r requirements.txt

# This will take 10-15 minutes
# It installs:
# - FastAPI, Uvicorn (web server)
# - Whisper (STT)
# - ChatterBox TTS
# - OpenCV (image processing)
# - Mediapipe, InsightFace (face detection)
# - And 40+ other dependencies
```

### 4.5 Install Perth (Special Install)

```bash
# Perth requires git installation
pip install git+https://github.com/KwaiVGI/perth.git
```

### 4.6 Configure Environment Variables

```bash
# Copy example env file
cp env.example .env

# Edit .env file
nano .env
```

**Important settings in `.env`:**

```ini
# ============================================================================
# MODE
# ============================================================================
MODE=local

# ============================================================================
# AVATAR SETTINGS (Use Ditto for best performance)
# ============================================================================
AVATAR_ENABLED=true
AVATAR_MODEL=ditto          # Options: ditto, sadtalker
AVATAR_DEVICE=cuda          # GPU device
AVATAR_SIZE=256             # Output size: 256 or 512
AVATAR_MODE=fast            # Mode: fast or quality
AVATAR_ENHANCER=None        # Face enhancer (for SadTalker)

# ============================================================================
# TTS SETTINGS
# ============================================================================
TTS_MODEL=chatterbox
TTS_DEVICE=cuda:1
TTS_MODE=local

# ============================================================================
# STT SETTINGS
# ============================================================================
STT_MODEL=whisper
STT_DEVICE=cuda:1
TRANSCRIPTION_MODE=parallel

# ============================================================================
# LLM API (Optional - if using cloud LLM)
# ============================================================================
QLU_API_KEY=your_api_key_here
```

---

## STEP 5: Download Model Weights

### 5.1 Ditto-TalkingHead (REQUIRED)

Model weights should be in:
```
backend/Avatar/ditto-talkinghead/checkpoints/ditto_pytorch/
```

**If missing**, download from your backup or original source.

Expected files (~1.9 GB):
- `appearance_feature_extractor.pt`
- `motion_extractor.pt`
- `audio2motion.pt`
- `stitching_retargeting_network.pt`
- `warping_network.pt`
- `spade_generator.pt`
- `wav2vec.pt`

### 5.2 Config Files (REQUIRED)

Location:
```
backend/Avatar/ditto-talkinghead/checkpoints/ditto_cfg/
```

Files:
- `v0.4_hubert_cfg_pytorch.pkl`

### 5.3 Auto-Downloaded Models

These will download automatically on first run:
- **ChatterBox TTS** (~1.6 GB) → `~/.cache/huggingface/`
- **Whisper** (~140 MB) → `~/.cache/whisper/`
- **Perth** (~200 MB) → `~/.cache/perth/`
- **InsightFace** (~300 MB) → `~/.insightface/`

---

## STEP 6: Setup Frontend

### 6.1 Install Node.js

```bash
# Install Node.js 18+ and npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify
node --version  # Should be v18.x.x or higher
npm --version   # Should be 9.x.x or higher
```

### 6.2 Install Frontend Dependencies

```bash
cd /path/to/Voice_Competition/voice-clone-chat-boilerplate/frontend/voice-ui

# Install all dependencies
npm install

# This will take 5-10 minutes
```

### 6.3 Configure Frontend (Optional)

```bash
# Create .env file if needed
nano .env
```

Add:
```ini
REACT_APP_API_URL=http://localhost:8000
```

---

## STEP 7: Test Installation

### 7.1 Test Backend

```bash
# Activate venv
cd /path/to/Voice_Competition/voice-clone-chat-boilerplate/backend
source venv/bin/activate

# Start backend (first run will download models)
uvicorn main:app --host 0.0.0.0 --port 8000

# Wait for startup messages:
# - "Application startup complete"
# - "Uvicorn running on http://0.0.0.0:8000"
```

**In another terminal:**

```bash
# Test health endpoint
curl http://localhost:8000/

# Test Ditto status
curl http://localhost:8000/api/ditto-online-fixed/status

# Should return:
# {"status":"ready","pool_size":3,"available_sdks":3}
```

### 7.2 Test Frontend

```bash
cd /path/to/Voice_Competition/voice-clone-chat-boilerplate/frontend/voice-ui

# Start frontend
npm start

# Opens browser at: http://localhost:3000
```

### 7.3 Test Complete Pipeline

```bash
cd /path/to/Voice_Competition
python test_online_fixed.py

# Should generate test videos successfully
```

---

## STEP 8: Verify GPU Usage

```bash
# While backend is running, check GPU usage
nvidia-smi

# You should see:
# - Python process using 6-8 GB GPU memory
# - GPU utilization during inference
```

---

## 📦 Requirements Files Summary

### Backend Requirements:
- **Main**: `backend/requirements.txt` (all Python packages)
- **Complete**: `/COMPLETE_REQUIREMENTS.txt` (with detailed comments)

### Frontend Requirements:
- **Main**: `frontend/voice-ui/package.json` (all npm packages)

### Model Weights:
- **Checklist**: `/MODEL_WEIGHTS_CHECKLIST.md` (all model files)

---

## 🔧 Troubleshooting

### Issue: "CUDA not available"

```bash
# Reinstall PyTorch with CUDA
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Issue: "FFmpeg not found"

```bash
sudo apt install ffmpeg
ffmpeg -version
```

### Issue: "ModuleNotFoundError"

```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt
```

### Issue: "Port 8000 already in use"

```bash
# Kill existing process
sudo lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn main:app --host 0.0.0.0 --port 8001
```

### Issue: Model files missing

Check locations:
```bash
# Ditto models
ls -lh backend/Avatar/ditto-talkinghead/checkpoints/ditto_pytorch/

# Auto-downloaded models
ls -lh ~/.cache/huggingface/
ls -lh ~/.cache/whisper/
ls -lh ~/.cache/perth/
ls -lh ~/.insightface/
```

---

## ✅ Installation Complete Checklist

- [ ] Python 3.12.3 installed
- [ ] CUDA 12.1+ installed and working
- [ ] FFmpeg installed
- [ ] Node.js 18+ installed
- [ ] Backend venv created and activated
- [ ] PyTorch with CUDA installed and verified
- [ ] All backend requirements installed
- [ ] Perth installed
- [ ] .env file configured
- [ ] Ditto model weights present
- [ ] Frontend dependencies installed
- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] `/api/ditto-online-fixed/status` returns "ready"
- [ ] GPU memory used during inference
- [ ] Test script runs successfully

---

## 🚀 Quick Start Commands

### Start Backend:
```bash
cd voice-clone-chat-boilerplate/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Start Frontend:
```bash
cd voice-clone-chat-boilerplate/frontend/voice-ui
npm start
```

### Run Tests:
```bash
cd Voice_Competition
python test_online_fixed.py
```

---

## 📚 Additional Resources

- **Model Weights**: See `MODEL_WEIGHTS_CHECKLIST.md`
- **Migration**: See `MIGRATION_GUIDE.md`
- **Performance**: See `ACHIEVE_8_SECOND_GOAL.md`
- **Complete Requirements**: See `COMPLETE_REQUIREMENTS.txt`

---

## 💾 Storage Requirements

| Component | Size | Required |
|-----------|------|----------|
| Backend Code | ~100 MB | ✅ Yes |
| Frontend Code | ~500 MB | ✅ Yes |
| Ditto Models | ~2 GB | ✅ Yes |
| ChatterBox TTS | ~1.6 GB | ✅ Yes |
| Whisper STT | ~140 MB | ✅ Yes |
| Perth | ~200 MB | ✅ Yes |
| InsightFace | ~300 MB | ✅ Yes |
| SadTalker | ~1.7 GB | ❌ Optional |
| **TOTAL** | **~6 GB** | - |

---

## ⏱️ Installation Time Estimate

- System dependencies: 10 minutes
- Python & CUDA: 15 minutes
- Backend setup: 20 minutes
- Model downloads (first run): 30 minutes
- Frontend setup: 10 minutes
- Testing: 5 minutes

**Total: ~90 minutes** (depending on internet speed)

---

**Installation complete! You're ready to achieve <8s first video with NO GAPS!** 🎉

