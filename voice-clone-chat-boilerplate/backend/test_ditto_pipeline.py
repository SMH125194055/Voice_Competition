#!/usr/bin/env python3
"""Test Ditto pipeline with reference image and audio."""

import requests
import json
import time
import os

# API endpoint
BASE_URL = "http://localhost:8000"

# Reference files
REFERENCE_IMAGE_ID = "ref_1761131562372"
REFERENCE_AUDIO_ID = "ref_1761118578"

def test_idle_animation():
    """Test idle animation generation with Ditto."""
    print("=" * 80)
    print("🎬 Testing Ditto-TalkingHead Complete Pipeline")
    print("=" * 80)
    print(f"Reference Image ID: {REFERENCE_IMAGE_ID}")
    print(f"Reference Audio ID: {REFERENCE_AUDIO_ID}")
    print("")
    
    # Check avatar status
    print("1️⃣ Checking avatar model status...")
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        data = response.json()
        avatar_info = data.get('avatar', {})
        print(f"   Model: {avatar_info.get('model')}")
        print(f"   Device: {avatar_info.get('device')}")
        print(f"   Initialized: {avatar_info.get('initialized')}")
        print(f"   ✅ Avatar model loaded successfully!")
    else:
        print(f"   ❌ Failed to get status: {response.status_code}")
        return
    
    print("")
    
    # Generate idle animation
    print("2️⃣ Generating idle animation with Ditto...")
    payload = {
        "picture_id": REFERENCE_IMAGE_ID,
        "duration": 3,
        "fps": 25,
        "preprocess": "crop",
        "pic_size": 256,
        "enable_enhancement": False
    }
    
    print(f"   Request: {json.dumps(payload, indent=4)}")
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/generate-idle-animation",
        json=payload,
        timeout=120
    )
    elapsed_time = time.time() - start_time
    
    if response.status_code == 200:
        result = response.json()
        video_url = result.get('idle_video_url')
        print(f"   ✅ Video generated successfully!")
        print(f"   📹 Video URL: {video_url}")
        print(f"   ⏱️  Generation Time: {elapsed_time:.2f} seconds")
        print(f"   📊 Status: {result.get('status')}")
        
        # Check if file exists
        if video_url:
            video_path = video_url.replace('/avatars/idle_animations/', 'outputs/idle_animations/')
            if os.path.exists(video_path):
                file_size = os.path.getsize(video_path) / (1024 * 1024)
                print(f"   📁 File Size: {file_size:.2f} MB")
                print(f"   📂 Local Path: {video_path}")
            else:
                print(f"   ⚠️ Video file not found at: {video_path}")
    else:
        print(f"   ❌ Failed to generate video: {response.status_code}")
        print(f"   Error: {response.text}")
        return
    
    print("")
    print("=" * 80)
    print("🎉 Pipeline Test Complete!")
    print("=" * 80)

if __name__ == "__main__":
    test_idle_animation()

