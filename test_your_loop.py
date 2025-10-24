#!/usr/bin/env python
"""
Test script showing how to use FastAvatarHelper in YOUR existing loop
This is a drop-in replacement that makes avatar generation faster
"""
import sys
import os
import time

# Add backend to path
sys.path.insert(0, '/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend')

from utils.fast_avatar_helper import FastAvatarHelper
from utils import text_to_speech, initialize_tts

# Configuration
reference_image = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/Avatar/References/ref_1761131562372.jpg"
reference_audio = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/audio/reference_voices/ref_1761118578.wav"
output_dir = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/generated_videos/test_loop"

print("🔄 Simulating YOUR Loop-Based Pipeline")
print("=" * 60)

# YOUR LOOP WOULD LOOK LIKE THIS:

# 1. Initialize TTS (do this ONCE, outside loop)
initialize_tts("local", reference_audio)

# 2. Initialize FastAvatarHelper (do this ONCE, outside loop)
print("\n📝 Step 1: Initialize avatar helper (ONE TIME)")
avatar_helper = FastAvatarHelper(reference_image, emotion=4, gaze=True)
avatar_helper.initialize()
print("✅ Avatar helper ready!\n")

# 3. Simulate your loop with text chunks
text_chunks = [
    "India is a country in South Asia.",
    "It has a rich history.",
    "The population is over one billion.",
    "Many languages are spoken there."
]

total_start = time.time()
first_video_time = None
results = []

print("🔄 Starting loop...")
print("=" * 60)

for i, text in enumerate(text_chunks):
    chunk_start = time.time()
    
    print(f"\n📝 Chunk {i+1}: {text[:40]}...")
    
    # YOUR CODE: LLM generates text (simulated - you already have this)
    llm_time = 0.8  # You said 800ms
    print(f"   LLM: {llm_time:.2f}s (your existing code)")
    
    # YOUR CODE: Generate audio (you already have this)
    print(f"   🎙️  Generating audio...")
    audio_start = time.time()
    audio_path = text_to_speech(
        text=text,
        mode="local",
        reference_audio_path=reference_audio
    )
    import asyncio
    audio_path = asyncio.run(audio_path)
    audio_time = time.time() - audio_start
    print(f"   ✅ Audio: {audio_time:.2f}s")
    
    # NEW FAST CODE: Generate video (THIS IS THE OPTIMIZED PART!)
    print(f"   🎬 Generating video...")
    video_start = time.time()
    video_path = avatar_helper.generate_video(audio_path, output_dir)
    video_time = time.time() - video_start
    print(f"   ✅ Video: {video_time:.2f}s")
    
    # YOUR CODE: Send to frontend (you already have this)
    print(f"   📡 Sending to frontend...")
    
    chunk_total = time.time() - chunk_start
    
    if first_video_time is None:
        first_video_time = time.time() - total_start
        print(f"\n   🎉 FIRST VIDEO COMPLETE IN: {first_video_time:.2f}s")
    
    results.append({
        'chunk': i+1,
        'llm': llm_time,
        'audio': audio_time,
        'video': video_time,
        'total': chunk_total
    })
    
    # Cleanup
    if os.path.exists(audio_path):
        os.unlink(audio_path)

# 4. Cleanup (do this AFTER loop)
avatar_helper.cleanup()

total_time = time.time() - total_start

print("\n" + "=" * 60)
print("📊 RESULTS")
print("=" * 60)
print(f"Total time: {total_time:.2f}s for {len(text_chunks)} chunks")
print(f"First complete chunk: {first_video_time:.2f}s")
print(f"Average per chunk: {total_time/len(text_chunks):.2f}s")

print("\n📊 Per-Chunk Breakdown:")
print("-" * 60)
print(f"{'Chunk':<8} {'LLM':<8} {'Audio':<8} {'Video':<8} {'Total':<8}")
print("-" * 60)
for r in results:
    print(f"{r['chunk']:<8} {r['llm']:<8.2f} {r['audio']:<8.2f} {r['video']:<8.2f} {r['total']:<8.2f}")

print("\n" + "=" * 60)
print("✅ YOUR OPTIMIZED PIPELINE:")
print("=" * 60)
print(f"LLM: {results[0]['llm']:.2f}s (your existing code)")
print(f"Audio: {results[0]['audio']:.2f}s (your existing code)")
print(f"Video: {results[0]['video']:.2f}s (OPTIMIZED!)")
print(f"────────────")
print(f"Total first chunk: {results[0]['total']:.2f}s")
print(f"Subsequent chunks: {sum(r['total'] for r in results[1:])/len(results[1:]):.2f}s avg" if len(results) > 1 else "")

if results[0]['video'] < 10:
    print(f"\n✅ Video generation improved from 15-25s to {results[0]['video']:.2f}s!")
    print(f"   Savings: ~{20-results[0]['video']:.0f}s per chunk!")

