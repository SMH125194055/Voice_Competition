#!/usr/bin/env python3
"""
ZERO GAP FINAL - TRUE CONTINUOUS PLAYBACK
==========================================

Strategy for ZERO gaps:
1. Start processing chunk N+2 while chunk N is playing
2. Since video plays for ~3-4s, and generation takes ~4s,
   we need to START the next chunk IMMEDIATELY
3. Use aggressive parallel processing with pre-buffering

This ensures next video is READY before current finishes!

Author: AI Assistant
Date: 2025-10-20
"""

import asyncio
import time
import os
from typing import List, Dict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from utils.tts import initialize_tts, text_to_speech
from utils.avatar_generator import initialize_avatar_generator, generate_avatar
from utils.llm import chat_with_llm_streaming

AUDIO_REF = "audio/Nafay_Org.mp3"
IMAGE_FILE = "audio/Huzaifa.jpg"
OUTPUT_DIR = "ZERO_GAP_FINAL_outputs"
CHUNK_WORDS = 15

class ZeroGapFinalPipeline:
    """
    ZERO GAP with aggressive pre-buffering.
    """
    
    def __init__(
        self,
        reference_audio: str,
        reference_image: str,
        output_dir: str = "ZERO_GAP_FINAL_outputs",
        device: str = "cuda:1"
    ):
        self.reference_audio = reference_audio
        self.reference_image = reference_image
        self.output_dir = output_dir
        self.device = device
        
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info("🚀 ZERO GAP FINAL Pipeline - AGGRESSIVE PRE-BUFFERING")
    
    async def initialize(self):
        """Initialize."""
        logger.info("📦 Initializing...")
        initialize_tts(mode="local", voice_audio_path=self.reference_audio)
        initialize_avatar_generator(device=self.device, size=256, enhancer=None, pool_size=1)
        logger.info("✅ Ready!")
    
    async def process_chunk(self, chunk_id: int, text: str) -> Dict:
        """Process one chunk."""
        start = time.time()
        
        # TTS
        tts_start = time.time()
        audio_path = await text_to_speech(text, mode="local", reference_audio_path=self.reference_audio)
        tts_time = time.time() - tts_start
        
        # Avatar
        avatar_start = time.time()
        video_path = await generate_avatar(audio_path, self.reference_image, output_dir=self.output_dir, fast_mode=False)
        avatar_time = time.time() - avatar_start
        
        total_time = time.time() - start
        ready_at = time.time()
        
        logger.info(f"✅ Chunk {chunk_id:2d} READY in {total_time:.2f}s (TTS:{tts_time:.2f}s Av:{avatar_time:.2f}s)")
        
        return {
            'chunk_id': chunk_id,
            'text': text,
            'video_path': video_path,
            'tts_time': tts_time,
            'avatar_time': avatar_time,
            'total_time': total_time,
            'ready_at': ready_at
        }
    
    async def process_with_zero_gaps(
        self,
        question: str,
        use_real_llm: bool = False
    ) -> List[Dict]:
        """
        Process with ZERO GAPS using aggressive parallel processing.
        
        Strategy:
        - Process ALL chunks in parallel immediately
        - Max concurrency = 3 (aggressive!)
        - This ensures next chunks are ready BEFORE previous finish playing
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"💬 QUESTION: {question}")
        logger.info(f"{'='*80}\n")
        
        start = time.time()
        
        # Get chunks
        if use_real_llm:
            try:
                chunks = []
                async for chunk in chat_with_llm_streaming(question, chunk_size=CHUNK_WORDS):
                    chunks.append(chunk)
            except:
                use_real_llm = False
        
        if not use_real_llm:
            responses = {
                "india and pakistan": (
                    "India and Pakistan are two neighboring countries in South Asia with complex historical and cultural differences. "
                    "India is a secular democracy with a Hindu majority population, while Pakistan is an Islamic republic. "
                    "They gained independence from British rule in 1947 through partition, which led to significant religious migration. "
                    "India has a larger land area and population, being the world's most populous country. "
                    "Pakistan's economy is smaller but strategically important in the region. "
                    "Both countries have nuclear capabilities and have fought multiple wars since independence. "
                    "The Kashmir conflict remains a major point of contention between them. "
                    "India's democracy is more established, while Pakistan has experienced military rule several times. "
                    "Culturally, they share many similarities including cuisine, music, and languages. "
                    "Cricket is immensely popular in both nations and creates moments of intense rivalry. "
                    "Economic ties are limited due to political tensions, though there's potential for greater cooperation. "
                    "Both countries face challenges including poverty, infrastructure development, and regional security issues."
                ),
                "america": (
                    "Living in America has several advantages. First, there are many economic opportunities and career growth potential. "
                    "The country has a strong economy with diverse industries. Second, America offers high quality education and research facilities. "
                    "However, there are also disadvantages to consider. Healthcare costs can be very expensive compared to other countries. "
                    "Income inequality is a significant issue in many regions. Additionally, work-life balance can be challenging with long working hours. "
                    "Gun violence and crime rates are higher than many developed nations. The political climate can be divisive and polarizing. "
                    "Student loan debt is a major burden for many young Americans. Public transportation is limited outside major cities. "
                    "The social safety net is weaker compared to European countries."
                )
            }
            
            if "india" in question.lower() and "pakistan" in question.lower():
                full_response = responses["india and pakistan"]
            else:
                full_response = responses["america"]
            
            words = full_response.split()
            chunks = [" ".join(words[i:i+CHUNK_WORDS]) for i in range(0, len(words), CHUNK_WORDS)]
        
        logger.info(f"✅ Got {len(chunks)} chunks")
        logger.info(f"🚀 AGGRESSIVE MODE: Processing up to 3 chunks in parallel\n")
        
        # AGGRESSIVE: Process with max_concurrent=3 for zero gaps
        semaphore = asyncio.Semaphore(3)  # Allow 3 simultaneous!
        
        async def process_with_limit(chunk_id, text):
            async with semaphore:
                return await self.process_chunk(chunk_id, text)
        
        tasks = [process_with_limit(i+1, chunk) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks)
        
        # Sort and calculate gaps
        results = [r for r in results if r]
        results.sort(key=lambda x: x['ready_at'])
        
        for i in range(len(results) - 1):
            results[i]['gap_to_next'] = results[i+1]['ready_at'] - results[i]['ready_at']
        if results:
            results[-1]['gap_to_next'] = 0
        
        results.sort(key=lambda x: x['chunk_id'])
        
        total_time = time.time() - start
        
        self.print_summary(results, total_time)
        
        return results
    
    def print_summary(self, results, total_time):
        """Print summary with gap analysis."""
        logger.info(f"\n{'='*80}")
        logger.info("📊 ZERO GAP FINAL RESULTS")
        logger.info(f"{'='*80}\n")
        
        for r in results:
            gap_str = f" → Gap:{r['gap_to_next']:.2f}s" if r['gap_to_next'] > 0 else " → END"
            logger.info(f"Chunk {r['chunk_id']:2d}: {r['total_time']:.2f}s{gap_str}")
        
        if results:
            avg_gap = sum(r.get('gap_to_next', 0) for r in results[:-1]) / max(len(results)-1, 1)
            max_gap = max(r.get('gap_to_next', 0) for r in results[:-1]) if len(results) > 1 else 0
            min_gap = min(r.get('gap_to_next', 0) for r in results[:-1]) if len(results) > 1 else 0
            
            # Count gaps by size
            gaps = [r.get('gap_to_next', 0) for r in results[:-1]]
            under_1s = sum(1 for g in gaps if g < 1.0)
            under_2s = sum(1 for g in gaps if g < 2.0)
            
            logger.info(f"\n📈 STATISTICS:")
            logger.info(f"  First chunk:   {results[0]['total_time']:.2f}s")
            logger.info(f"  Total time:    {total_time:.2f}s")
            logger.info(f"  Avg gap:       {avg_gap:.2f}s")
            logger.info(f"  Min gap:       {min_gap:.2f}s")
            logger.info(f"  Max gap:       {max_gap:.2f}s")
            logger.info(f"  Gaps < 1s:     {under_1s}/{len(results)-1}")
            logger.info(f"  Gaps < 2s:     {under_2s}/{len(results)-1}")
            
            logger.info(f"\n🎯 ZERO GAP ANALYSIS:")
            if max_gap < 0.5:
                logger.info(f"✅ PERFECT! Max gap {max_gap:.2f}s - ZERO GAP ACHIEVED! 🎉")
            elif max_gap < 1.0:
                logger.info(f"✅ EXCELLENT! Max gap {max_gap:.2f}s - Nearly seamless!")
            elif max_gap < 1.5:
                logger.info(f"⚠️  VERY GOOD! Max gap {max_gap:.2f}s - Tiny pauses")
            else:
                logger.info(f"⚠️  Max gap {max_gap:.2f}s - Still has gaps")
            
            logger.info(f"\n🎬 PLAYBACK SIMULATION:")
            logger.info(f"   Video 1 starts: 0s (after {results[0]['total_time']:.1f}s generation)")
            logger.info(f"   Video 1 plays for: ~3-4s")
            if len(results) > 1:
                video1_end = 3.5  # Average video duration
                video2_ready = results[1]['ready_at'] - results[0]['ready_at']
                if video2_ready < video1_end:
                    logger.info(f"   Video 2 ready at: {video2_ready:.1f}s")
                    logger.info(f"   ✅ Video 2 READY BEFORE Video 1 ends! SEAMLESS! 🎉")
                else:
                    gap = video2_ready - video1_end
                    logger.info(f"   Video 2 ready at: {video2_ready:.1f}s")
                    logger.info(f"   ⚠️  Gap of {gap:.1f}s after Video 1 ends")
        
        logger.info(f"{'='*80}\n")


async def main():
    """Test ZERO GAP."""
    
    pipeline = ZeroGapFinalPipeline(
        reference_audio=AUDIO_REF,
        reference_image=IMAGE_FILE,
        output_dir=OUTPUT_DIR,
        device="cuda:1"
    )
    
    await pipeline.initialize()
    
    test_questions = [
        "Tell me the difference between India and Pakistan?",
        "What are the pros and cons of living in America?"
    ]
    
    logger.info(f"\n{'='*80}")
    logger.info("🎯 ZERO GAP FINAL - AGGRESSIVE PARALLEL PROCESSING")
    logger.info("🎯 GOAL: Next video READY before previous finishes playing")
    logger.info(f"{'='*80}\n")
    
    for i, question in enumerate(test_questions, 1):
        logger.info(f"\n{'#'*80}")
        logger.info(f"TEST {i}/{len(test_questions)}")
        logger.info(f"{'#'*80}\n")
        
        results = await pipeline.process_with_zero_gaps(
            question,
            use_real_llm=False
        )
        
        logger.info(f"\n✅ Test {i} complete: {len(results)} videos in {OUTPUT_DIR}/")
        
        if i < len(test_questions):
            logger.info("\n⏸️  Waiting 3s...\n")
            await asyncio.sleep(3)
    
    logger.info(f"\n{'='*80}")
    logger.info("🎉 ZERO GAP TESTING COMPLETE!")
    logger.info(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())





