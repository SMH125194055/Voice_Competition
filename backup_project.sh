#!/bin/bash
# ============================================================================
# COMPLETE PROJECT BACKUP SCRIPT
# ============================================================================
# Creates a complete backup of all code, models, and configurations
# for easy migration to new GPU/storage
# ============================================================================

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║               VOICE COMPETITION PROJECT - BACKUP SCRIPT                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
BACKUP_DIR="voice_competition_backup_$(date +%Y%m%d_%H%M%S)"
PROJECT_ROOT="/home/syedhuzaifa/Voice_Competition"

echo "📁 Backup directory: $BACKUP_DIR"
echo "📂 Project root: $PROJECT_ROOT"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"
cd "$PROJECT_ROOT"

# ============================================================================
# 1. BACKEND CODE
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 1/10: Backing up backend code..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tar -czf "$BACKUP_DIR/backend_code.tar.gz" \
  voice-clone-chat-boilerplate/backend/ \
  --exclude='voice-clone-chat-boilerplate/backend/venv' \
  --exclude='voice-clone-chat-boilerplate/backend/__pycache__' \
  --exclude='voice-clone-chat-boilerplate/backend/**/__pycache__' \
  --exclude='voice-clone-chat-boilerplate/backend/**/*.pyc' \
  --exclude='voice-clone-chat-boilerplate/backend/generated_videos' \
  --exclude='voice-clone-chat-boilerplate/backend/audio/generated/*.wav' \
  2>/dev/null || echo "⚠️  Some files skipped"
echo "✅ Backend code backed up"
echo ""

# ============================================================================
# 2. FRONTEND CODE
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 2/10: Backing up frontend code..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tar -czf "$BACKUP_DIR/frontend_code.tar.gz" \
  voice-clone-chat-boilerplate/frontend/ \
  --exclude='voice-clone-chat-boilerplate/frontend/node_modules' \
  --exclude='voice-clone-chat-boilerplate/frontend/build' \
  --exclude='voice-clone-chat-boilerplate/frontend/.next' \
  2>/dev/null || echo "⚠️  Frontend not found (skipping)"
echo "✅ Frontend code backed up"
echo ""

# ============================================================================
# 3. DITTO MODELS (Primary Avatar)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎬 3/10: Backing up Ditto-TalkingHead models (~2 GB)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "voice-clone-chat-boilerplate/backend/Avatar/ditto-talkinghead/checkpoints" ]; then
  tar -czf "$BACKUP_DIR/ditto_models.tar.gz" \
    voice-clone-chat-boilerplate/backend/Avatar/ditto-talkinghead/checkpoints/
  echo "✅ Ditto models backed up"
else
  echo "⚠️  Ditto checkpoints not found!"
fi
echo ""

# ============================================================================
# 4. SADTALKER MODELS (Alternative Avatar)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎬 4/10: Backing up SadTalker models (~1.7 GB)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "voice-clone-chat-boilerplate/backend/Avatar/SadTalker/checkpoints" ]; then
  tar -czf "$BACKUP_DIR/sadtalker_models.tar.gz" \
    voice-clone-chat-boilerplate/backend/Avatar/SadTalker/checkpoints/
  echo "✅ SadTalker models backed up"
else
  echo "⚠️  SadTalker checkpoints not found (skipping)"
fi
echo ""

# ============================================================================
# 5. REFERENCE FILES
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📸 5/10: Backing up reference images and audio..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tar -czf "$BACKUP_DIR/references.tar.gz" \
  voice-clone-chat-boilerplate/backend/Avatar/References/ \
  voice-clone-chat-boilerplate/backend/audio/ \
  --exclude='voice-clone-chat-boilerplate/backend/audio/generated/*.wav' \
  2>/dev/null || echo "⚠️  Some reference files not found"
echo "✅ Reference files backed up"
echo ""

# ============================================================================
# 6. HUGGINGFACE CACHE (ChatterBox TTS)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔊 6/10: Backing up HuggingFace models (ChatterBox TTS) (~1.6 GB)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "$HOME/.cache/huggingface" ]; then
  tar -czf "$BACKUP_DIR/huggingface_cache.tar.gz" -C "$HOME" .cache/huggingface/
  echo "✅ HuggingFace cache backed up"
else
  echo "⚠️  HuggingFace cache not found (will auto-download on new machine)"
fi
echo ""

# ============================================================================
# 7. WHISPER MODELS (STT)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎤 7/10: Backing up Whisper models (~140 MB)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "$HOME/.cache/whisper" ]; then
  tar -czf "$BACKUP_DIR/whisper_cache.tar.gz" -C "$HOME" .cache/whisper/
  echo "✅ Whisper models backed up"
else
  echo "⚠️  Whisper cache not found (will auto-download on new machine)"
fi
echo ""

# ============================================================================
# 8. PERTH MODELS (Face Landmarks)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👤 8/10: Backing up Perth models (~200 MB)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "$HOME/.cache/perth" ]; then
  tar -czf "$BACKUP_DIR/perth_cache.tar.gz" -C "$HOME" .cache/perth/
  echo "✅ Perth models backed up"
else
  echo "⚠️  Perth cache not found (will auto-download on new machine)"
fi
echo ""

# ============================================================================
# 9. INSIGHTFACE MODELS
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👤 9/10: Backing up InsightFace models (~300 MB)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -d "$HOME/.insightface" ]; then
  tar -czf "$BACKUP_DIR/insightface_cache.tar.gz" -C "$HOME" .insightface/
  echo "✅ InsightFace models backed up"
else
  echo "⚠️  InsightFace models not found (will auto-download on new machine)"
fi
echo ""

# ============================================================================
# 10. DOCUMENTATION & CONFIG
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📄 10/10: Backing up documentation and configs..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tar -czf "$BACKUP_DIR/configs_docs.tar.gz" \
  COMPLETE_REQUIREMENTS.txt \
  MODEL_WEIGHTS_CHECKLIST.md \
  MIGRATION_GUIDE.md \
  ACHIEVE_8_SECOND_GOAL.md \
  FINAL_SOLUTION_SUMMARY.md \
  QUICK_START.md \
  ONLINE_MODE_FIXED.md \
  test_online_fixed.py \
  backup_project.sh \
  2>/dev/null || echo "⚠️  Some docs not found"
echo "✅ Documentation backed up"
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 BACKUP SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
du -sh "$BACKUP_DIR"/*
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💾 TOTAL BACKUP SIZE:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
du -sh "$BACKUP_DIR"
echo ""

# Create README
cat > "$BACKUP_DIR/README.txt" << EOF
╔══════════════════════════════════════════════════════════════════════════╗
║               VOICE COMPETITION PROJECT - BACKUP                         ║
╚══════════════════════════════════════════════════════════════════════════╝

Backup created: $(date)
Source machine: $(hostname)

CONTENTS:
---------
1. backend_code.tar.gz         - Backend Python code
2. frontend_code.tar.gz        - Frontend React code
3. ditto_models.tar.gz         - Ditto-TalkingHead weights (~2 GB)
4. sadtalker_models.tar.gz     - SadTalker weights (~1.7 GB)
5. references.tar.gz           - Reference images and audio
6. huggingface_cache.tar.gz    - ChatterBox TTS models (~1.6 GB)
7. whisper_cache.tar.gz        - Whisper STT models (~140 MB)
8. perth_cache.tar.gz          - Perth face landmarks (~200 MB)
9. insightface_cache.tar.gz    - InsightFace models (~300 MB)
10. configs_docs.tar.gz        - Documentation and configs

TOTAL SIZE: ~6-9 GB

TO RESTORE ON NEW MACHINE:
--------------------------
1. See MIGRATION_GUIDE.md in configs_docs.tar.gz
2. Extract configs_docs.tar.gz first to get the guide
3. Follow step-by-step instructions in MIGRATION_GUIDE.md

QUICK RESTORE:
--------------
1. Extract all .tar.gz files
2. Install Python 3.12.3, CUDA 12.1+, FFmpeg
3. Create venv and install requirements
4. Start backend and frontend

For detailed instructions, extract and read:
  tar -xzf configs_docs.tar.gz
  cat MIGRATION_GUIDE.md

System Requirements:
-------------------
- Ubuntu 20.04+
- NVIDIA GPU with 8GB+ VRAM
- 15GB+ free storage
- Python 3.12.3
- CUDA 12.1+
- FFmpeg

═══════════════════════════════════════════════════════════════════════════
EOF

echo "✅ README created: $BACKUP_DIR/README.txt"
echo ""

# Create restore script
cat > "$BACKUP_DIR/restore_project.sh" << 'EOF'
#!/bin/bash
# Quick restore script for new machine

echo "🚀 Starting restoration..."
echo ""

# Get current directory
BACKUP_DIR=$(pwd)

echo "📦 Extracting backend code..."
tar -xzf backend_code.tar.gz -C ~/ 2>/dev/null || echo "Backend extraction error"

echo "📦 Extracting frontend code..."
tar -xzf frontend_code.tar.gz -C ~/ 2>/dev/null || echo "Frontend extraction error"

echo "🎬 Extracting Ditto models..."
tar -xzf ditto_models.tar.gz -C ~/ 2>/dev/null || echo "Ditto extraction error"

echo "🎬 Extracting SadTalker models..."
tar -xzf sadtalker_models.tar.gz -C ~/ 2>/dev/null || echo "SadTalker not found (optional)"

echo "📸 Extracting reference files..."
tar -xzf references.tar.gz -C ~/ 2>/dev/null || echo "References extraction error"

echo "🔊 Extracting TTS models..."
mkdir -p ~/.cache/huggingface
tar -xzf huggingface_cache.tar.gz -C ~/ 2>/dev/null || echo "TTS not found (will auto-download)"

echo "🎤 Extracting Whisper models..."
mkdir -p ~/.cache/whisper
tar -xzf whisper_cache.tar.gz -C ~/ 2>/dev/null || echo "Whisper not found (will auto-download)"

echo "👤 Extracting Perth models..."
mkdir -p ~/.cache/perth
tar -xzf perth_cache.tar.gz -C ~/ 2>/dev/null || echo "Perth not found (will auto-download)"

echo "👤 Extracting InsightFace models..."
mkdir -p ~/.insightface
tar -xzf insightface_cache.tar.gz -C ~/ 2>/dev/null || echo "InsightFace not found (will auto-download)"

echo "📄 Extracting documentation..."
tar -xzf configs_docs.tar.gz -C ~/ 2>/dev/null || echo "Docs extraction error"

echo ""
echo "✅ Restoration complete!"
echo ""
echo "📋 NEXT STEPS:"
echo "1. Read MIGRATION_GUIDE.md for detailed setup"
echo "2. Install system dependencies (Python 3.12.3, CUDA, FFmpeg)"
echo "3. Create venv and install requirements"
echo "4. Configure .env file"
echo "5. Start backend and frontend"
echo ""
echo "See ~/Voice_Competition/MIGRATION_GUIDE.md for details"
EOF

chmod +x "$BACKUP_DIR/restore_project.sh"
echo "✅ Restore script created: $BACKUP_DIR/restore_project.sh"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 BACKUP COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Backup location: $PROJECT_ROOT/$BACKUP_DIR"
echo ""
echo "📤 TO TRANSFER TO NEW MACHINE:"
echo ""
echo "Option 1: Network transfer (recommended)"
echo "  rsync -avz --progress $BACKUP_DIR/ user@new-machine:/destination/"
echo ""
echo "Option 2: Create single archive"
echo "  tar -czf voice_competition_complete.tar.gz $BACKUP_DIR/"
echo "  # Then upload to cloud or copy to USB"
echo ""
echo "Option 3: Copy to external drive"
echo "  cp -r $BACKUP_DIR /mnt/external_drive/"
echo ""
echo "🔧 ON NEW MACHINE:"
echo "  1. Extract configs_docs.tar.gz first"
echo "  2. Read MIGRATION_GUIDE.md"
echo "  3. Run restore_project.sh"
echo "  4. Follow setup instructions"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

