"""
Test Streaming Avatar Endpoint
Tests the complete API endpoint for streaming video generation
"""

import asyncio
import aiohttp
import json
import logging
import time
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_streaming_endpoint():
    """Test streaming avatar API endpoint"""
    
    logger.info("="*80)
    logger.info("🎬 TESTING STREAMING AVATAR API ENDPOINT")
    logger.info("="*80)
    
    # Endpoint URL (adjust if your backend runs on different port)
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/avatar/generate-streaming"
    
    # Request payload
    payload = {
        "text": "This is a test of the streaming avatar generation system.",
        "emotion": 4,  # Neutral
        "gaze": True,
        "chunk_duration": 2.0
    }
    
    logger.info(f"\n📡 Connecting to: {endpoint}")
    logger.info(f"📝 Payload: {json.dumps(payload, indent=2)}\n")
    
    start_time = time.time()
    first_chunk_time = None
    chunk_count = 0
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload) as response:
                if response.status != 200:
                    logger.error(f"❌ Request failed: {response.status}")
                    text = await response.text()
                    logger.error(f"   Response: {text}")
                    return
                
                logger.info("✅ Connection established, streaming chunks...\n")
                
                # Process Server-Sent Events
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        
                        try:
                            data = json.loads(data_str)
                            
                            if data.get('event') == 'complete':
                                logger.info(f"\n✅ Streaming complete!")
                                logger.info(f"   Total chunks: {data['total_chunks']}")
                                logger.info(f"   Total time: {data['total_time']:.2f}s")
                                break
                            
                            elif data.get('event') == 'error':
                                logger.error(f"❌ Error: {data['message']}")
                                break
                            
                            elif 'chunk_idx' in data:
                                chunk_count += 1
                                elapsed = time.time() - start_time
                                
                                if first_chunk_time is None:
                                    first_chunk_time = elapsed
                                    logger.info(f"🎉 FIRST CHUNK READY IN: {first_chunk_time:.2f}s\n")
                                
                                logger.info(f"📦 Chunk {data['chunk_idx']}:")
                                logger.info(f"   Video URL: {data['video_url']}")
                                logger.info(f"   Duration: {data['duration']:.2f}s")
                                logger.info(f"   Generation: {data['generation_time']:.2f}s")
                                logger.info(f"   Elapsed: {elapsed:.2f}s")
                                logger.info(f"   Is last: {data['is_last']}\n")
                        
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️ Failed to parse data: {data_str}")
    
    except aiohttp.ClientConnectorError:
        logger.error(f"❌ Cannot connect to {base_url}")
        logger.error(f"   Make sure the backend server is running:")
        logger.error(f"   cd /home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend")
        logger.error(f"   uvicorn main:app --reload --port 8000")
        return
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    total_time = time.time() - start_time
    
    # Results
    logger.info(f"\n{'='*80}")
    logger.info("📊 TEST RESULTS")
    logger.info(f"{'='*80}")
    
    if first_chunk_time:
        logger.info(f"✅ First chunk latency: {first_chunk_time:.2f}s")
        
        if first_chunk_time <= 5.0:
            logger.info(f"🎉 SUCCESS: First chunk <5s target achieved!")
        else:
            logger.warning(f"⚠️ First chunk >5s, needs optimization")
    
    logger.info(f"✅ Total chunks received: {chunk_count}")
    logger.info(f"✅ Total time: {total_time:.2f}s")
    
    logger.info(f"\n📁 Generated videos should be at:")
    logger.info(f"   backend/generated_videos/streaming/")


async def test_status_endpoint():
    """Test the status endpoint"""
    logger.info("\n" + "="*80)
    logger.info("🔍 TESTING STATUS ENDPOINT")
    logger.info("="*80)
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/avatar/streaming-status"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"\n✅ Status: {json.dumps(data, indent=2)}")
                else:
                    logger.error(f"❌ Status request failed: {response.status}")
    
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")


async def main():
    """Run all tests"""
    logger.info("\n🚀 Starting API endpoint tests...\n")
    
    # Test 1: Status endpoint
    await test_status_endpoint()
    
    # Test 2: Streaming generation
    await test_streaming_endpoint()
    
    logger.info("\n✅ All API tests complete!")


if __name__ == "__main__":
    asyncio.run(main())

