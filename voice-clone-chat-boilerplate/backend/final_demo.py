#!/usr/bin/env python3
"""
Final demonstration: Generate talking head video with cloned voice
Using ChatterBox TTS + SadTalker
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

# Configuration
BACKEND_DIR = Path(__file__).parent
SADTALKER_DIR = BACKEND_DIR / 'Avatar' / 'SadTalker'

# User-provided files
VOICE_REFERENCE = BACKEND_DIR / 'audio' / 'Nafay_Org.mp3'
SOURCE_IMAGE = BACKEND_DIR / 'audio' / 'Huzaifa.jpg'

# Output directory
OUTPUT_DIR = BACKEND_DIR / 'results' / 'final_demo'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Text to speak
TEXT_TO_SPEAK = """
Hello! This is a demonstration of the complete pipeline.
I am using ChatterBox for voice cloning and SadTalker for generating the talking head video.
The voice is cloned from the provided audio sample, and the face is animated from the provided image.
This technology can be used for various applications including virtual assistants, content creation, and educational videos.
"""

print("=" * 80)
print("FINAL DEMONSTRATION")
print("ChatterBox TTS + SadTalker Talking Head Generation")
print("=" * 80)
print()
print(f"Voice Reference: {VOICE_REFERENCE}")
print(f"Source Image: {SOURCE_IMAGE}")
print(f"Output Directory: {OUTPUT_DIR}")
print()
print(f"Text to speak:\n{TEXT_TO_SPEAK}")
print()
print("=" * 80)
print()

# Verify files exist
if not VOICE_REFERENCE.exists():
    print(f"❌ ERROR: Voice reference file not found: {VOICE_REFERENCE}")
    sys.exit(1)

if not SOURCE_IMAGE.exists():
    print(f"❌ ERROR: Source image file not found: {SOURCE_IMAGE}")
    sys.exit(1)

# Step 1: Generate voice using ChatterBox TTS
print("Step 1: Generating voice with ChatterBox TTS...")
print("-" * 80)

try:
    sys.path.insert(0, str(BACKEND_DIR))
    from utils import tts as tts_module
    
    # Initialize TTS
    print(f"Initializing ChatterBox TTS...")
    tts_module.initialize_tts('local', str(VOICE_REFERENCE))
    
    if not tts_module.tts_model:
        print("❌ Failed to initialize ChatterBox TTS")
        sys.exit(1)
    
    print("✅ ChatterBox TTS initialized")
    
    # Generate speech
    print("Generating speech...")
    
    async def generate():
        return await tts_module.text_to_speech(TEXT_TO_SPEAK, 'local', str(VOICE_REFERENCE))
    
    generated_audio = asyncio.run(generate())
    
    if not generated_audio or not os.path.exists(generated_audio):
        print("❌ Failed to generate speech")
        sys.exit(1)
    
    print(f"✅ Voice generated: {generated_audio}")
    audio_size = os.path.getsize(generated_audio) / 1024
    print(f"   Audio file size: {audio_size:.1f} KB")
    print()
    
except Exception as e:
    print(f"❌ ChatterBox TTS failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Generate talking head with SadTalker
print("Step 2: Generating talking head video with SadTalker...")
print("-" * 80)

try:
    os.chdir(str(SADTALKER_DIR))
    
    cmd = [
        sys.executable,
        'inference.py',
        '--driven_audio', generated_audio,
        '--source_image', str(SOURCE_IMAGE),
        '--result_dir', str(OUTPUT_DIR),
        '--enhancer', 'gfpgan'
    ]
    
    print("Running SadTalker inference...")
    print(f"Command: python inference.py \\")
    print(f"         --driven_audio {generated_audio} \\")
    print(f"         --source_image {SOURCE_IMAGE} \\")
    print(f"         --result_dir {OUTPUT_DIR} \\")
    print(f"         --enhancer gfpgan")
    print()
    
    result = subprocess.run(cmd, check=True, capture_output=False, text=True)
    
    # Find generated video
    video_files = list(OUTPUT_DIR.glob('*.mp4'))
    if not video_files:
        print("❌ No video file found")
        sys.exit(1)
    
    final_video = sorted(video_files)[-1]
    video_size = os.path.getsize(final_video) / 1024
    
    print()
    print("✅ Talking head video generated successfully!")
    print(f"   Video file: {final_video}")
    print(f"   Video size: {video_size:.1f} KB")
    print()
    
except subprocess.CalledProcessError as e:
    print(f"❌ SadTalker failed with error code {e.returncode}")
    sys.exit(1)
except Exception as e:
    print(f"❌ SadTalker failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Success summary
print("=" * 80)
print("🎉 SUCCESS! TALKING HEAD VIDEO GENERATED!")
print("=" * 80)
print()
print("Summary:")
print(f"  📝 Text spoken: {len(TEXT_TO_SPEAK.split())} words")
print(f"  🎤 Voice cloned from: {VOICE_REFERENCE.name}")
print(f"  🖼️  Face animated from: {SOURCE_IMAGE.name}")
print(f"  🎵 Generated audio: {Path(generated_audio).name} ({audio_size:.1f} KB)")
print(f"  🎬 Final video: {final_video.name} ({video_size:.1f} KB)")
print()
print(f"📂 Output location: {OUTPUT_DIR}")
print()
print("You can now view the generated video!")
print("=" * 80)





