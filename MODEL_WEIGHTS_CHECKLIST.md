# 📦 MODEL WEIGHTS & CHECKPOINTS CHECKLIST

## Complete list of all models, weights, and files needed for migration

---

## 1️⃣ DITTO-TALKINGHEAD (Avatar Model)

### Location:
`voice-clone-chat-boilerplate/backend/Avatar/ditto-talkinghead/checkpoints/`

### PyTorch Models (Primary - REQUIRED):
```
checkpoints/ditto_pytorch/
├── appearance_feature_extractor.pt     (~500 MB)
├── motion_extractor.pt                 (~200 MB)
├── audio2motion.pt                     (~150 MB)
├── stitching_retargeting_network.pt    (~100 MB)
├── warping_network.pt                  (~300 MB)
├── spade_generator.pt                  (~250 MB)
└── wav2vec.pt                          (~380 MB)
```

**Total Size**: ~1.9 GB

### TensorRT Models (Optional - for faster inference):
```
checkpoints/ditto_trt_Ampere_Plus/
└── [Same structure as PyTorch, but .trt files]
```

**Total Size**: ~2.5 GB

### Config Files (REQUIRED):
```
checkpoints/ditto_cfg/
├── v0.4_hubert_cfg_pytorch.pkl         (~10 KB)
└── v0.4_hubert_cfg_trt.pkl            (~10 KB)
```

### Additional Models:
```
checkpoints/
├── wav2vec2-base-960h/                 (~360 MB)
│   ├── config.json
│   ├── preprocessor_config.json
│   └── pytorch_model.bin
└── mediapipe/
    └── face_landmarker_v2_with_blendshapes.task  (~28 MB)
```

---

## 2️⃣ SADTALKER (Alternative Avatar Model)

### Location:
`voice-clone-chat-boilerplate/backend/Avatar/SadTalker/checkpoints/`

### Required Checkpoints:
```
checkpoints/
├── mapping_00109-model.pth.tar         (~200 MB)
├── mapping_00229-model.pth.tar         (~200 MB)
├── SadTalker_V0.0.2_256.safetensors   (~400 MB)
├── SadTalker_V0.0.2_512.safetensors   (~400 MB)
├── epoch_20.pth                        (~350 MB)
├── BFM/
│   ├── BFM_model_front.mat            (~50 MB)
│   └── std_exp.txt                    (~1 KB)
└── hub/
    └── checkpoints/
        └── s3fd-619a316812.pth        (~90 MB)
```

**Total Size**: ~1.7 GB

### GFPGAN (Face Enhancement):
```
gfpgan/
└── GFPGANv1.4.pth                     (~350 MB)
```

---

## 3️⃣ CHATTERBOX TTS (Voice Cloning)

### Location:
`~/.cache/huggingface/hub/` (auto-downloaded)

### Model Components:
```
models--facebook--wav2vec2-base-960h/
└── snapshots/[hash]/                   (~360 MB)
    ├── pytorch_model.bin
    ├── config.json
    └── preprocessor_config.json

models--Zyphra--Chatterbox-TTS/
└── snapshots/[hash]/                   (~1.2 GB)
    ├── diffusion_pytorch_model.safetensors
    ├── config.json
    └── model_index.json

models--charactr--vocos-mel-24khz/
└── snapshots/[hash]/                   (~80 MB)
    ├── pytorch_model.bin
    └── config.json
```

**Total Size**: ~1.6 GB

---

## 4️⃣ WHISPER STT (Speech Recognition)

### Location:
`~/.cache/whisper/` (auto-downloaded)

### Models:
```
base.pt                                 (~140 MB)
# OR choose one:
tiny.pt                                 (~39 MB)
small.pt                                (~244 MB)
medium.pt                               (~769 MB)
large.pt                                (~1.5 GB)
```

**Recommended**: `base.pt` for speed/accuracy balance

---

## 5️⃣ PERTH (Face Landmarks)

### Location:
`~/.cache/perth/` (auto-downloaded)

### Model:
```
perth_implicit_250k.pth                 (~200 MB)
```

---

## 6️⃣ INSIGHTFACE (Face Analysis)

### Location:
`~/.insightface/models/` (auto-downloaded)

### Models:
```
buffalo_l/
├── det_10g.onnx                        (~17 MB)
├── w600k_r50.onnx                      (~167 MB)
└── [other detection models]            (~300 MB total)
```

---

## 📊 TOTAL STORAGE REQUIREMENTS

| Component | Size | Priority |
|-----------|------|----------|
| Ditto PyTorch | ~1.9 GB | ⭐⭐⭐ Required |
| Ditto TensorRT | ~2.5 GB | Optional (faster) |
| SadTalker | ~1.7 GB | ⭐⭐ Alternative |
| ChatterBox TTS | ~1.6 GB | ⭐⭐⭐ Required |
| Whisper STT | ~0.14 GB | ⭐⭐⭐ Required |
| Perth | ~0.2 GB | ⭐⭐⭐ Required |
| InsightFace | ~0.3 GB | ⭐⭐⭐ Required |
| GFPGAN | ~0.35 GB | ⭐ Optional |

**MINIMUM REQUIRED**: ~6 GB
**FULL INSTALL**: ~9 GB

---

## 🗂️ ADDITIONAL FILES TO BACKUP

### Reference Files:
```
voice-clone-chat-boilerplate/backend/Avatar/References/
└── ref_1761131562372.jpg               # Reference face image

voice-clone-chat-boilerplate/backend/audio/reference_voices/
└── ref_1761118578.wav                  # Reference voice audio
```

### Configuration:
```
voice-clone-chat-boilerplate/backend/.env
voice-clone-chat-boilerplate/backend/audio/Nafay_Org.mp3
```

### Frontend Build (if applicable):
```
voice-clone-chat-boilerplate/frontend/voice-ui/node_modules/
voice-clone-chat-boilerplate/frontend/voice-ui/build/
```

---

## 📥 DOWNLOAD CHECKLIST

Use this checklist when setting up on new machine:

### Backend Models:
- [ ] Ditto PyTorch checkpoints (1.9 GB)
- [ ] Ditto config files
- [ ] SadTalker checkpoints (1.7 GB) - if using
- [ ] Reference image and audio files

### Auto-Downloaded (will download on first run):
- [ ] ChatterBox TTS (~1.6 GB)
- [ ] Whisper base model (~140 MB)
- [ ] Perth landmarks (~200 MB)
- [ ] InsightFace models (~300 MB)

### System Dependencies:
- [ ] FFmpeg installed
- [ ] CUDA 12.1+ installed
- [ ] cuDNN installed
- [ ] Python 3.12.3

---

## 💾 BACKUP COMMAND

To create a complete backup:

```bash
# Backend models
tar -czf backend_models.tar.gz \
  voice-clone-chat-boilerplate/backend/Avatar/ditto-talkinghead/checkpoints/ \
  voice-clone-chat-boilerplate/backend/Avatar/SadTalker/checkpoints/ \
  voice-clone-chat-boilerplate/backend/Avatar/References/ \
  voice-clone-chat-boilerplate/backend/audio/

# HuggingFace cache (ChatterBox, Whisper)
tar -czf huggingface_cache.tar.gz ~/.cache/huggingface/

# Other models
tar -czf other_models.tar.gz \
  ~/.cache/whisper/ \
  ~/.cache/perth/ \
  ~/.insightface/

# Configuration
tar -czf config_backup.tar.gz \
  voice-clone-chat-boilerplate/backend/.env \
  voice-clone-chat-boilerplate/backend/audio/Nafay_Org.mp3
```

**Total backup size**: ~6-9 GB compressed

---

## 🚀 QUICK MIGRATION

See `MIGRATION_GUIDE.md` for step-by-step setup on new machine.

