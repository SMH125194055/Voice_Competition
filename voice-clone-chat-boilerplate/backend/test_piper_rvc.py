"""
Test script for Piper TTS + RVC voice cloning pipeline.

This script tests:
1. Piper TTS for fast base speech generation
2. RVC for voice conversion (cloning)
3. Full pipeline with reference audio
"""
import os
import sys
import time

# Add backend to path
backend_path = os.path.dirname(__file__)
sys.path.insert(0, backend_path)

print("=" * 70)
print("PIPER TTS + RVC VOICE CLONING TEST")
print("=" * 70)

# Configuration
REFERENCE_AUDIO = "audio/Nafay_Org.mp3"
TEST_TEXT = "Hello! This is a test of Piper TTS with RVC voice cloning."
OUTPUT_AUDIO = "test_piper_rvc_output.wav"

print(f"\n1. Configuration:")
print(f"   - Reference Audio: {REFERENCE_AUDIO}")
print(f"   - Test Text: {TEST_TEXT}")
print(f"   - Output File: {OUTPUT_AUDIO}")

# Check if reference audio exists
if not os.path.exists(REFERENCE_AUDIO):
    print(f"\n[ERROR] Reference audio not found: {REFERENCE_AUDIO}")
    print("Please provide a reference audio file first.")
    sys.exit(1)
else:
    print(f"   [OK] Reference audio found")

# Step 1: Test Piper TTS
print("\n" + "=" * 70)
print("STEP 1: Testing Piper TTS (Base Speech Generation)")
print("=" * 70)

try:
    import piper
    print("[OK] Piper TTS installed")
except ImportError:
    print("[ERROR] Piper TTS not installed")
    print("\nSolution: Install with:")
    print("  pip install piper-tts")
    sys.exit(1)

try:
    print("\n2. Downloading Piper voice model...")
    print("   (First run will download ~60MB - may take a minute)")
    
    import subprocess
    import urllib.request
    
    # Download model files
    model_base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
    model_files = [
        ("en_US-lessac-medium.onnx", f"{model_base}/en_US-lessac-medium.onnx"),
        ("en_US-lessac-medium.onnx.json", f"{model_base}/en_US-lessac-medium.onnx.json")
    ]
    
    for filename, url in model_files:
        if not os.path.exists(filename):
            print(f"   Downloading {filename}...")
            urllib.request.urlretrieve(url, filename)
            print(f"   [OK] Downloaded {filename}")
        else:
            print(f"   [OK] {filename} already exists")
    
    from piper import PiperVoice
    
    print("\n3. Loading Piper voice model...")
    start_time = time.time()
    
    # Initialize Piper
    voice = PiperVoice.load("en_US-lessac-medium.onnx")
    
    load_time = time.time() - start_time
    print(f"   [OK] Piper model loaded in {load_time:.2f}s")
    
    print("\n4. Generating base speech with Piper...")
    start_time = time.time()
    
    # Generate speech
    temp_base_audio = "temp_piper_base.wav"
    with open(temp_base_audio, 'wb') as f:
        voice.synthesize(TEST_TEXT, f)
    
    gen_time = time.time() - start_time
    print(f"   [OK] Base audio generated in {gen_time:.2f}s")
    print(f"   [OK] Saved to: {temp_base_audio}")
    
except Exception as e:
    print(f"[ERROR] Piper TTS failed: {e}")
    print("\nFull error:")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Test RVC Voice Conversion
print("\n" + "=" * 70)
print("STEP 2: Testing RVC Voice Conversion")
print("=" * 70)

try:
    from rvc_python.infer import RVCInference
    print("[OK] RVC Python installed")
except ImportError:
    print("[ERROR] RVC Python not installed")
    print("\nSolution: Install with:")
    print("  pip install rvc-python")
    sys.exit(1)

try:
    print("\n5. Initializing RVC...")
    start_time = time.time()
    
    rvc = RVCInference(device="cpu")
    
    init_time = time.time() - start_time
    print(f"   [OK] RVC initialized in {init_time:.2f}s")
    
    print("\n6. Converting voice with reference audio...")
    print(f"   Reference: {REFERENCE_AUDIO}")
    start_time = time.time()
    
    # Perform voice conversion
    output_audio = rvc.infer_file(
        input_path=temp_base_audio,
        reference_path=REFERENCE_AUDIO,
        pitch_shift=0,
        index_rate=0.5,
        filter_radius=3,
        rms_mix_rate=0.25,
        protect_rate=0.33
    )
    
    convert_time = time.time() - start_time
    print(f"   [OK] Voice converted in {convert_time:.2f}s")
    
    # Save output
    import torchaudio
    torchaudio.save(OUTPUT_AUDIO, output_audio, 16000)
    print(f"   [OK] Saved to: {OUTPUT_AUDIO}")
    
    # Clean up temp file
    if os.path.exists(temp_base_audio):
        os.unlink(temp_base_audio)
    
except Exception as e:
    print(f"[ERROR] RVC conversion failed: {e}")
    print("\nFull error:")
    import traceback
    traceback.print_exc()
    
    # Clean up
    if os.path.exists(temp_base_audio):
        os.unlink(temp_base_audio)
    sys.exit(1)

# Summary
print("\n" + "=" * 70)
print("SUCCESS! PIPER + RVC PIPELINE WORKING!")
print("=" * 70)
print(f"\n📊 Performance Summary:")
print(f"   - Piper Load Time:     {load_time:.2f}s")
print(f"   - Speech Generation:   {gen_time:.2f}s")
print(f"   - RVC Initialization:  {init_time:.2f}s")
print(f"   - Voice Conversion:    {convert_time:.2f}s")
print(f"   - TOTAL TIME:          {load_time + gen_time + init_time + convert_time:.2f}s")
print(f"\n✅ Output saved: {OUTPUT_AUDIO}")
print(f"   Play it to hear your cloned voice!")
print("\n" + "=" * 70)

