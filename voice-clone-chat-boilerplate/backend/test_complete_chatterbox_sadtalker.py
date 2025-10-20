#!/usr/bin/env python3
"""
Complete test of ChatterBox TTS + SadTalker pipeline
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).parent
SADTALKER_DIR = BACKEND_DIR / 'Avatar' / 'SadTalker'
VOICE_AUDIO = BACKEND_DIR / 'audio' / 'Nafay_Org.mp3'
SOURCE_IMAGE = BACKEND_DIR / 'audio' / 'Huzaifa.jpg'
RESULT_DIR = BACKEND_DIR / 'results' / 'complete_test'

# Ensure paths exist
if not VOICE_AUDIO.exists():
    print(f"❌ Voice audio file not found: {VOICE_AUDIO}")
    sys.exit(1)

if not SOURCE_IMAGE.exists():
    print(f"❌ Source image file not found: {SOURCE_IMAGE}")
    sys.exit(1)

# Create result directory
RESULT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("COMPLETE PIPELINE TEST: ChatterBox TTS + SadTalker Talking Head Generation")
print("=" * 80)
print()

# Step 1: Test ChatterBox TTS
print("Step 1: Testing ChatterBox TTS voice cloning...")
print("-" * 80)

try:
    # Import TTS functions
    sys.path.insert(0, str(BACKEND_DIR))
    from utils import tts as tts_module
    
    # Initialize TTS with voice cloning
    print(f"Initializing ChatterBox TTS with voice: {VOICE_AUDIO}")
    tts_module.initialize_tts('local', str(VOICE_AUDIO))
    
    # Check if model was initialized (check the module's tts_model variable)
    if not tts_module.tts_model:
        print("❌ Failed to initialize ChatterBox TTS")
        sys.exit(1)
    
    print("✅ ChatterBox TTS initialized successfully")
    print()
    
    # Generate speech
    test_text = "Hello! This is a test of voice cloning with ChatterBox and talking head generation with SadTalker."
    print(f"Generating speech for: '{test_text}'")
    
    async def generate_tts():
        return await tts_module.text_to_speech(test_text, 'local', str(VOICE_AUDIO))
    
    generated_audio = asyncio.run(generate_tts())
    
    if not generated_audio or not os.path.exists(generated_audio):
        print("❌ Failed to generate speech")
        sys.exit(1)
    
    print(f"✅ Speech generated successfully: {generated_audio}")
    print()
    
except Exception as e:
    print(f"❌ ChatterBox TTS test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Generate talking head with SadTalker
print("Step 2: Generating talking head with SadTalker...")
print("-" * 80)

try:
    # Change to SadTalker directory
    os.chdir(str(SADTALKER_DIR))
    
    # Run SadTalker inference with the generated audio
    cmd = [
        sys.executable,
        'inference.py',
        '--driven_audio', generated_audio,
        '--source_image', str(SOURCE_IMAGE),
        '--result_dir', str(RESULT_DIR),
        '--enhancer', 'gfpgan'
    ]
    
    print(f"Running SadTalker...")
    result = subprocess.run(cmd, check=True, capture_output=False, text=True)
    
    # Find the generated video
    video_files = list(RESULT_DIR.glob('*.mp4'))
    if not video_files:
        print("❌ No video file found in result directory")
        sys.exit(1)
    
    final_video = sorted(video_files)[-1]  # Get the most recent
    print(f"✅ Talking head video generated successfully: {final_video}")
    print()
    
except subprocess.CalledProcessError as e:
    print(f"❌ SadTalker generation failed with error code {e.returncode}")
    sys.exit(1)
except Exception as e:
    print(f"❌ SadTalker test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Success!
print("=" * 80)
print("🎉 COMPLETE PIPELINE TEST PASSED!")
print("=" * 80)
print()
print(f"📝 Original text: {test_text}")
print(f"🎤 Voice reference: {VOICE_AUDIO}")
print(f"🎵 Generated audio: {generated_audio}")
print(f"🖼️  Source image: {SOURCE_IMAGE}")
print(f"🎬 Final video: {final_video}")
print()
print("All components working together successfully!")
print("=" * 80)
