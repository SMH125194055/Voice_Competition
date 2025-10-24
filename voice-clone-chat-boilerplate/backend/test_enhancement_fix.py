#!/usr/bin/env python3
"""
Test script to verify GFPGAN enhancement is working correctly.
This will test the avatar generator with and without enhancement.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project paths
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, 'Avatar', 'SadTalker'))

def test_enhancement():
    """Test GFPGAN enhancement initialization and usage."""
    
    print("="*80)
    print("🧪 TESTING GFPGAN ENHANCEMENT FIX")
    print("="*80)
    print()
    
    # Test 1: Check avatar_config.py
    print("TEST 1: Checking avatar_config.py...")
    from avatar_config import AVATAR_ENHANCER
    print(f"   AVATAR_ENHANCER = {AVATAR_ENHANCER}")
    
    if AVATAR_ENHANCER and AVATAR_ENHANCER.lower() != "none":
        print("   ✅ Config is correct - GFPGAN should be enabled")
    else:
        print("   ❌ Config issue - AVATAR_ENHANCER is None or 'none'")
        print("   📝 Check: /backend/avatar_config.py line 16")
    print()
    
    # Test 2: Initialize avatar generator with GFPGAN
    print("TEST 2: Initializing avatar generator with GFPGAN...")
    try:
        from utils.avatar_generator import initialize_avatar_generator, get_avatar_generator
        
        # Force initialize with gfpgan
        success = initialize_avatar_generator(
            device='cuda:1',  # Use your AVATAR_DEVICE
            size=256,
            enhancer='gfpgan',  # Explicitly set to gfpgan
            pool_size=1
        )
        
        if success:
            print("   ✅ Avatar generator initialized")
            
            generator = get_avatar_generator()
            if generator:
                print(f"   📊 Generator enhancer: {generator.enhancer}")
                
                if generator.enhancer == 'gfpgan':
                    print("   ✅ GFPGAN enhancer is properly set!")
                elif generator.enhancer is None:
                    print("   ❌ Enhancer is None - initialization failed")
                else:
                    print(f"   ⚠️ Unexpected enhancer value: {generator.enhancer}")
            else:
                print("   ❌ Generator is None")
        else:
            print("   ❌ Initialization failed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Test 3: Generate test video WITH enhancement
    print("TEST 3: Generating test video WITH enhancement...")
    try:
        import asyncio
        from utils.avatar_generator import generate_avatar
        
        # Prepare test files
        audio_file = "/tmp/test_audio_3s.wav"
        image_file = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/Avatar/References/ref_1761131562372.jpg"
        output_dir = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/Avatar/output"
        
        # Create 3-second silent audio
        if not os.path.exists(audio_file):
            print("   📝 Creating test audio file...")
            import subprocess
            subprocess.run([
                'ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=16000:cl=mono',
                '-t', '3', '-y', audio_file
            ], capture_output=True)
        
        if os.path.exists(image_file):
            print("   🎬 Generating video WITH enhancement (enable_enhancer=True)...")
            
            async def test_generate():
                video_path = await generate_avatar(
                    audio_path=audio_file,
                    image_path=image_file,
                    output_dir=output_dir,
                    fast_mode=True,
                    preprocess='crop',
                    pic_size=256,
                    enable_enhancer=True  # ⭐ ENABLE ENHANCEMENT
                )
                return video_path
            
            video_path = asyncio.run(test_generate())
            
            if video_path and os.path.exists(video_path):
                size_mb = os.path.getsize(video_path) / (1024 * 1024)
                print(f"   ✅ Video generated: {video_path}")
                print(f"   📊 File size: {size_mb:.2f} MB")
                print()
                print("   🔍 CHECK LOGS ABOVE FOR:")
                print("       - '🎨 Face Enhancement: ENABLED (enhancer=gfpgan)'")
                print("       - 'face enhancer....' message")
                print("       - Enhanced video should take 2-5 seconds longer")
            else:
                print("   ❌ Video generation failed")
        else:
            print(f"   ⚠️ Test image not found: {image_file}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Summary
    print("="*80)
    print("📋 SUMMARY")
    print("="*80)
    print()
    print("If you see '🎨 Face Enhancement: ENABLED (enhancer=gfpgan)' above:")
    print("   ✅ Enhancement is working correctly!")
    print()
    print("If you see '🎨 Face Enhancement: ENABLED (enhancer=None)' above:")
    print("   ❌ Enhancement is NOT working - generator wasn't initialized with GFPGAN")
    print()
    print("💡 Solution:")
    print("   1. Make sure avatar_config.py has: AVATAR_ENHANCER = 'gfpgan'")
    print("   2. RESTART the backend: Ctrl+C, then 'python main.py'")
    print("   3. The generator is initialized at STARTUP, not per-request")
    print()

if __name__ == "__main__":
    test_enhancement()




