#!/usr/bin/env python
"""
Test Ditto Pipelined Streaming
================================
Tests the new pipelined streaming that achieves <8s first video by:
1. Streaming audio in chunks (5-10s each)
2. Generating video for each chunk immediately
3. No waiting for full audio generation
"""

import requests
import json
import time
from datetime import datetime

def test_pipelined_streaming():
    """Test pipelined streaming endpoint"""
    
    url = "http://localhost:8000/api/ditto-pipelined/generate"
    
    # Test with long text (should take 30+ seconds if generated as full audio)
    # But with pipelined streaming, first video should arrive in <8 seconds!
    payload = {
        "text": """
        India and Pakistan are two neighboring countries in South Asia with a complex shared history. 
        They were part of British India until 1947, when they gained independence and were partitioned 
        into two separate nations. This partition led to significant political and social upheaval, 
        including the displacement of millions of people and ongoing tensions. Both countries have 
        diverse cultures, languages, and religions, with India being predominantly Hindu and Pakistan 
        being predominantly Muslim. The relationship between these two nations continues to be one of 
        the most important and challenging geopolitical dynamics in the region.
        """,
        "chunk_duration": 5.0  # 5-second audio chunks
    }
    
    print("=" * 80)
    print("🚀 TESTING PIPELINED STREAMING")
    print("=" * 80)
    print(f"Text length: {len(payload['text'])} characters")
    print(f"Chunk duration: {payload['chunk_duration']} seconds")
    print(f"Expected: First video within 8 seconds!")
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
        audio_times = []
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
                        print(f"[{timestamp}] 🎬 {data.get('message')}")
                        print(f"             Chunk duration: {data.get('chunk_duration')}s")
                        print()
                    
                    elif event_type == 'audio_chunk':
                        chunk_id = data.get('chunk_id')
                        text_snippet = data.get('text', '')[:50]
                        audio_time = data.get('audio_time', 0)
                        audio_times.append(audio_time)
                        
                        print(f"[{timestamp}] 🎙️  Audio Chunk {chunk_id}")
                        print(f"             Text: \"{text_snippet}...\"")
                        print(f"             Time: {audio_time:.2f}s")
                        print(f"             Elapsed: {elapsed:.2f}s")
                        print()
                    
                    elif event_type == 'video_chunk':
                        chunk_id = data.get('chunk_id')
                        video_path = data.get('video_path', '')
                        video_time = data.get('video_time', 0)
                        duration = data.get('duration', 0)
                        first_video = data.get('first_video_time')
                        
                        video_times.append(video_time)
                        chunks_received += 1
                        
                        if first_video_time is None:
                            first_video_time = first_video
                        
                        print(f"[{timestamp}] 🎬 VIDEO CHUNK {chunk_id} READY!")
                        print(f"             Path: {video_path}")
                        print(f"             Duration: {duration:.2f}s")
                        print(f"             Video gen time: {video_time:.2f}s")
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
                        print(f"Total time: {total_time:.2f}s")
                        print(f"First video: {first_video_time:.2f}s")
                        print(f"Avg per chunk: {avg_time:.2f}s")
                        
                        if audio_times:
                            print(f"Avg audio time: {sum(audio_times) / len(audio_times):.2f}s")
                        if video_times:
                            print(f"Avg video time: {sum(video_times) / len(video_times):.2f}s")
                        
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
                    print(f"[WARNING] Could not parse line: {line}")
        
        print(f"\n✅ Stream complete!")
        
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after 300 seconds")
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except KeyboardInterrupt:
        print(f"\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pipelined_streaming()

