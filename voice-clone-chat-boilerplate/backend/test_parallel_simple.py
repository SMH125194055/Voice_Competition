#!/usr/bin/env python
"""Simple test for parallel pipeline using requests"""
import requests
import json
import time

def test_parallel_pipeline():
    url = "http://localhost:8000/api/parallel-pipeline/generate"
    
    payload = {
        "question": "What are the main differences between India and Pakistan?",
        "reference_image": "Avatar/References/ref_1761131562372.jpg",
        "reference_audio": "audio/reference_voices/ref_1761118578.wav"
    }
    
    print("🧪 Testing Parallel Pipeline")
    print(f"   Question: {payload['question']}")
    print(f"   Target: First video <5 seconds\n")
    
    start_time = time.time()
    first_video_time = None
    video_count = 0
    
    print("📡 Connecting to pipeline...")
    
    with requests.post(url, json=payload, stream=True, timeout=300) as response:
        print(f"✅ Connected (status: {response.status_code})\n")
        print("───────────────────────────────────────────────────────────")
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    event = data.get('event', 'unknown')
                    elapsed = time.time() - start_time
                    
                    if event == 'started':
                        print(f"[{elapsed:6.2f}s] 🚀 Pipeline started (session: {data.get('session_id')})")
                    
                    elif event == 'video_chunk':
                        video_count += 1
                        if first_video_time is None:
                            first_video_time = elapsed
                            print(f"[{elapsed:6.2f}s] 🎉 FIRST VIDEO READY!")
                        print(f"[{elapsed:6.2f}s] 📹 Video {video_count}: {data.get('video_url', 'N/A')}")
                        print(f"               Duration: {data.get('duration', 0):.2f}s, Gen Time: {data.get('generation_time', 0):.2f}s")
                    
                    elif event == 'complete':
                        total_time = elapsed
                        print(f"\n[{elapsed:6.2f}s] ✅ Pipeline Complete!")
                        break
                    
                    elif event == 'error':
                        print(f"\n[{elapsed:6.2f}s] ❌ Error: {data.get('message')}")
                        break
    
    print("───────────────────────────────────────────────────────────")
    print("\n📊 RESULTS:")
    print(f"   Total Videos: {video_count}")
    if first_video_time:
        print(f"   First Video: {first_video_time:.2f}s")
        if first_video_time < 5.0:
            print(f"   🎉 SUCCESS! Target <5s achieved!")
        elif first_video_time < 10.0:
            print(f"   ⚠️  GOOD: Close to target (<10s)")
        else:
            print(f"   ⚠️  Needs optimization (>{first_video_time:.0f}s)")
    else:
        print(f"   ❌ No videos generated")
    
    print(f"   Total Time: {time.time() - start_time:.2f}s\n")

if __name__ == "__main__":
    test_parallel_pipeline()

