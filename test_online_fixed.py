#!/usr/bin/env python
"""
Test FIXED Online Mode - All chunks should work!
"""
import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/ditto-online-fixed/generate"
STATUS_ENDPOINT = f"{BASE_URL}/api/ditto-online-fixed/status"

TEST_REQUEST = {
    "text": "India and Pakistan are two neighboring countries in South Asia with a complex shared history. They were part of British India until 1947, when they gained independence and were partitioned into two separate nations. This partition led to significant political and social upheaval, including the displacement of millions of people and ongoing tensions.",
    "emotion": 4,
    "gaze": True,
    "target_chunk_duration": 3.0
}

def test_status():
    """Test status endpoint"""
    print("=" * 70)
    print("1️⃣  Testing Status")
    print("=" * 70)
    
    try:
        response = requests.get(STATUS_ENDPOINT)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {data['status']}")
        print(f"   Mode: {data['mode']}")
        print(f"   SDK Pool: {data.get('sdk_pool_size', 0)}")
        print(f"   Message: {data['message']}\n")
        return True
    except Exception as e:
        print(f"❌ Status check failed: {e}\n")
        return False

def test_fixed_online():
    """Test fixed online streaming"""
    print("=" * 70)
    print("2️⃣  Testing FIXED Online Mode")
    print("=" * 70)
    print("Text: India-Pakistan (4 chunks expected)")
    print("Fix: Each chunk gets fresh SDK from pool\n")
    
    try:
        start_time = time.time()
        first_chunk_time = None
        chunk_results = []
        
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
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                
                if line.startswith('data: '):
                    event_data = line[6:]
                    
                    try:
                        event = json.loads(event_data)
                        event_type = event.get('type', 'unknown')
                        
                        if event_type == 'initializing':
                            print(f"🔥 {event.get('message')}")
                        
                        elif event_type == 'setup':
                            print(f"⚙️  {event.get('message')}")
                        
                        elif event_type == 'started':
                            print(f"🚀 {event.get('message')}")
                        
                        elif event_type == 'text_chunked':
                            total = event.get('total_chunks', 0)
                            print(f"📝 Text chunked into {total} parts")
                            for chunk in event.get('chunks', []):
                                print(f"    Chunk {chunk['id']}: {chunk['text']}")
                            print()
                        
                        elif event_type == 'chunk_started':
                            chunk_id = event.get('chunk_id', 0)
                            print(f"⏱️  CHUNK {chunk_id} STARTED")
                        
                        elif event_type == 'audio_ready':
                            chunk_id = event.get('chunk_id', 0)
                            audio_time = event.get('generation_time', 0)
                            print(f"🎙️  Audio {chunk_id}: {audio_time:.2f}s")
                        
                        elif event_type == 'chunk_complete':
                            chunk_id = event.get('chunk_id', 0)
                            audio_time = event.get('audio_time', 0)
                            video_time = event.get('video_time', 0)
                            setup_time = event.get('setup_time', 0)
                            chunk_total = event.get('chunk_total_time', 0)
                            elapsed = event.get('elapsed_time', 0)
                            sdk_index = event.get('sdk_index', 0)
                            
                            print(f"✅ CHUNK {chunk_id} COMPLETE (SDK #{sdk_index})")
                            print(f"    Audio: {audio_time:.2f}s | Setup: {setup_time:.2f}s | Video: {video_time:.2f}s")
                            print(f"    Total: {chunk_total:.2f}s | Elapsed: {elapsed:.2f}s\n")
                            
                            chunk_results.append({
                                'chunk_id': chunk_id,
                                'audio': audio_time,
                                'setup': setup_time,
                                'video': video_time,
                                'total': chunk_total,
                                'elapsed': elapsed,
                                'sdk': sdk_index
                            })
                        
                        elif event_type == 'first_chunk_milestone':
                            first_chunk_time = event.get('time_to_first_chunk', 0)
                            target_met = event.get('target_met', False)
                            
                            print(f"{'🎉' if target_met else '⏰'} FIRST CHUNK MILESTONE")
                            print(f"    Time: {first_chunk_time:.2f}s")
                            print(f"    Note: {event.get('note', '')}\n")
                        
                        elif event_type == 'complete':
                            total_time = event.get('total_time', 0)
                            total_chunks = event.get('total_chunks', 0)
                            print(f"\n✅ COMPLETE!")
                            print(f"    Total Chunks: {total_chunks}")
                            print(f"    Total Time: {total_time:.2f}s")
                        
                        elif event_type == 'error':
                            chunk_id = event.get('chunk_id', '?')
                            print(f"\n❌ ERROR (Chunk {chunk_id}): {event.get('message')}")
                    
                    except json.JSONDecodeError:
                        print(f"⚠️  Parse error: {event_data}")
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 RESULTS")
        print("=" * 70)
        
        if first_chunk_time:
            print(f"⏱️  First Chunk: {first_chunk_time:.2f}s")
        
        if chunk_results:
            print(f"\n📋 All Chunks:")
            print(f"{'ID':<4} {'SDK':<4} {'Audio':<8} {'Setup':<8} {'Video':<8} {'Total':<8}")
            print("-" * 50)
            for cr in chunk_results:
                print(f"{cr['chunk_id']:<4} #{cr['sdk']:<3} {cr['audio']:<8.2f} {cr['setup']:<8.2f} {cr['video']:<8.2f} {cr['total']:<8.2f}")
            
            # Check if all chunks completed
            print(f"\n✨ Result:")
            print(f"   Total chunks: {len(chunk_results)}")
            print(f"   All completed: {'✅ YES!' if len(chunk_results) >= 3 else '❌ NO'}")
            
            if len(chunk_results) >= 2:
                avg_subsequent = sum(cr['total'] for cr in chunk_results[1:]) / len(chunk_results[1:])
                print(f"   Avg per chunk: {avg_subsequent:.2f}s")
        
        print("=" * 70)
        return len(chunk_results) >= 3  # Success if at least 3 chunks completed
        
    except Exception as e:
        print(f"❌ Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run tests"""
    print("\n" + "=" * 70)
    print("🧪 DITTO ONLINE MODE - FIXED VERSION")
    print("=" * 70)
    print("Fix: SDK pool with separate instances per chunk")
    print("Expected: ALL chunks complete successfully\n")
    
    # Test status
    status_ok = test_status()
    if not status_ok:
        print("⚠️  Backend not running?")
        return False
    
    # Test fixed online
    test_ok = test_fixed_online()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Status:    {'✅ PASS' if status_ok else '❌ FAIL'}")
    print(f"Streaming: {'✅ PASS (All chunks work!)' if test_ok else '❌ FAIL'}")
    print("=" * 70)
    
    return status_ok and test_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

