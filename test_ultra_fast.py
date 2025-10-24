#!/usr/bin/env python
"""
Test Ultra-Fast Pipeline
Uses tiny chunks for fastest first video
"""
import asyncio
import websockets
import json
import time

async def test_ultra_fast():
    uri = "ws://localhost:8000/api/ultra-fast/stream"
    
    print("🚀 Testing Ultra-Fast Pipeline")
    print("=" * 60)
    
    async with websockets.connect(uri) as websocket:
        # Send request
        request = {
            "type": "start",
            "question": "What is India?",  # Very short question
            "reference_image": "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/Avatar/References/ref_1761131562372.jpg",
            "reference_audio": "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/audio/reference_voices/ref_1761118578.wav"
        }
        
        await websocket.send(json.dumps(request))
        print(f"📝 Question: {request['question']}")
        print("=" * 60)
        
        start_time = time.time()
        first_chunk_time = None
        chunk_count = 0
        
        while True:
            message = await websocket.recv()
            
            if isinstance(message, bytes):
                chunk_count += 1
                elapsed = time.time() - start_time
                
                if first_chunk_time is None:
                    first_chunk_time = elapsed
                    print(f"\n🎉 FIRST VIDEO CHUNK IN: {elapsed:.2f}s")
                    print("=" * 60)
                
                print(f"📹 Chunk {chunk_count}: {len(message)/1024:.1f}KB (elapsed: {elapsed:.2f}s)")
            else:
                data = json.loads(message)
                event_type = data.get("type")
                
                if event_type == "started":
                    print("✅ Pipeline started")
                
                elif event_type == "video_meta":
                    # Metadata already logged with binary
                    pass
                
                elif event_type == "complete":
                    print("=" * 60)
                    print(f"✅ Complete: {data['chunks']} chunks in {data['total_time']:.2f}s")
                    break
                
                elif event_type == "error":
                    print(f"❌ Error: {data['message']}")
                    break
        
        print("\n" + "=" * 60)
        print("📊 RESULT")
        print("=" * 60)
        if first_chunk_time:
            print(f"First chunk: {first_chunk_time:.2f}s")
            if first_chunk_time < 5.0:
                print(f"✅ SUCCESS! Goal achieved (<5s)!")
            else:
                print(f"⚠️  Close: +{first_chunk_time-5:.2f}s over goal")
        print(f"Total chunks: {chunk_count}")

if __name__ == "__main__":
    asyncio.run(test_ultra_fast())

