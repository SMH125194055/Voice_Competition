# 🚀 COMPLETE MIGRATION GUIDE

## Transfer Project to New GPU/Storage

### Overview
This guide helps you migrate the entire Voice Competition project (backend + frontend) with all models (ChatterBox, SadTalker, Ditto) to a new machine.

---

## 📋 PREREQUISITES (New Machine)

### System Requirements:
- **OS**: Ubuntu 20.04+ or similar Linux
- **GPU**: NVIDIA GPU with 8GB+ VRAM
- **Storage**: 15GB+ free space
- **RAM**: 16GB+ recommended
- **CUDA**: 12.1 or higher
- **Python**: 3.12.3

---

## STEP 1: PREPARE BACKUP (Old Machine)

### 1.1 Create Backup Script

Create `backup_project.sh`:

```bash
#!/bin/bash

echo "🗜️  Creating project backup..."

BACKUP_DIR="voice_competition_backup"
mkdir -p $BACKUP_DIR

# 1. Backend code
echo "📦 Backing up backend code..."
tar -czf $BACKUP_DIR/backend_code.tar.gz \
  voice-clone-chat-boilerplate/backend/ \
  --exclude='voice-clone-chat-boilerplate/backend/venv' \
  --exclude='voice-clone-chat-boilerplate/backend/__pycache__' \
  --exclude='voice-clone-chat-boilerplate/backend/**/*.pyc'

# 2. Frontend code
echo "📦 Backing up frontend code..."
tar -czf $BACKUP_DIR/frontend_code.tar.gz \
  voice-clone-chat-boilerplate/frontend/ \
  --exclude='voice-clone-chat-boilerplate/frontend/node_modules' \
  --exclude='voice-clone-chat-boilerplate/frontend/build'

# 3. Model weights - Ditto
echo "🎬 Backing up Ditto models..."
tar -czf $BACKUP_DIR/ditto_models.tar.gz \
  voice-clone-chat-boilerplate/backend/Avatar/ditto-talkinghead/checkpoints/

# 4. Model weights - SadTalker (if you use it)
echo "🎬 Backing up SadTalker models..."
if [ -d "voice-clone-chat-boilerplate/backend/Avatar/SadTalker/checkpoints" ]; then
  tar -czf $BACKUP_DIR/sadtalker_models.tar.gz \
    voice-clone-chat-boilerplate/backend/Avatar/SadTalker/checkpoints/
fi

# 5. Reference files
echo "📸 Backing up reference files..."
tar -czf $BACKUP_DIR/references.tar.gz \
  voice-clone-chat-boilerplate/backend/Avatar/References/ \
  voice-clone-chat-boilerplate/backend/audio/

# 6. HuggingFace cache (ChatterBox TTS)
echo "🔊 Backing up TTS models..."
if [ -d "$HOME/.cache/huggingface" ]; then
  tar -czf $BACKUP_DIR/huggingface_cache.tar.gz ~/.cache/huggingface/
fi

# 7. Whisper models
echo "🎤 Backing up Whisper models..."
if [ -d "$HOME/.cache/whisper" ]; then
  tar -czf $BACKUP_DIR/whisper_cache.tar.gz ~/.cache/whisper/
fi

# 8. Other models (Perth, InsightFace)
echo "👤 Backing up face models..."
if [ -d "$HOME/.cache/perth" ]; then
  tar -czf $BACKUP_DIR/perth_cache.tar.gz ~/.cache/perth/
fi
if [ -d "$HOME/.insightface" ]; then
  tar -czf $BACKUP_DIR/insightface_cache.tar.gz ~/.insightface/
fi

# 9. Configuration and docs
echo "⚙️  Backing up configs and docs..."
tar -czf $BACKUP_DIR/configs_docs.tar.gz \
  COMPLETE_REQUIREMENTS.txt \
  MODEL_WEIGHTS_CHECKLIST.md \
  MIGRATION_GUIDE.md \
  ACHIEVE_8_SECOND_GOAL.md \
  FINAL_SOLUTION_SUMMARY.md \
  QUICK_START.md \
  ONLINE_MODE_FIXED.md \
  test_online_fixed.py

echo "✅ Backup complete!"
echo ""
echo "📊 Backup summary:"
du -sh $BACKUP_DIR/*
echo ""
echo "💾 Total size:"
du -sh $BACKUP_DIR
echo ""
echo "📤 Transfer this folder to your new machine:"
echo "   rsync -avz --progress $BACKUP_DIR/ user@new-machine:/path/to/destination/"
```

### 1.2 Run Backup

```bash
cd /home/syedhuzaifa/Voice_Competition
chmod +x backup_project.sh
./backup_project.sh
```

### 1.3 Transfer Files

```bash
# Option 1: rsync over network
rsync -avz --progress voice_competition_backup/ user@new-machine:/home/user/

# Option 2: Copy to external drive
cp -r voice_competition_backup/ /mnt/external_drive/

# Option 3: Create single archive
tar -czf voice_competition_complete.tar.gz voice_competition_backup/
# Upload to cloud or transfer via USB
```

---

## STEP 2: SETUP NEW MACHINE

### 2.1 Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y build-essential git wget curl

# Install FFmpeg (required for video processing)
sudo apt install -y ffmpeg

# Verify FFmpeg
ffmpeg -version

# Install Python 3.12.3 (if not already installed)
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Install pip for Python 3.12
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12
```

### 2.2 Install CUDA and cuDNN

```bash
# Check if CUDA is already installed
nvidia-smi

# If not installed, download CUDA 12.1+
# Visit: https://developer.nvidia.com/cuda-downloads
# Follow official installation guide for your OS

# Verify CUDA installation
nvcc --version

# Install cuDNN (required)
# Visit: https://developer.nvidia.com/cudnn
# Download and install cuDNN for your CUDA version
```

---

## STEP 3: RESTORE PROJECT

### 3.1 Extract Backup

```bash
# Create project directory
mkdir -p /home/user/Voice_Competition
cd /home/user/Voice_Competition

# Extract all backups
BACKUP_DIR="/path/to/voice_competition_backup"

echo "📦 Extracting backend code..."
tar -xzf $BACKUP_DIR/backend_code.tar.gz

echo "📦 Extracting frontend code..."
tar -xzf $BACKUP_DIR/frontend_code.tar.gz

echo "🎬 Extracting model weights..."
tar -xzf $BACKUP_DIR/ditto_models.tar.gz
tar -xzf $BACKUP_DIR/sadtalker_models.tar.gz 2>/dev/null || true

echo "📸 Extracting reference files..."
tar -xzf $BACKUP_DIR/references.tar.gz

echo "🔊 Extracting TTS models..."
mkdir -p ~/.cache/huggingface
tar -xzf $BACKUP_DIR/huggingface_cache.tar.gz -C ~/

echo "🎤 Extracting Whisper models..."
mkdir -p ~/.cache/whisper
tar -xzf $BACKUP_DIR/whisper_cache.tar.gz -C ~/

echo "👤 Extracting face models..."
mkdir -p ~/.cache/perth
tar -xzf $BACKUP_DIR/perth_cache.tar.gz -C ~/ 2>/dev/null || true
mkdir -p ~/.insightface
tar -xzf $BACKUP_DIR/insightface_cache.tar.gz -C ~/ 2>/dev/null || true

echo "⚙️  Extracting configs..."
tar -xzf $BACKUP_DIR/configs_docs.tar.gz

echo "✅ Extraction complete!"
```

---

## STEP 4: SETUP BACKEND

### 4.1 Create Virtual Environment

```bash
cd /home/user/Voice_Competition/voice-clone-chat-boilerplate/backend

# Create venv with Python 3.12
python3.12 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 4.2 Install PyTorch with CUDA

```bash
# Install PyTorch with CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify PyTorch CUDA
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"
```

### 4.3 Install All Requirements

```bash
# Install from complete requirements file
pip install -r ../../COMPLETE_REQUIREMENTS.txt

# This will take 10-15 minutes
```

### 4.4 Install Perth (Special case)

```bash
pip install git+https://github.com/KwaiVGI/perth.git
```

### 4.5 Configure Environment

```bash
# Copy example env file
cp env.example .env

# Edit .env file
nano .env
```

Update these key settings:
```ini
# Set your mode
MODE=local

# Avatar settings
AVATAR_MODEL=ditto
AVATAR_DEVICE=cuda
AVATAR_SIZE=256
AVATAR_MODE=fast

# TTS settings
TTS_MODEL=chatterbox
TTS_DEVICE=cuda:1

# STT settings
STT_MODEL=whisper
STT_DEVICE=cuda:1

# LLM API (if using)
QLU_API_KEY=your_key_here
```

---

## STEP 5: SETUP FRONTEND

### 5.1 Install Node.js (if not installed)

```bash
# Install Node.js 18+ and npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

### 5.2 Install Frontend Dependencies

```bash
cd /home/user/Voice_Competition/voice-clone-chat-boilerplate/frontend/voice-ui

# Install dependencies
npm install

# This will take 5-10 minutes
```

### 5.3 Configure Frontend

```bash
# Create .env file (if needed)
nano .env
```

Add:
```ini
REACT_APP_API_URL=http://localhost:8000
```

---

## STEP 6: TEST THE SETUP

### 6.1 Test Backend

```bash
cd /home/user/Voice_Competition/voice-clone-chat-boilerplate/backend
source venv/bin/activate

# Start backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Wait for startup messages, then in another terminal:

```bash
# Test health endpoint
curl http://localhost:8000/

# Test avatar endpoint status
curl http://localhost:8000/api/ditto-online-fixed/status

# Should return:
# {"status":"ready","pool_size":3,"available_sdks":3}
```

### 6.2 Test Complete Pipeline

```bash
cd /home/user/Voice_Competition
python test_online_fixed.py
```

Expected: Videos generated successfully!

### 6.3 Test Frontend

```bash
cd /home/user/Voice_Competition/voice-clone-chat-boilerplate/frontend/voice-ui

# Start frontend
npm start
```

Open browser: `http://localhost:3000`

---

## STEP 7: VERIFY MODEL LOADING

### 7.1 Check Model Files

```bash
# Ditto models
ls -lh voice-clone-chat-boilerplate/backend/Avatar/ditto-talkinghead/checkpoints/ditto_pytorch/

# Should show:
# - appearance_feature_extractor.pt
# - motion_extractor.pt
# - audio2motion.pt
# - etc. (see MODEL_WEIGHTS_CHECKLIST.md)

# HuggingFace cache
ls -lh ~/.cache/huggingface/hub/

# Whisper models
ls -lh ~/.cache/whisper/
```

### 7.2 Test GPU Usage

```bash
# While backend is running, check GPU usage
nvidia-smi

# You should see Python processes using GPU memory (6-8 GB)
```

---

## STEP 8: PRODUCTION SETUP (Optional)

### 8.1 Setup as System Service

Create `/etc/systemd/system/voice-backend.service`:

```ini
[Unit]
Description=Voice Competition Backend
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/user/Voice_Competition/voice-clone-chat-boilerplate/backend
Environment="PATH=/home/user/Voice_Competition/voice-clone-chat-boilerplate/backend/venv/bin"
ExecStart=/home/user/Voice_Competition/voice-clone-chat-boilerplate/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable voice-backend
sudo systemctl start voice-backend
sudo systemctl status voice-backend
```

---

## 🔧 TROUBLESHOOTING

### Issue: CUDA not found

```bash
# Check CUDA installation
nvcc --version
nvidia-smi

# Reinstall PyTorch with correct CUDA version
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Issue: FFmpeg not found

```bash
sudo apt install ffmpeg
ffmpeg -version
```

### Issue: Model files missing

```bash
# Re-extract from backup
cd /home/user/Voice_Competition
tar -xzf voice_competition_backup/ditto_models.tar.gz
```

### Issue: Port already in use

```bash
# Kill existing process
sudo lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn main:app --host 0.0.0.0 --port 8001
```

### Issue: Permission denied

```bash
# Fix permissions
chmod +x voice-clone-chat-boilerplate/backend/venv/bin/activate
chmod -R 755 voice-clone-chat-boilerplate/
```

---

## 📊 VERIFICATION CHECKLIST

After migration, verify:

- [ ] CUDA available (`nvidia-smi` works)
- [ ] Python 3.12.3 installed
- [ ] Virtual environment activated
- [ ] All requirements installed (`pip list`)
- [ ] FFmpeg installed (`ffmpeg -version`)
- [ ] Backend starts without errors
- [ ] Ditto models loaded (check startup logs)
- [ ] `/api/ditto-online-fixed/status` returns "ready"
- [ ] Test script runs successfully
- [ ] Frontend builds and starts
- [ ] Can access UI at `http://localhost:3000`
- [ ] GPU memory used during inference (~6-8 GB)

---

## 🎉 MIGRATION COMPLETE!

Your project should now be fully operational on the new machine!

### Quick Start Commands:

**Backend**:
```bash
cd /home/user/Voice_Competition/voice-clone-chat-boilerplate/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd /home/user/Voice_Competition/voice-clone-chat-boilerplate/frontend/voice-ui
npm start
```

**Test**:
```bash
cd /home/user/Voice_Competition
python test_online_fixed.py
```

---

## 📚 Additional Resources

- **Model Weights**: See `MODEL_WEIGHTS_CHECKLIST.md`
- **Requirements**: See `COMPLETE_REQUIREMENTS.txt`
- **Performance**: See `ACHIEVE_8_SECOND_GOAL.md`
- **API Docs**: See `FINAL_SOLUTION_SUMMARY.md`

---

## 💾 BACKUP SCHEDULE (Recommended)

After successful migration, setup automatic backups:

```bash
# Add to crontab
crontab -e

# Backup models weekly (Sunday 2 AM)
0 2 * * 0 tar -czf ~/backups/models_$(date +\%Y\%m\%d).tar.gz ~/.cache/huggingface ~/.cache/whisper ~/.insightface

# Backup code daily (2 AM)
0 2 * * * tar -czf ~/backups/code_$(date +\%Y\%m\%d).tar.gz ~/Voice_Competition/voice-clone-chat-boilerplate
```

**Migration time estimate**: 30-60 minutes (depending on internet speed for downloads)

**Total storage needed**: ~15 GB

Good luck with your migration! 🚀

