#!/usr/bin/env python
"""Simple test to verify the parallel pipeline is working"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

async def main():
    # Import here after loading .env
    from api.parallel_pipeline import ParallelPipelineOrchestrator
    import logging
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("Creating orchestrator...")
    orchestrator = ParallelPipelineOrchestrator()
    
    question = "What is 2+2?"
    reference_image = os.path.join(os.path.dirname(__file__), "Avatar/References/ref_1761131562372.jpg")
    reference_audio = os.path.join(os.path.dirname(__file__), "audio/reference_voices/ref_1761118578.wav")
    
    logger.info("Starting pipeline...")
    orchestrator.start(
        question=question,
        reference_image=reference_image,
        reference_audio=reference_audio,
        emotion=4,
        pose={},
        gaze=True
    )
    
    logger.info("Streaming results for 30 seconds...")
    count = 0
    timeout = asyncio.create_task(asyncio.sleep(30))
    
    async def stream_with_timeout():
        nonlocal count
        async for result in orchestrator.stream_results():
            logger.info(f"📦 Result {count}: {result.get('event', 'unknown')}")
            count += 1
            if count >= 10:
                break
    
    try:
        await asyncio.wait_for(stream_with_timeout(), timeout=30)
    except asyncio.TimeoutError:
        logger.info("Timeout reached")
    
    orchestrator.stop()
    logger.info(f"✅ Test complete, received {count} results")

if __name__ == "__main__":
    asyncio.run(main())

