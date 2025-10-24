#!/usr/bin/env python
"""
Test script for Ditto Online Streaming API
This script demonstrates how to call the API and receive streaming events
"""
import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/ditto-online/generate"
STATUS_ENDPOINT = f"{BASE_URL}/api/ditto-online/status"

# Test data
TEST_REQUEST = {
    "text": "Hello! This is a test of Ditto's online streaming mode. It should generate video in real-time chunks as the audio is processed.",
    "emotion": 4,  # Neutral
    "gaze": True,
    "chunk_duration": 3.0
    # reference_image and reference_audio will use defaults
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
        print(f"   Chunk Duration: {data.get('chunk_duration')}s")
        print(f"   Message: {data['message']}\n")
        return True
    except Exception as e:
        print(f"❌ Status check failed: {e}\n")
        return False

def test_streaming_generation():
    """Test the streaming generation endpoint"""
    print("=" * 70)
    print("2️⃣  Testing Streaming Generation")
    print("=" * 70)
    print(f"Request: {json.dumps(TEST_REQUEST, indent=2)}\n")
    
    try:
        # Make streaming request
        response = requests.post(
            API_ENDPOINT,
            json=TEST_REQUEST,
            stream=True,  # Important: enable streaming
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
        )
        response.raise_for_status()
        
        print("📡 Streaming events:\n")
        event_count = 0
        
        # Process server-sent events
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                
                # SSE format: "data: {...}"
                if line.startswith('data: '):
                    event_data = line[6:]  # Remove "data: " prefix
                    
                    try:
                        event = json.loads(event_data)
                        event_count += 1
                        
                        event_type = event.get('type', 'unknown')
                        
                        # Pretty print based on event type
                        if event_type == 'started':
                            print(f"🚀 [{event_count}] STARTED: {event.get('message')}")
                        
                        elif event_type == 'audio_ready':
                            print(f"🎙️  [{event_count}] AUDIO READY")
                            print(f"    Path: {event.get('audio_path')}")
                        
                        elif event_type == 'setup':
                            print(f"⚙️  [{event_count}] SETUP: {event.get('message')}")
                        
                        elif event_type == 'setup_complete':
                            print(f"✅ [{event_count}] SETUP COMPLETE")
                            print(f"    Audio Duration: {event.get('audio_duration'):.2f}s")
                            print(f"    Expected Chunks: {event.get('expected_chunks')}")
                        
                        elif event_type == 'streaming':
                            print(f"📹 [{event_count}] STREAMING: {event.get('message')}")
                        
                        elif event_type == 'chunk':
                            print(f"🎬 [{event_count}] CHUNK {event.get('chunk_id')}")
                            print(f"    Duration: {event.get('duration'):.2f}s")
                            print(f"    Frames: {event.get('start_frame')} -> {event.get('end_frame')}")
                            print(f"    Path: {event.get('chunk_path')}")
                        
                        elif event_type == 'final_video':
                            print(f"🎥 [{event_count}] FINAL VIDEO")
                            print(f"    Path: {event.get('video_path')}")
                        
                        elif event_type == 'complete':
                            print(f"\n✅ [{event_count}] COMPLETE!")
                            print(f"    Total Chunks: {event.get('total_chunks')}")
                            print(f"    Total Time: {event.get('total_time'):.2f}s")
                            print(f"    Message: {event.get('message')}")
                        
                        elif event_type == 'error':
                            print(f"\n❌ [{event_count}] ERROR: {event.get('message')}")
                        
                        else:
                            print(f"📨 [{event_count}] {event_type.upper()}: {event}")
                    
                    except json.JSONDecodeError:
                        print(f"⚠️  Could not parse event: {event_data}")
        
        print(f"\n✅ Streaming completed ({event_count} events received)")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🧪 DITTO ONLINE STREAMING API TEST")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}\n")
    
    # Test 1: Check status
    status_ok = test_status()
    if not status_ok:
        print("⚠️  Status check failed. Is the backend running?")
        print(f"   Try: cd backend && uvicorn main:app --reload --port 8000\n")
        return False
    
    # Test 2: Test streaming generation
    streaming_ok = test_streaming_generation()
    
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

