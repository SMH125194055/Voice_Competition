#!/usr/bin/env python
"""
Test Ditto Cascade Streaming
==============================
Tests the cascade approach: multiple overlapping calls to existing endpoint
Goal: <8s first video, NO GAPS between chunks
"""

import requests
import json
import time
from datetime import datetime

def test_cascade_streaming(overlap=True):
    """Test cascade streaming endpoint"""
    
    url = "http://localhost:8000/api/ditto-cascade/generate"
    
    # Short test text (should generate 2-3 chunks)
    payload = {
        "text": """
        India and Pakistan are two neighboring countries in South Asia with a complex shared history. 
        They were part of British India until 1947, when they gained independence and were partitioned 
        into two separate nations.
        """,
        "chunk_duration": 5.0,  # 5-second chunks
        "overlap": overlap  # TRUE = all chunks start immediately!
    }
    
    print("=" * 80)
    print(f"🚀 TESTING CASCADE STREAMING (overlap={overlap})")
    print("=" * 80)
    print(f"Text length: {len(payload['text'])} characters")
    print(f"Chunk duration: {payload['chunk_duration']} seconds")
    print(f"Overlap mode: {'✅ YES - All chunks start immediately!' if overlap else '❌ NO - Sequential'}")
    print(f"**TARGET: First video within 8 seconds!**")
    print("=" * 80)
    print()
    
    try:
        # Send request
        print(f"🔗 Connecting to {url}")
        start_time = time.time()
        
        response = requests.post(url, json=payload, stream=True, timeout=300)
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return
        
        print(f"✅ Connected! Streaming started...")
        print("=" * 80)
        print()
        
        # Track metrics
        first_video_time = None
        chunks_received = 0
        video_times = []
        
        # Read streaming response
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    elapsed = time.time() - start_time
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    
                    event_type = data.get('type')
                    
                    if event_type == 'started':
                        total_chunks = data.get('total_chunks')
                        overlap_enabled = data.get('overlap_enabled')
                        
                        print(f"[{timestamp}] 🎬 {data.get('message')}")
                        print(f"             Total chunks: {total_chunks}")
                        print(f"             Overlap: {'✅ YES' if overlap_enabled else '❌ NO'}")
                        print()
                    
                    elif event_type == 'video_chunk':
                        chunk_id = data.get('chunk_id')
                        text_snippet = data.get('text', '')
                        video_path = data.get('video_path', '')
                        duration = data.get('duration', 0)
                        gen_time = data.get('generation_time', 0)
                        first_video = data.get('first_video_time')
                        
                        video_times.append(gen_time)
                        chunks_received += 1
                        
                        if first_video_time is None:
                            first_video_time = first_video
                        
                        print(f"[{timestamp}] 🎬 VIDEO CHUNK {chunk_id} READY!")
                        print(f"             Text: \"{text_snippet}\"")
                        print(f"             Path: {video_path}")
                        print(f"             Duration: {duration:.2f}s")
                        print(f"             Generation time: {gen_time:.2f}s")
                        print(f"             Total elapsed: {elapsed:.2f}s")
                        
                        if chunk_id == 0:
                            print(f"             🎉 FIRST VIDEO TIME: {first_video:.2f}s")
                        
                        print()
                    
                    elif event_type == 'complete':
                        total_chunks = data.get('total_chunks', 0)
                        total_time = data.get('total_time', 0)
                        avg_time = data.get('avg_time_per_chunk', 0)
                        
                        print("=" * 80)
                        print(f"[{timestamp}] ✅ {data.get('message')}")
                        print("=" * 80)
                        print()
                        print("📊 FINAL RESULTS")
                        print("-" * 80)
                        print(f"Total chunks: {total_chunks}")
                        print(f"Chunks received: {chunks_received}")
                        print(f"Total time: {total_time:.2f}s")
                        print(f"First video: {first_video_time:.2f}s")
                        print(f"Avg per chunk: {avg_time:.2f}s")
                        
                        if video_times:
                            print(f"Avg generation time: {sum(video_times) / len(video_times):.2f}s")
                        
                        print("-" * 80)
                        
                        # Goal assessment
                        print()
                        print("🎯 GOAL ASSESSMENT")
                        print("-" * 80)
                        if first_video_time and first_video_time <= 8.0:
                            print(f"✅ SUCCESS! First video in {first_video_time:.2f}s (<8s goal)")
                        elif first_video_time:
                            print(f"⚠️  CLOSE! First video in {first_video_time:.2f}s (goal: <8s)")
                            print(f"   Need to reduce by {first_video_time - 8.0:.2f}s")
                        else:
                            print("❌ No video received")
                        
                        print("=" * 80)
                    
                    elif event_type == 'error':
                        print(f"[{timestamp}] ❌ Error: {data.get('message')}")
                        if 'chunk_id' in data:
                            print(f"             Chunk: {data.get('chunk_id')}")
                        print()
                
                except json.JSONDecodeError:
                    pass
        
        print(f"\n✅ Stream complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "DITTO CASCADE STREAMING TEST" + " " * 30 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Test with overlap (parallel execution)
    test_cascade_streaming(overlap=True)

