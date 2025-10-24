"""
Test Parallel Pipeline End-to-End
Tests: LLM → Voice Cloner → Avatar Generation (all parallel with queues)
Question: "What are the differences between India and Pakistan?"
Target: First video <5 seconds
"""

import asyncio
import aiohttp
import json
import logging
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


async def test_parallel_pipeline():
    """Test the complete parallel pipeline"""
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}🎬 PARALLEL PIPELINE TEST{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    # Configuration
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/parallel-pipeline/generate"
    
    # Test question
    question = "What are the differences between India and Pakistan?"
    
    payload = {
        "question": question,
        "emotion": 4,  # Neutral
        "gaze": True,
        "pose": {}
    }
    
    print(f"{Colors.CYAN}📝 Question:{Colors.ENDC} {question}")
    print(f"{Colors.CYAN}🎯 Target:{Colors.ENDC} First video <5 seconds")
    print(f"{Colors.CYAN}📡 Endpoint:{Colors.ENDC} {endpoint}\n")
    
    # Track metrics
    start_time = time.time()
    first_video_time = None
    video_count = 0
    text_chunks = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload) as response:
                if response.status != 200:
                    logger.error(f"❌ Request failed: {response.status}")
                    text = await response.text()
                    logger.error(f"   Response: {text}")
                    return
                
                print(f"{Colors.GREEN}✅ Connection established{Colors.ENDC}")
                print(f"{Colors.YELLOW}⚡ Pipeline started...{Colors.ENDC}\n")
                
                print(f"{Colors.BOLD}{'─'*80}{Colors.ENDC}")
                print(f"{Colors.BOLD}Pipeline Progress:{Colors.ENDC}\n")
                
                # Process SSE stream
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('data: '):
                        data_str = line[6:]
                        
                        try:
                            data = json.loads(data_str)
                            
                            if data.get('event') == 'video_chunk':
                                video_count += 1
                                elapsed = time.time() - start_time
                                
                                if first_video_time is None:
                                    first_video_time = elapsed
                                    print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 FIRST VIDEO READY IN: {first_video_time:.2f}s{Colors.ENDC}\n")
                                
                                # Display video chunk info
                                print(f"{Colors.CYAN}📹 Video {video_count}:{Colors.ENDC}")
                                print(f"   Audio Chunk: {data['audio_chunk_idx']}")
                                print(f"   Text: {data['text'][:60]}...")
                                print(f"   Video URL: {data['video_url']}")
                                print(f"   Duration: {data['duration']:.2f}s")
                                print(f"   Generation: {data['generation_time']:.2f}s")
                                print(f"   Elapsed: {elapsed:.2f}s")
                                
                                # Check if <5s goal achieved
                                if first_video_time and first_video_time <= 5.0:
                                    if video_count == 1:
                                        print(f"   {Colors.GREEN}✅ <5s TARGET ACHIEVED!{Colors.ENDC}")
                                
                                print()
                                
                                # Track text
                                if data['text'] not in text_chunks:
                                    text_chunks.append(data['text'])
                            
                            elif data.get('event') == 'complete':
                                total_time = time.time() - start_time
                                
                                print(f"\n{Colors.BOLD}{'─'*80}{Colors.ENDC}")
                                print(f"{Colors.BOLD}{Colors.GREEN}✅ PIPELINE COMPLETE!{Colors.ENDC}")
                                print(f"{Colors.BOLD}{'─'*80}{Colors.ENDC}\n")
                                
                                print(f"{Colors.BOLD}📊 FINAL RESULTS:{Colors.ENDC}")
                                print(f"   Total Videos: {video_count}")
                                print(f"   Total Time: {total_time:.2f}s")
                                print(f"   First Video: {first_video_time:.2f}s")
                                
                                if first_video_time:
                                    if first_video_time <= 5.0:
                                        print(f"   {Colors.GREEN}{Colors.BOLD}✅ SUCCESS: First video <5s target achieved!{Colors.ENDC}")
                                    elif first_video_time <= 10.0:
                                        print(f"   {Colors.YELLOW}⚠️  GOOD: First video in {first_video_time:.2f}s (close to target){Colors.ENDC}")
                                    else:
                                        print(f"   {Colors.RED}⚠️  NEEDS OPTIMIZATION: First video in {first_video_time:.2f}s{Colors.ENDC}")
                                
                                print(f"\n{Colors.BOLD}📝 Response Summary:{Colors.ENDC}")
                                full_response = " ".join(text_chunks)
                                print(f"   Length: {len(full_response)} characters")
                                print(f"   Preview: {full_response[:200]}...")
                                
                                break
                            
                            elif data.get('event') == 'error':
                                print(f"\n{Colors.RED}❌ Error: {data['message']}{Colors.ENDC}")
                                break
                        
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️  Failed to parse data: {data_str}")
    
    except aiohttp.ClientConnectorError:
        print(f"\n{Colors.RED}❌ Cannot connect to {base_url}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Make sure the backend server is running:{Colors.ENDC}")
        print(f"   cd backend")
        print(f"   uvicorn main:app --reload --port 8000")
        return
    
    except Exception as e:
        print(f"\n{Colors.RED}❌ Test failed: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return
    
    # Final summary
    print(f"\n{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}TEST COMPLETE{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


async def test_status_endpoint():
    """Test the status endpoint"""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/parallel-pipeline/status"
    
    print(f"{Colors.CYAN}🔍 Checking pipeline status...{Colors.ENDC}\n")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"{Colors.GREEN}✅ Pipeline Status:{Colors.ENDC}")
                    print(f"   {json.dumps(data, indent=2)}\n")
                else:
                    print(f"{Colors.RED}❌ Status check failed: {response.status}{Colors.ENDC}\n")
    
    except Exception as e:
        print(f"{Colors.RED}❌ Cannot reach status endpoint: {e}{Colors.ENDC}\n")


async def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}PARALLEL PIPELINE END-TO-END TEST{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.ENDC}\n")
    
    print(f"{Colors.BOLD}Test Configuration:{Colors.ENDC}")
    print(f"   Question: What are the differences between India and Pakistan?")
    print(f"   Target: First video <5 seconds")
    print(f"   Pipeline: LLM → Voice → Avatar (parallel with queues)\n")
    
    # Test 1: Status
    await test_status_endpoint()
    
    # Test 2: Full pipeline
    await test_parallel_pipeline()
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}✅ All tests complete!{Colors.ENDC}\n")


if __name__ == "__main__":
    asyncio.run(main())

