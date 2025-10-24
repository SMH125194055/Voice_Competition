# 🚀 BACKEND SETUP GUIDE

**Created:** October 24, 2025  
**Python:** 3.12.3  
**CUDA:** 12.1+

Complete setup for Voice Competition backend with all models:
- **ChatterBox TTS** (Text-to-Speech)
- **Ditto-TalkingHead** (Avatar Generation - Primary)
- **SadTalker** (Avatar Generation - Alternative)
- **Whisper STT** (Speech-to-Text)

---

## ⚡ QUICK SETUP (Automated)

### One-Command Install:

```bash
./quick_setup.sh
```

This script automatically:
1. ✅ Checks Python 3.12.3
2. ✅ Creates virtual environment
3. ✅ Installs PyTorch with CUDA 12.1
4. ✅ Installs all requirements (60+ packages)
5. ✅ Installs Perth
6. ✅ Checks model weights

**Time:** ~15-20 minutes

---

## 📋 MANUAL SETUP (Step-by-Step)

### Prerequisites:
```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3.12 python3.12-venv ffmpeg

# Verify
python3.12 --version  # Should be 3.12.3
ffmpeg -version
```

### Step 1: Create Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### Step 2: Install PyTorch with CUDA

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Verify:
```bash
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
# Should print: CUDA: True
```

### Step 3: Install Requirements

**Choose ONE:**

**Option A - Latest (Recommended)**:
```bash
pip install -r requirements_complete_20251024.txt
```

**Option B - Clean**:
```bash
pip install -r requirements.txt
```

**Option C - Exact Replication**:
```bash
pip install -r ../../environment.txt
```

### Step 4: Install Perth

```bash
pip install git+https://github.com/KwaiVGI/perth.git
```

### Step 5: Check Model Weights

```bash
python download_model_weights.py
```

### Step 6: Configure Environment

```bash
cp .env.example .env
nano .env
```

Set:
```ini
AVATAR_MODEL=ditto
AVATAR_DEVICE=cuda
TTS_MODEL=chatterbox
STT_MODEL=whisper
MODE=local
```

---

## 📦 REQUIREMENTS FILES EXPLAINED

### `requirements_complete_20251024.txt` ⭐⭐⭐ **NEW!**
- **Created**: October 24, 2025
- **Packages**: 60 core packages
- **Includes**: ALL models (ChatterBox, Ditto, SadTalker, Whisper)
- **Best for**: Fresh installs with date stamp
- **Use**: `pip install -r requirements_complete_20251024.txt`

### `requirements.txt` ⭐⭐
- **Packages**: 60 core packages
- **Includes**: Essential packages only
- **Best for**: Clean installations
- **Use**: `pip install -r requirements.txt`

### `../../environment.txt` ⭐
- **Packages**: 230 packages (exact pip freeze)
- **Best for**: Exact replication
- **Use**: `pip install -r ../../environment.txt`

---

## 🎬 MODEL WEIGHTS

### Auto-Download (First Run):
- ChatterBox TTS (~1.6 GB) → `~/.cache/huggingface/`
- Whisper STT (~140 MB) → `~/.cache/whisper/`
- Perth (~200 MB) → `~/.cache/perth/`
- InsightFace (~300 MB) → `~/.insightface/`

### Manual Download Required:

#### Ditto-TalkingHead (REQUIRED) ~2 GB:
```
Avatar/ditto-talkinghead/checkpoints/ditto_pytorch/
├── appearance_feature_extractor.pt
├── motion_extractor.pt
├── audio2motion.pt
├── stitching_retargeting_network.pt
├── warping_network.pt
├── spade_generator.pt
└── wav2vec.pt
```

#### SadTalker (OPTIONAL) ~1.7 GB:
```
Avatar/SadTalker/checkpoints/
├── mapping_00109-model.pth.tar
├── mapping_00229-model.pth.tar
├── SadTalker_V0.0.2_256.safetensors
└── epoch_20.pth
```

**Check with:**
```bash
python download_model_weights.py
```

---

## 🚀 START BACKEND

```bash
# Activate venv
source venv/bin/activate

# Start server
uvicorn main:app --host 0.0.0.0 --port 8000

# Or with auto-reload during development
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Test Backend:

```bash
# In another terminal

# Health check
curl http://localhost:8000/

# Ditto status
curl http://localhost:8000/api/ditto-online-fixed/status

# Should return:
# {"status":"ready","pool_size":3,"available_sdks":3}
```

---

## 🧪 TEST INSTALLATION

```bash
cd ../../
python test_online_fixed.py
```

Expected output:
- ✅ Backend connected
- ✅ Video generated
- ✅ All chunks working

---

## 📊 INSTALLATION CHECKLIST

- [ ] Python 3.12.3 installed
- [ ] FFmpeg installed
- [ ] Virtual environment created
- [ ] PyTorch with CUDA installed
- [ ] All requirements installed (`requirements_complete_20251024.txt`)
- [ ] Perth installed
- [ ] `.env` file configured
- [ ] Ditto weights present (~2 GB)
- [ ] Backend starts without errors
- [ ] `/api/ditto-online-fixed/status` returns "ready"
- [ ] Test script passes

---

## 🔧 TROUBLESHOOTING

### Issue: CUDA not available

```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
python -c "import torch; print(torch.cuda.is_available())"
```

### Issue: FFmpeg not found

```bash
sudo apt install ffmpeg
ffmpeg -version
```

### Issue: ModuleNotFoundError

```bash
source venv/bin/activate
pip install -r requirements_complete_20251024.txt
```

### Issue: Ditto weights missing

```bash
python download_model_weights.py
# Check output for missing files
# Restore from backup or place weights manually
```

### Issue: Port 8000 in use

```bash
sudo lsof -ti:8000 | xargs kill -9
# Or use different port
uvicorn main:app --host 0.0.0.0 --port 8001
```

---

## 📂 DIRECTORY STRUCTURE

```
backend/
├── README_SETUP.md                      ← This file
├── requirements_complete_20251024.txt   ⭐ NEW! Use this
├── requirements.txt                     Alternative
├── quick_setup.sh                       ⭐ Automated setup
├── download_model_weights.py            ⭐ Check weights
├── .env.example                         Config template
├── main.py                             Backend server
├── api/
│   ├── ditto_online_fixed.py           ⭐ Main endpoint
│   └── ...
├── utils/
│   ├── ditto_avatar_generator.py
│   ├── tts.py
│   └── ...
└── Avatar/
    ├── ditto-talkinghead/
    │   └── checkpoints/                ⭐ Place Ditto weights here
    └── SadTalker/
        └── checkpoints/                Optional weights
```

---

## 🎯 QUICK COMMANDS

### Setup:
```bash
./quick_setup.sh                                      # Automated setup
```

### Install:
```bash
pip install -r requirements_complete_20251024.txt     # Install requirements
python download_model_weights.py                      # Check weights
```

### Run:
```bash
source venv/bin/activate                              # Activate venv
uvicorn main:app --host 0.0.0.0 --port 8000          # Start server
```

### Test:
```bash
curl http://localhost:8000/api/ditto-online-fixed/status
cd ../../ && python test_online_fixed.py
```

---

## 📚 MORE DOCUMENTATION

- **Complete Installation**: `../../INSTALLATION_GUIDE.md`
- **Migration Guide**: `../../MIGRATION_GUIDE.md`
- **Model Weights**: `../../MODEL_WEIGHTS_CHECKLIST.md`
- **Quick Start**: `../../QUICK_START.md`
- **Performance**: `../../ACHIEVE_8_SECOND_GOAL.md`

---

## 📊 PACKAGE SUMMARY

| File | Packages | Date | Use Case |
|------|----------|------|----------|
| `requirements_complete_20251024.txt` | 60 | Oct 24, 2025 | **Latest** ⭐ |
| `requirements.txt` | 60 | - | Clean install |
| `../../environment.txt` | 230 | Oct 24, 2025 | Exact replication |

---

## ✅ SETUP COMPLETE!

After successful setup:
- ✅ Backend running on port 8000
- ✅ All models loaded (ChatterBox, Ditto, Whisper)
- ✅ GPU memory used (~6-8 GB)
- ✅ API endpoint ready: `/api/ditto-online-fixed/generate`
- ✅ Ready to achieve <8s first video!

---

**Setup time:** ~15-20 minutes (automated) or ~30 minutes (manual)  
**Total storage:** ~6 GB (Ditto only) or ~8 GB (with SadTalker)  
**Status:** ✨ Ready for production!

*Created: October 24, 2025*  
*Tested and verified: ✅*

