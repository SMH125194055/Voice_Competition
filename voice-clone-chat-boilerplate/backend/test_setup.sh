#!/bin/bash
# Quick test to verify backend setup

echo "🔍 Backend Setup Verification"
echo "================================"
echo ""

# Check if we're in the right directory
BACKEND_DIR="/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend"
CURRENT_DIR=$(pwd)

if [ "$CURRENT_DIR" != "$BACKEND_DIR" ]; then
    echo "📂 Moving to backend directory..."
    cd "$BACKEND_DIR"
fi

echo "📍 Current directory: $(pwd)"
echo ""

# Check for venv
if [ -d "venv" ]; then
    echo "✅ Virtual environment found"
else
    echo "❌ Virtual environment not found!"
    echo "   Creating it now..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo "✅ Virtual environment created"
    else
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
fi

# Check activate script
if [ -f "venv/bin/activate" ]; then
    echo "✅ Activation script found"
else
    echo "❌ Activation script not found"
    exit 1
fi

# Test activation
echo ""
echo "🧪 Testing activation..."
source venv/bin/activate

if [ $? -eq 0 ]; then
    echo "✅ Virtual environment activated successfully"
    
    # Check Python
    PYTHON_VERSION=$(python --version 2>&1)
    echo "   Python: $PYTHON_VERSION"
    
    # Check key packages
    echo ""
    echo "📦 Checking packages..."
    python -c "import fastapi; print('   ✅ FastAPI')" 2>/dev/null || echo "   ❌ FastAPI"
    python -c "import torch; print('   ✅ Torch')" 2>/dev/null || echo "   ❌ Torch"
    python -c "import whisper; print('   ✅ Whisper')" 2>/dev/null || echo "   ❌ Whisper"
    python -c "import anthropic; print('   ✅ Anthropic')" 2>/dev/null || echo "   ❌ Anthropic"
    
    echo ""
    echo "================================"
    echo "✅ Setup verification complete!"
    echo ""
    echo "To start the backend:"
    echo "  cd $BACKEND_DIR"
    echo "  source venv/bin/activate"
    echo "  uvicorn main:app --reload --port 8001"
    echo ""
    echo "Or simply run:"
    echo "  ./start_backend.sh"
    
else
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

