#!/usr/bin/env python3
"""
Direct test of SadTalker using the actual inference.py
"""

import os
import sys
import subprocess

# Paths
SADTALKER_DIR = os.path.join(os.path.dirname(__file__), 'Avatar', 'SadTalker')
AUDIO_PATH = os.path.join(os.path.dirname(__file__), 'audio', 'Nafay_Org.mp3')
IMAGE_PATH = os.path.join(os.path.dirname(__file__), 'audio', 'Huzaifa.jpg')
RESULT_DIR = os.path.join(os.path.dirname(__file__), 'results', 'sadtalker_test')

# Ensure paths exist
if not os.path.exists(AUDIO_PATH):
    print(f"❌ Audio file not found: {AUDIO_PATH}")
    sys.exit(1)

if not os.path.exists(IMAGE_PATH):
    print(f"❌ Image file not found: {IMAGE_PATH}")
    sys.exit(1)

# Create result directory
os.makedirs(RESULT_DIR, exist_ok=True)

print("🎬 Starting SadTalker talking head generation...")
print(f"  Image: {IMAGE_PATH}")
print(f"  Audio: {AUDIO_PATH}")
print(f"  Output: {RESULT_DIR}")
print()

# Change to SadTalker directory
os.chdir(SADTALKER_DIR)

# Run SadTalker inference
cmd = [
    sys.executable,
    'inference.py',
    '--driven_audio', AUDIO_PATH,
    '--source_image', IMAGE_PATH,
    '--result_dir', RESULT_DIR,
    '--enhancer', 'gfpgan'
]

print(f"Running command: {' '.join(cmd)}")
print()

try:
    result = subprocess.run(cmd, check=True, capture_output=False, text=True)
    print()
    print("✅ SadTalker generation completed successfully!")
    print(f"📁 Check the results in: {RESULT_DIR}")
except subprocess.CalledProcessError as e:
    print()
    print(f"❌ SadTalker generation failed with error code {e.returncode}")
    sys.exit(1)
except Exception as e:
    print()
    print(f"❌ Error: {e}")
    sys.exit(1)
