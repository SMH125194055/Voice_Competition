"""
Test script for Edge-TTS (Microsoft's fast, free TTS).

Edge-TTS is:
- Extremely fast (2-3 seconds)
- High quality
- No voice cloning (but many built-in voices)
- Free and no API key needed
"""
import os
import sys
import time
import asyncio

# Add backend to path
backend_path = os.path.dirname(__file__)
sys.path.insert(0, backend_path)

print("=" * 70)
print("EDGE-TTS FAST SPEECH TEST")
print("=" * 70)

# Configuration
TEST_TEXT = "Hello! This is a test of Edge TTS for fast, high-quality speech generation."
OUTPUT_AUDIO = "test_edge_tts_output.mp3"

print(f"\n1. Configuration:")
print(f"   - Test Text: {TEST_TEXT}")
print(f"   - Output File: {OUTPUT_AUDIO}")

# Check if edge-tts is installed
try:
    import edge_tts
    print(f"   [OK] Edge-TTS installed (version: {edge_tts.__version__ if hasattr(edge_tts, '__version__') else 'unknown'})")
except ImportError:
    print("[ERROR] Edge-TTS not installed")
    print("\nSolution: Install with:")
    print("  pip install edge-tts")
    sys.exit(1)

# Test Edge-TTS
print("\n" + "=" * 70)
print("Testing Edge-TTS")
print("=" * 70)

async def test_edge_tts():
    """Test Edge-TTS generation."""
    
    print("\n2. Preparing voice...")
    print(f"   Using: en-US-GuyNeural (Male, US English)")
    
    print("\n3. Generating speech with Edge-TTS...")
    start_time = time.time()
    
    # Create TTS
    communicate = edge_tts.Communicate(TEST_TEXT, "en-US-GuyNeural")
    
    # Generate and save
    await communicate.save(OUTPUT_AUDIO)
    
    gen_time = time.time() - start_time
    print(f"   [OK] Speech generated in {gen_time:.2f}s")
    print(f"   [OK] Saved to: {OUTPUT_AUDIO}")
    
    # Get file size
    file_size = os.path.getsize(OUTPUT_AUDIO) / 1024  # KB
    print(f"   [OK] File size: {file_size:.2f} KB")
    
    return gen_time

# Run the test
try:
    print("\n" + "=" * 70)
    total_start = time.time()
    
    gen_time = asyncio.run(test_edge_tts())
    
    total_time = time.time() - total_start
    
    print("\n" + "=" * 70)
    print("SUCCESS! EDGE-TTS WORKING!")
    print("=" * 70)
    print(f"\n📊 Performance Summary:")
    print(f"   - Speech Generation:   {gen_time:.2f}s")
    print(f"   - TOTAL TIME:          {total_time:.2f}s")
    print(f"\n✅ Output saved: {OUTPUT_AUDIO}")
    print(f"   Play it to hear the generated speech!")
    print("\n💡 Edge-TTS Benefits:")
    print(f"   - Extremely fast (2-3 seconds)")
    print(f"   - High quality Microsoft voices")
    print(f"   - No API key needed")
    print(f"   - Free unlimited usage")
    print(f"\n⚠️  No voice cloning, but you can:")
    print(f"   - Choose from 100+ high-quality voices")
    print(f"   - Mix different voices for characters")
    print(f"   - Use for fast prototyping")
    print("\n" + "=" * 70)
    
except Exception as e:
    print(f"\n[ERROR] Edge-TTS failed: {e}")
    print("\nFull error:")
    import traceback
    traceback.print_exc()
    sys.exit(1)

