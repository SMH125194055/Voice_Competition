#!/bin/bash
# ============================================================================
# QUICK SETUP SCRIPT - Voice Competition Project
# ============================================================================
# Created: October 24, 2025
# 
# This script automates the complete installation of:
# - ChatterBox TTS (Text-to-Speech)
# - SadTalker (Avatar Generation - Optional)
# - Ditto-TalkingHead (Avatar Generation - Primary)
# - Whisper STT (Speech-to-Text)
# 
# Usage:
#   ./quick_setup.sh
# 
# ============================================================================

set -e  # Exit on error

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║           VOICE COMPETITION PROJECT - QUICK SETUP SCRIPT                ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Created: October 24, 2025"
echo "Python Required: 3.12.3"
echo "CUDA Required: 12.1+"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ============================================================================
# STEP 1: Check Python version
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 STEP 1/6: Checking Python version..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 not found!"
    echo "   Install: sudo add-apt-repository ppa:deadsnakes/ppa -y && sudo apt install python3.12 python3.12-venv"
    exit 1
fi

PYTHON_VERSION=$(python3.12 --version)
echo "✅ $PYTHON_VERSION found"
echo ""

# ============================================================================
# STEP 2: Check/Create Virtual Environment
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 STEP 2/6: Setting up virtual environment..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -d "venv" ]; then
    echo "Creating new virtual environment..."
    python3.12 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo "✅ pip upgraded"
echo ""

# ============================================================================
# STEP 3: Install PyTorch with CUDA
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔥 STEP 3/6: Installing PyTorch with CUDA 12.1..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if PyTorch is already installed
if python -c "import torch" 2>/dev/null; then
    TORCH_VERSION=$(python -c "import torch; print(torch.__version__)")
    CUDA_AVAILABLE=$(python -c "import torch; print(torch.cuda.is_available())")
    echo "PyTorch already installed: $TORCH_VERSION"
    echo "CUDA available: $CUDA_AVAILABLE"
    
    if [ "$CUDA_AVAILABLE" = "False" ]; then
        echo "⚠️  CUDA not available in current PyTorch installation"
        echo "Reinstalling PyTorch with CUDA support..."
        pip uninstall torch torchvision torchaudio -y
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    else
        echo "✅ PyTorch with CUDA already installed"
    fi
else
    echo "Installing PyTorch with CUDA 12.1..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    echo "✅ PyTorch installed"
fi

# Verify installation
python -c "import torch; print(f'\n✅ PyTorch {torch.__version__}'); print(f'✅ CUDA available: {torch.cuda.is_available()}'); print(f'✅ CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"
echo ""

# ============================================================================
# STEP 4: Install Requirements
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 STEP 4/6: Installing all requirements..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "requirements_complete_20251024.txt" ]; then
    echo "Installing from requirements_complete_20251024.txt..."
    pip install -r requirements_complete_20251024.txt
    echo "✅ All requirements installed"
else
    echo "⚠️  requirements_complete_20251024.txt not found!"
    echo "   Falling back to requirements.txt..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        echo "✅ Requirements installed from requirements.txt"
    else
        echo "❌ No requirements file found!"
        exit 1
    fi
fi
echo ""

# ============================================================================
# STEP 5: Install Perth
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👤 STEP 5/6: Installing Perth (Face Landmarks)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if python -c "import perth" 2>/dev/null; then
    echo "✅ Perth already installed"
else
    echo "Installing Perth from GitHub..."
    pip install git+https://github.com/KwaiVGI/perth.git
    echo "✅ Perth installed"
fi
echo ""

# ============================================================================
# STEP 6: Check Model Weights
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎬 STEP 6/6: Checking model weights..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "download_model_weights.py" ]; then
    python download_model_weights.py
else
    echo "⚠️  download_model_weights.py not found"
    echo "   Skipping model weights check"
fi
echo ""

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ INSTALLATION COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 Installed:"
echo "   ✅ Python 3.12 virtual environment"
echo "   ✅ PyTorch with CUDA 12.1"
echo "   ✅ All requirements (60+ packages)"
echo "   ✅ Perth face landmarks"
echo ""
echo "🎬 Model Weights:"
echo "   ✅ Auto-download models (will download on first run)"
echo "   ⚠️  Ditto weights (check manually - see above)"
echo ""
echo "🚀 Next Steps:"
echo ""
echo "1. Configure .env file:"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "2. Start backend:"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --host 0.0.0.0 --port 8000"
echo ""
echo "3. Test installation:"
echo "   cd ../../"
echo "   python test_online_fixed.py"
echo ""
echo "📚 Documentation:"
echo "   - INSTALLATION_GUIDE.md"
echo "   - QUICK_START.md"
echo "   - MODEL_WEIGHTS_CHECKLIST.md"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

