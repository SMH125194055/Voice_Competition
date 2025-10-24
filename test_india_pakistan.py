#!/usr/bin/env python
"""
Test with real question: "What are the differences between India and Pakistan?"
This will generate multiple chunks and show the optimization in action
"""
import sys
import os
import time
import asyncio

# Add backend to path
sys.path.insert(0, '/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend')

from utils.fast_avatar_helper import FastAvatarHelper
from utils import text_to_speech, chat_with_llm_streaming, initialize_tts
from dotenv import load_dotenv

# Load environment
load_dotenv('/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/.env')

# Configuration
reference_image = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/Avatar/References/ref_1761131562372.jpg"
reference_audio = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/audio/reference_voices/ref_1761118578.wav"
output_dir = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/generated_videos/india_pakistan_test"

print("🌍 Testing: What are the differences between India and Pakistan?")
print("=" * 70)

async def main():
    # Initialize TTS
    print("\n📝 Step 1: Initialize TTS")
    initialize_tts("local", reference_audio)
    print("✅ TTS ready")
    
    # Initialize Avatar Helper (PRE-PROCESS REFERENCE IMAGE ONCE)
    print("\n📝 Step 2: Initialize Avatar Helper")
    print("   (This pre-processes the reference image ONE TIME)")
    avatar_helper = FastAvatarHelper(reference_image, emotion=4, gaze=True)
    avatar_helper.initialize()
    print("✅ Avatar helper ready!\n")
    
    # Stream LLM response
    question = "What are the differences between India and Pakistan?"
    print(f"📝 Question: {question}")
    print("=" * 70)
    
    total_start = time.time()
    first_chunk_time = None
    chunk_count = 0
    results = []
    
    text_buffer = ""
    min_chars = 80
    sentence_endings = ['.', '!', '?', '\n']
    
    print("\n🔄 Processing LLM response in real-time...\n")
    
    async for llm_chunk in chat_with_llm_streaming(question):
        text_buffer += llm_chunk
        
        # Check if we should process this chunk
        should_process = (
            len(text_buffer) >= min_chars and
            any(text_buffer.endswith(end) for end in sentence_endings)
        ) or len(text_buffer) > 200
        
        if should_process:
            text = text_buffer.strip()
            text_buffer = ""
            
            if not text:
                continue
            
            chunk_count += 1
            chunk_start = time.time()
            
            print(f"📝 Chunk {chunk_count}: {text[:50]}...")
            
            # Generate audio
            audio_start = time.time()
            audio_path = await text_to_speech(
                text=text,
                mode="local",
                reference_audio_path=reference_audio
            )
            audio_time = time.time() - audio_start
            
            if not audio_path:
                print(f"   ❌ Audio generation failed")
                continue
            
            print(f"   🎙️  Audio: {audio_time:.2f}s")
            
            # Generate video (OPTIMIZED!)
            video_start = time.time()
            video_path = avatar_helper.generate_video(audio_path, output_dir)
            video_time = time.time() - video_start
            print(f"   🎬 Video: {video_time:.2f}s")
            
            chunk_total = time.time() - chunk_start
            elapsed = time.time() - total_start
            
            if first_chunk_time is None:
                first_chunk_time = elapsed
                print(f"\n   🎉 FIRST COMPLETE CHUNK IN: {elapsed:.2f}s")
                print("   " + "=" * 60)
            
            print(f"   ✅ Total for chunk {chunk_count}: {chunk_total:.2f}s (elapsed: {elapsed:.2f}s)\n")
            
            results.append({
                'chunk': chunk_count,
                'audio': audio_time,
                'video': video_time,
                'total': chunk_total,
                'text': text[:50] + "..."
            })
            
            # Cleanup audio
            if os.path.exists(audio_path):
                os.unlink(audio_path)
    
    # Process remaining text
    if text_buffer.strip():
        text = text_buffer.strip()
        chunk_count += 1
        chunk_start = time.time()
        
        print(f"📝 Chunk {chunk_count} (final): {text[:50]}...")
        
        audio_start = time.time()
        audio_path = await text_to_speech(text=text, mode="local", reference_audio_path=reference_audio)
        audio_time = time.time() - audio_start
        
        if audio_path:
            print(f"   🎙️  Audio: {audio_time:.2f}s")
            
            video_start = time.time()
            video_path = avatar_helper.generate_video(audio_path, output_dir)
            video_time = time.time() - video_start
            print(f"   🎬 Video: {video_time:.2f}s")
            
            chunk_total = time.time() - chunk_start
            elapsed = time.time() - total_start
            
            print(f"   ✅ Total for chunk {chunk_count}: {chunk_total:.2f}s (elapsed: {elapsed:.2f}s)\n")
            
            results.append({
                'chunk': chunk_count,
                'audio': audio_time,
                'video': video_time,
                'total': chunk_total,
                'text': text[:50] + "..."
            })
            
            if os.path.exists(audio_path):
                os.unlink(audio_path)
    
    # Cleanup
    avatar_helper.cleanup()
    
    total_time = time.time() - total_start
    
    # Print results
    print("\n" + "=" * 70)
    print("📊 FINAL RESULTS")
    print("=" * 70)
    print(f"Question: {question}")
    print(f"Total chunks: {chunk_count}")
    print(f"Total time: {total_time:.2f}s")
    print(f"First chunk: {first_chunk_time:.2f}s")
    print(f"Average per chunk: {total_time/chunk_count:.2f}s")
    
    print("\n📊 Per-Chunk Breakdown:")
    print("-" * 70)
    print(f"{'#':<4} {'Audio':<8} {'Video':<8} {'Total':<8} {'Text':<40}")
    print("-" * 70)
    for r in results:
        print(f"{r['chunk']:<4} {r['audio']:<8.2f} {r['video']:<8.2f} {r['total']:<8.2f} {r['text']:<40}")
    
    # Calculate improvement
    first_video = results[0]['video'] if results else 0
    avg_subsequent = sum(r['video'] for r in results[1:]) / len(results[1:]) if len(results) > 1 else 0
    
    print("\n" + "=" * 70)
    print("✨ OPTIMIZATION RESULTS")
    print("=" * 70)
    print(f"First video generation: {first_video:.2f}s (includes reference setup)")
    if len(results) > 1:
        print(f"Subsequent videos: {avg_subsequent:.2f}s average (reuses reference!)")
        print(f"\n🚀 Speed improvement: {((first_video - avg_subsequent) / first_video * 100):.0f}% faster after first chunk!")
    
    print(f"\n💾 Generated videos saved to:")
    print(f"   {output_dir}")
    
    # List generated videos
    if os.path.exists(output_dir):
        videos = [f for f in os.listdir(output_dir) if f.endswith('.mp4')]
        print(f"\n📹 {len(videos)} videos generated:")
        for video in videos[:5]:  # Show first 5
            print(f"   - {video}")
        if len(videos) > 5:
            print(f"   ... and {len(videos)-5} more")

if __name__ == "__main__":
    asyncio.run(main())

