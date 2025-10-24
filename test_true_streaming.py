#!/usr/bin/env python
"""
Test TRUE STREAMING: Text → Audio Chunks → Video Chunks
Target: First chunk within 5 seconds!
"""
import requests
import json
import sys
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/ditto-streaming/generate"
STATUS_ENDPOINT = f"{BASE_URL}/api/ditto-streaming/status"

# Test data
TEST_REQUEST = {
    "text": "India and Pakistan are two neighboring countries in South Asia with a complex shared history. They were part of British India until 1947, when they gained independence and were partitioned into two separate nations. This partition led to significant political and social upheaval, including the displacement of millions of people and ongoing tensions.",
    "emotion": 4,
    "gaze": True,
    "target_chunk_duration": 3.0
}

def test_status():
    """Test the status endpoint"""
    print("=" * 70)
    print("1️⃣  Testing Status Endpoint")
    print("=" * 70)
    
    try:
        response = requests.get(STATUS_ENDPOINT)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {data['status']}")
        print(f"   Mode: {data['mode']}")
        print(f"   Pool Size: {data.get('pool_size', 'N/A')}")
        print(f"   Message: {data['message']}\n")
        return True
    except Exception as e:
        print(f"❌ Status check failed: {e}\n")
        return False

def test_true_streaming():
    """Test the true streaming generation"""
    print("=" * 70)
    print("2️⃣  Testing TRUE STREAMING (Text → Audio → Video)")
    print("=" * 70)
    print(f"Text: {TEST_REQUEST['text'][:80]}...")
    print(f"Target: First chunk within 5 seconds!\n")
    
    try:
        start_time = time.time()
        first_chunk_time = None
        chunk_times = []
        total_chunks = 0
        
        # Make streaming request
        response = requests.post(
            API_ENDPOINT,
            json=TEST_REQUEST,
            stream=True,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
        )
        response.raise_for_status()
        
        print("📡 Streaming events:\n")
        
        # Process events
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                
                if line.startswith('data: '):
                    event_data = line[6:]
                    
                    try:
                        event = json.loads(event_data)
                        event_type = event.get('type', 'unknown')
                        
                        if event_type == 'initializing':
                            print(f"🔥 INITIALIZING: {event.get('message')}")
                        
                        elif event_type == 'started':
                            print(f"🚀 STARTED: {event.get('message')}")
                        
                        elif event_type == 'text_chunked':
                            total_chunks = event.get('total_chunks', 0)
                            print(f"📝 TEXT CHUNKED into {total_chunks} parts")
                            for chunk in event.get('chunks', []):
                                print(f"    Chunk {chunk['id']}: {chunk['text']}")
                            print()
                        
                        elif event_type == 'chunk_started':
                            chunk_id = event.get('chunk_id', 0)
                            print(f"⏱️  CHUNK {chunk_id} STARTED")
                            print(f"    Text: {event.get('text', '')[:60]}...")
                        
                        elif event_type == 'audio_ready':
                            chunk_id = event.get('chunk_id', 0)
                            audio_time = event.get('generation_time', 0)
                            print(f"🎙️  AUDIO {chunk_id} ready in {audio_time:.2f}s")
                        
                        elif event_type == 'chunk_complete':
                            chunk_id = event.get('chunk_id', 0)
                            audio_time = event.get('audio_time', 0)
                            video_time = event.get('video_time', 0)
                            chunk_total = event.get('chunk_total_time', 0)
                            elapsed = event.get('elapsed_time', 0)
                            
                            print(f"✅ CHUNK {chunk_id} COMPLETE")
                            print(f"    Audio: {audio_time:.2f}s | Video: {video_time:.2f}s | Total: {chunk_total:.2f}s")
                            print(f"    Elapsed: {elapsed:.2f}s")
                            print(f"    Video: {event.get('video_path', '')}")
                            
                            chunk_times.append({
                                'chunk_id': chunk_id,
                                'audio': audio_time,
                                'video': video_time,
                                'total': chunk_total,
                                'elapsed': elapsed
                            })
                        
                        elif event_type == 'first_chunk_milestone':
                            first_chunk_time = event.get('time_to_first_chunk', 0)
                            target_met = event.get('target_met', False)
                            
                            print(f"\n{'🎉' if target_met else '⚠️ '} FIRST CHUNK MILESTONE")
                            print(f"    Time: {first_chunk_time:.2f}s")
                            print(f"    Target (<5s): {'✅ MET!' if target_met else '❌ NOT MET'}")
                            print()
                        
                        elif event_type == 'complete':
                            total_time = event.get('total_time', 0)
                            print(f"\n✅ COMPLETE!")
                            print(f"    Total Chunks: {event.get('total_chunks', 0)}")
                            print(f"    Total Time: {total_time:.2f}s")
                            print(f"    Output Dir: {event.get('output_dir', '')}")
                        
                        elif event_type == 'error':
                            print(f"\n❌ ERROR: {event.get('message', 'Unknown error')}")
                    
                    except json.JSONDecodeError:
                        print(f"⚠️  Could not parse: {event_data}")
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 70)
        
        if first_chunk_time:
            print(f"🎯 First Chunk: {first_chunk_time:.2f}s {'✅' if first_chunk_time <= 5.0 else '❌'} (target: <5s)")
        
        if chunk_times:
            print(f"\n📋 Chunk Breakdown:")
            print(f"{'ID':<4} {'Audio':<8} {'Video':<8} {'Total':<8} {'Elapsed':<10}")
            print("-" * 45)
            for ct in chunk_times:
                print(f"{ct['chunk_id']:<4} {ct['audio']:<8.2f} {ct['video']:<8.2f} {ct['total']:<8.2f} {ct['elapsed']:<10.2f}")
            
            # Calculate averages (excluding first chunk which has setup)
            if len(chunk_times) > 1:
                avg_subsequent = sum(ct['total'] for ct in chunk_times[1:]) / len(chunk_times[1:])
                print(f"\n⚡ Avg subsequent chunks: {avg_subsequent:.2f}s")
        
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"❌ Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 DITTO TRUE STREAMING API TEST")
    print("=" * 70)
    print(f"Target: First chunk within 5 seconds!\n")
    
    # Test 1: Check status
    status_ok = test_status()
    if not status_ok:
        print("⚠️  Status check failed. Is the backend running?")
        return False
    
    # Test 2: Test true streaming
    streaming_ok = test_true_streaming()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Status Endpoint:    {'✅ PASS' if status_ok else '❌ FAIL'}")
    print(f"Streaming Endpoint: {'✅ PASS' if streaming_ok else '❌ FAIL'}")
    print("=" * 70)
    
    return status_ok and streaming_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

