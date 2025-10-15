#!/bin/bash

# Avatar + Voice Cloning Server Startup Script

echo "🎬 Starting Avatar + Voice Cloning Server..."
echo "============================================"

# Navigate to backend
cd "$(dirname "$0")/backend" || exit 1

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please set up the backend first."
    exit 1
fi

# Activate venv
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "🐍 Python version: $python_version"

# Check CUDA availability
echo "🎮 Checking GPU availability..."
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')" 2>/dev/null || echo "⚠️  PyTorch not installed"

# Display configuration
echo ""
echo "⚙️  Avatar Configuration:"
echo "   AVATAR_ENABLED=${AVATAR_ENABLED:-true}"
echo "   AVATAR_DEVICE=${AVATAR_DEVICE:-cuda}"
echo "   AVATAR_SIZE=${AVATAR_SIZE:-256}"
echo "   AVATAR_ENHANCER=${AVATAR_ENHANCER:-gfpgan}"
echo ""

# Start server
echo "🚀 Starting FastAPI server..."
echo "============================================"
echo ""
echo "📡 Server will be available at:"
echo "   http://localhost:8000"
echo ""
echo "📚 Documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "🎬 Avatar endpoints:"
echo "   POST /upload-reference-picture"
echo "   GET  /list-reference-pictures"
echo "   POST /vad-chat-avatar-stream"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================================"
echo ""

# Run server
python main.py

# Cleanup
echo ""
echo "🛑 Server stopped"
deactivate


