"""Test XTTS loading to see the actual error."""
import os
import sys

# Add path
backend_path = os.path.dirname(__file__)
sys.path.insert(0, backend_path)

print("=" * 60)
print("Testing XTTS Model Loading")
print("=" * 60)

try:
    print("\n1. Testing TTS import...")
    from TTS.api import TTS
    print("   [OK] TTS library imported successfully")
    
    print("\n2. Loading XTTS model...")
    print("   (This will download the model on first run - may take a few minutes)")
    model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cpu")
    print("   [OK] XTTS model loaded successfully!")
    
    print("\n3. Testing voice generation...")
    test_text = "Hello, this is a test of Coqui XTTS."
    wav = model.tts(text=test_text, language="en")
    print(f"   [OK] Generated audio with {len(wav)} samples")
    
    print("\n" + "=" * 60)
    print("SUCCESS! XTTS is working properly!")
    print("=" * 60)
    
except ImportError as e:
    print(f"\n[ERROR] Import Error: {e}")
    print("\nSolution: Install TTS library")
    print("  pip install TTS")
    
except Exception as e:
    print(f"\n[ERROR] Error: {type(e).__name__}")
    print(f"  Message: {e}")
    print(f"\nFull error details:")
    import traceback
    traceback.print_exc()

