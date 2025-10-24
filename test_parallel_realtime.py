import requests
import json
import time

url = "http://localhost:8000/api/parallel-pipeline/generate"
data = {
    "question": "what are the pros and cons of living in America",
    "reference_image": "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/Avatar/References/ref_1761131562372.jpg",
    "reference_audio": "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/audio/reference_voices/ref_1761118578.wav",
    "emotion": 4,
    "gaze": True
}

print("🚀 Starting parallel pipeline test...")
print(f"Question: {data['question']}")
print("-" * 60)

start_time = time.time()
first_video_time = None
video_count = 0
chunks_received = []

with requests.post(url, json=data, stream=True) as response:
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        exit(1)
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                try:
                    event = json.loads(data_str)
                    event_type = event.get('event')
                    
                    if event_type == 'started':
                        print(f"✅ Pipeline started (session: {event.get('session_id')})")
                    
                    elif event_type == 'video_chunk':
                        video_count += 1
                        elapsed = time.time() - start_time
                        
                        if first_video_time is None:
                            first_video_time = elapsed
                            print(f"\n🎉 FIRST VIDEO IN: {elapsed:.2f}s")
                            print("-" * 60)
                        
                        chunk_info = {
                            'chunk_idx': event.get('chunk_idx'),
                            'duration': event.get('duration'),
                            'gen_time': event.get('generation_time'),
                            'elapsed': elapsed
                        }
                        chunks_received.append(chunk_info)
                        
                        print(f"📹 Video {video_count}: chunk_{event.get('chunk_idx'):04d} | "
                              f"duration={event.get('duration'):.1f}s | "
                              f"gen_time={event.get('generation_time'):.2f}s | "
                              f"elapsed={elapsed:.2f}s")
                    
                    elif event_type == 'complete':
                        total_time = time.time() - start_time
                        print("-" * 60)
                        print(f"✅ COMPLETE!")
                        print(f"   Total videos: {video_count}")
                        print(f"   Total time: {total_time:.2f}s")
                        if first_video_time:
                            print(f"   First video: {first_video_time:.2f}s")
                        print(f"   Avg per video: {total_time/video_count:.2f}s")
                    
                    elif event_type == 'error':
                        print(f"❌ Error: {event.get('message')}")
                
                except json.JSONDecodeError:
                    pass

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
