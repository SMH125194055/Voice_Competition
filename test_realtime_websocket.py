#!/usr/bin/env python
"""
Test Real-Time WebSocket Streaming
Tests the complete LLM → TTS → Avatar pipeline with streaming
"""
import asyncio
import websockets
import json
import time

async def test_realtime_streaming():
    uri = "ws://localhost:8000/api/realtime/stream"
    
    print("🔌 Connecting to real-time streaming WebSocket...")
    
    async with websockets.connect(uri) as websocket:
        print("✅ Connected!")
        
        # Send request
        request = {
            "type": "start",
            "question": "Tell me briefly about India",
            "reference_image": "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/Avatar/References/ref_1761131562372.jpg",
            "reference_audio": "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/audio/reference_voices/ref_1761118578.wav"
        }
        
        await websocket.send(json.dumps(request))
        print(f"📝 Sent question: {request['question']}")
        print("=" * 60)
        
        start_time = time.time()
        first_chunk_time = None
        video_chunk_count = 0
        audio_chunk_count = 0
        total_bytes = 0
        
        try:
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=120)
                
                # Check if it's JSON or binary
                if isinstance(message, bytes):
                    # Binary video data
                    video_chunk_count += 1
                    total_bytes += len(message)
                    
                    elapsed = time.time() - start_time
                    
                    if first_chunk_time is None:
                        first_chunk_time = elapsed
                        print(f"\n🎉 FIRST VIDEO CHUNK IN: {elapsed:.2f}s")
                        print("=" * 60)
                    
                    print(f"📹 Video chunk {video_chunk_count}: {len(message)/1024:.1f}KB (elapsed: {elapsed:.2f}s)")
                
                else:
                    # JSON status message
                    try:
                        data = json.loads(message)
                        event_type = data.get("type")
                        
                        if event_type == "started":
                            print(f"✅ Pipeline started")
                        
                        elif event_type == "text":
                            audio_chunk_count += 1
                            print(f"\n🎙️ Audio chunk {audio_chunk_count}: {data['text'][:50]}...")
                        
                        elif event_type == "video_chunk_meta":
                            # Metadata about the chunk (already logged above)
                            pass
                        
                        elif event_type == "complete":
                            total_time = time.time() - start_time
                            print("=" * 60)
                            print(f"✅ COMPLETE!")
                            print(f"   Audio chunks: {data['total_audio_chunks']}")
                            print(f"   Video chunks: {video_chunk_count}")
                            print(f"   Total video: {data['total_video_mb']:.2f}MB")
                            print(f"   Total time: {total_time:.2f}s")
                            if first_chunk_time:
                                print(f"   First chunk: {first_chunk_time:.2f}s")
                            break
                        
                        elif event_type == "error":
                            print(f"❌ Error: {data['message']}")
                            break
                    
                    except json.JSONDecodeError:
                        print(f"⚠️  Invalid JSON: {message}")
        
        except asyncio.TimeoutError:
            print("❌ Timeout waiting for response")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"First video chunk: {first_chunk_time:.2f}s" if first_chunk_time else "No chunks received")
    print(f"Total video chunks: {video_chunk_count}")
    print(f"Total video data: {total_bytes/1024/1024:.2f}MB")
    print(f"Total time: {time.time() - start_time:.2f}s")
    
    if first_chunk_time and first_chunk_time < 5.0:
        print(f"\n✅ SUCCESS! First chunk in {first_chunk_time:.2f}s (<5s goal achieved!)")
    elif first_chunk_time:
        print(f"\n⚠️  Close! First chunk in {first_chunk_time:.2f}s (goal: <5s, delta: +{first_chunk_time-5:.2f}s)")
    else:
        print("\n❌ FAILED: No video chunks received")

if __name__ == "__main__":
    print("🚀 Real-Time WebSocket Streaming Test")
    print("=" * 60)
    asyncio.run(test_realtime_streaming())

