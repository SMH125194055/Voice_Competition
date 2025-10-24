#!/bin/bash

echo "🧪 Testing parallel pipeline with curl..."
echo ""

curl -N -X POST http://localhost:8000/api/parallel-pipeline/generate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is 2 plus 2?",
    "reference_image": "Avatar/References/ref_1761131562372.jpg",
    "reference_audio": "audio/reference_voices/ref_1761118578.wav"
  }' \
  2>&1 | while IFS= read -r line; do
    echo "[$(date +%H:%M:%S)] $line"
done

echo ""
echo "✅ Test complete"

