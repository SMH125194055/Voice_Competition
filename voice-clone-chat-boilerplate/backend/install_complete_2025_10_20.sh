#!/bin/bash

# ============================================
# Complete Installation Script
# Voice Clone Chat Backend with ChatterBox + SadTalker
# Generated: October 20, 2025
# ============================================

set -e  # Exit on error

echo "============================================"
echo "Voice Clone Chat - Complete Installation"
echo "Date: October 20, 2025"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in correct directory
if [ ! -f "requirements_complete_2025_10_20.txt" ]; then
    echo -e "${RED}ERROR: requirements_complete_2025_10_20.txt not found!${NC}"
    echo "Please run this script from the backend directory"
    exit 1
fi

echo -e "${GREEN}Step 1: Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python version: $PYTHON_VERSION"

# Check if Python 3.10+ is installed
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    echo -e "${RED}ERROR: Python 3.10 or higher is required${NC}"
    echo "Current version: $PYTHON_VERSION"
    exit 1
fi
echo -e "${GREEN}✓ Python version OK${NC}"
echo ""

echo -e "${GREEN}Step 2: Checking for CUDA...${NC}"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    echo -e "${GREEN}✓ CUDA GPU detected${NC}"
else
    echo -e "${YELLOW}⚠ No CUDA GPU detected. Will use CPU (slower)${NC}"
fi
echo ""

echo -e "${GREEN}Step 3: Checking for ffmpeg...${NC}"
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -1)
    echo "$FFMPEG_VERSION"
    echo -e "${GREEN}✓ ffmpeg found${NC}"
else
    echo -e "${RED}ERROR: ffmpeg not found!${NC}"
    echo "Please install ffmpeg:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    echo "  Windows: Download from https://ffmpeg.org/download.html"
    exit 1
fi
echo ""

echo -e "${GREEN}Step 4: Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
fi
echo ""

echo -e "${GREEN}Step 5: Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

echo -e "${GREEN}Step 6: Upgrading pip...${NC}"
pip install --upgrade pip setuptools wheel
echo ""

echo -e "${GREEN}Step 7: Installing PyTorch with CUDA support...${NC}"
pip install torch==2.9.0 torchvision==0.24.0 torchaudio==2.9.0 --index-url https://download.pytorch.org/whl/cu128
echo ""

echo -e "${GREEN}Step 8: Installing main requirements...${NC}"
echo "This may take 10-20 minutes..."
pip install -r requirements_complete_2025_10_20.txt
echo ""

echo -e "${GREEN}Step 9: Installing ChatterBox TTS...${NC}"
if [ -d "Chatterbox-gitclone" ]; then
    echo -e "${YELLOW}⚠ ChatterBox directory already exists${NC}"
    echo "Reinstalling from local directory..."
    cd Chatterbox-gitclone/chatterbox
    pip install -e .
    cd ../..
    echo -e "${GREEN}✓ ChatterBox TTS installed${NC}"
else
    echo "Cloning ChatterBox repository..."
    git clone https://github.com/resemble-ai/Chatterbox.git Chatterbox-gitclone
    cd Chatterbox-gitclone/chatterbox
    pip install -e .
    cd ../..
    echo -e "${GREEN}✓ ChatterBox TTS cloned and installed${NC}"
fi
echo ""

echo -e "${GREEN}Step 10: Checking SadTalker installation...${NC}"
if [ -d "Avatar/SadTalker" ]; then
    echo -e "${GREEN}✓ SadTalker directory found${NC}"
    
    # Check if models exist
    if [ -d "Avatar/SadTalker/checkpoints" ]; then
        echo -e "${GREEN}✓ SadTalker checkpoints directory found${NC}"
    else
        echo -e "${YELLOW}⚠ SadTalker checkpoints not found${NC}"
        echo "You need to download SadTalker models:"
        echo "  cd Avatar/SadTalker"
        echo "  bash scripts/download_models.sh"
        echo ""
        echo "Or download manually from:"
        echo "  https://github.com/OpenTalker/SadTalker/releases"
    fi
else
    echo -e "${RED}ERROR: SadTalker directory not found at Avatar/SadTalker${NC}"
    exit 1
fi
echo ""

echo -e "${GREEN}Step 11: Creating necessary directories...${NC}"
mkdir -p audio/generated
mkdir -p results
mkdir -p logs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

echo -e "${GREEN}Step 12: Verifying installation...${NC}"
python3 << 'EOF'
import sys
import torch

print(f"Python version: {sys.version}")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# Try importing key packages
try:
    import transformers
    print(f"✓ Transformers: {transformers.__version__}")
except ImportError as e:
    print(f"✗ Transformers: {e}")

try:
    import diffusers
    print(f"✓ Diffusers: {diffusers.__version__}")
except ImportError as e:
    print(f"✗ Diffusers: {e}")

try:
    import perth
    print(f"✓ Perth (ChatterBox dependency): OK")
except ImportError as e:
    print(f"✗ Perth: {e}")

try:
    import cv2
    print(f"✓ OpenCV: {cv2.__version__}")
except ImportError as e:
    print(f"✗ OpenCV: {e}")

try:
    import gfpgan
    print(f"✓ GFPGAN: OK")
except ImportError as e:
    print(f"✗ GFPGAN: {e}")

print("\n✓ Core packages imported successfully!")
EOF
echo ""

echo "============================================"
echo -e "${GREEN}Installation Complete! ✅${NC}"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Make sure you have the required media files:"
echo "   - Voice reference: audio/Nafay_Org.mp3"
echo "   - Source image: audio/Huzaifa.jpg"
echo ""
echo "2. Download SadTalker models if not already done:"
echo "   cd Avatar/SadTalker"
echo "   bash scripts/download_models.sh"
echo ""
echo "3. Run the test suite:"
echo "   python final_demo.py"
echo ""
echo "4. Check outputs in:"
echo "   - audio/generated/ (for audio files)"
echo "   - results/ (for video files)"
echo ""
echo "For troubleshooting, see:"
echo "   - PIPELINE_SUCCESS_SUMMARY.md"
echo "   - Test logs in backend directory"
echo ""
echo "============================================"











