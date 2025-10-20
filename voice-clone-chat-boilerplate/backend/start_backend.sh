#!/bin/bash
# Quick Start Script for Backend

echo "🚀 Starting Voice Clone Chat Backend..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Check if activation worked
if [ $? -eq 0 ]; then
    echo "✅ Virtual environment activated"
else
    echo "❌ Failed to activate virtual environment"
    echo "   Run: python3 -m venv venv"
    exit 1
fi

# Start the server
echo "🌐 Starting FastAPI server on port 8001..."
echo "   Access at: http://127.0.0.1:8001"
echo "   Press CTRL+C to stop"
echo ""

uvicorn main:app --reload --port 8001

