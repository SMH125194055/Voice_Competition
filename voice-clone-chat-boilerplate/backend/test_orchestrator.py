#!/usr/bin/env python
import sys
import os
import logging
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

async def test_orchestrator():
    from api.parallel_pipeline import ParallelPipelineOrchestrator
    import asyncio
    
    logger.info("Creating orchestrator...")
    orchestrator = ParallelPipelineOrchestrator()
    logger.info("✅ Orchestrator created")
    
    # Try to start it
    question = "What is 2+2?"
    reference_image = os.path.join(os.path.dirname(__file__), "Avatar/References/ref_1761131562372.jpg")
    reference_audio = os.path.join(os.path.dirname(__file__), "audio/reference_voices/ref_1761118578.wav")
    
    logger.info("Starting orchestrator...")
    orchestrator.start(
        question=question,
        reference_image=reference_image,
        reference_audio=reference_audio,
        emotion=4,
        pose={},
        gaze=True
    )
    logger.info("✅ Orchestrator started")
    
    # Try to stream results
    logger.info("Streaming results...")
    count = 0
    async for result in orchestrator.stream_results():
        logger.info(f"Result {count}: {result}")
        count += 1
        if count >= 5:  # Get first 5 results
            break
    
    orchestrator.stop()
    logger.info("✅ Test complete")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_orchestrator())

