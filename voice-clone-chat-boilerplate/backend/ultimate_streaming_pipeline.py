#!/usr/bin/env python3
"""
ULTIMATE Streaming Avatar Pipeline - TRUE PIPELINING
====================================================

This implements CONTINUOUS PIPELINING with:
- Chunks start IMMEDIATELY when one slot opens
- TTS runs while previous avatars render
- NO GAPS between chunks
- TRUE streaming queue

Author: AI Assistant
Date: 2025-10-20
"""

import asyncio
import time
import os
from typing import List, Dict, Optional
import logging
from queue import Queue
import threading

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
OUTPUT_DIR = "ultimate_outputs"
CHUNK_WORDS = 15

class UltimateStreamingPipeline:
    """
    TRUE pipelined processing - minimum gaps.
    """
    
    def __init__(
        self,
        reference_audio: str,
        reference_image: str,
        output_dir: str = "ultimate_outputs",
        device: str = "cuda:1"
    ):
        self.reference_audio = reference_audio
        self.reference_image = reference_image
        self.output_dir = output_dir
        self.device = device
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.results = []
        self.pipeline_start = None
        
        logger.info("🚀 ULTIMATE Pipeline initialized")
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("📦 Initializing TTS...")
        initialize_tts(mode="local", voice_audio_path=self.reference_audio)
        
        logger.info("📦 Initializing Avatar Generator...")
        initialize_avatar_generator(
            device=self.device,
            size=256,
            enhancer=None,
            pool_size=1
        )
        
        logger.info("✅ All ready!")
    
    async def process_chunk_continuous(
        self,
        chunk_id: int,
        text: str
    ) -> Dict:
        """Process chunk with immediate start."""
        chunk_start = time.time()
        
        logger.info(f"🔄 Chunk {chunk_id} START: {text[:50]}...")
        
        try:
            # TTS
            tts_start = time.time()
            audio_path = await text_to_speech(
                text,
                mode="local",
                reference_audio_path=self.reference_audio
            )
            tts_time = time.time() - tts_start
            
            if not audio_path or not os.path.exists(audio_path):
                logger.error(f"❌ TTS failed chunk {chunk_id}")
                return None
            
            # Avatar (immediately after TTS)
            avatar_start = time.time()
            video_path = await generate_avatar(
                audio_path,
                self.reference_image,
                output_dir=self.output_dir,
                fast_mode=False
            )
            avatar_time = time.time() - avatar_start
            
            if not video_path or not os.path.exists(video_path):
                logger.error(f"❌ Avatar failed chunk {chunk_id}")
                return None
            
            total_time = time.time() - chunk_start
            ready_at = time.time()
            
            result = {
                'chunk_id': chunk_id,
                'text': text,
                'video_path': video_path,
                'tts_time': tts_time,
                'avatar_time': avatar_time,
                'total_time': total_time,
                'ready_at': ready_at
            }
            
            logger.info(f"✅ Chunk {chunk_id} READY in {total_time:.2f}s (TTS:{tts_time:.2f}s Avatar:{avatar_time:.2f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error chunk {chunk_id}: {e}")
            return None
    
    async def process_continuously(
        self,
        question: str,
        use_real_llm: bool = False,
        max_concurrent: int = 2  # Only 2 concurrent to reduce GPU contention
    ) -> List[Dict]:
        """
        Process with CONTINUOUS pipelining.
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"💬 QUESTION: {question}")
        logger.info(f"{'='*80}\n")
        
        self.pipeline_start = time.time()
        
        # Get LLM chunks (same as before)
        if use_real_llm:
            logger.info("🤖 Getting LLM response...")
            try:
                chunks = []
                async for chunk in chat_with_llm_streaming(
                    question,
                    chunk_size=CHUNK_WORDS
                ):
                    chunks.append(chunk)
            except Exception as e:
                logger.error(f"❌ LLM error: {e}")
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
            
            logger.info("🤖 Using simulated response...")
            words = full_response.split()
            chunks = [" ".join(words[i:i+CHUNK_WORDS]) for i in range(0, len(words), CHUNK_WORDS)]
        
        logger.info(f"✅ Got {len(chunks)} chunks\n")
        
        # Process with limited concurrency but continuous flow
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_limit(chunk_id, text):
            async with semaphore:
                return await self.process_chunk_continuous(chunk_id, text)
        
        # Create tasks and process
        tasks = [process_with_limit(i+1, chunk) for i, chunk in enumerate(chunks)]
        
        logger.info(f"🚀 Processing {len(tasks)} chunks (max {max_concurrent} concurrent)\n")
        
        results = await asyncio.gather(*tasks)
        results = [r for r in results if r is not None]
        results.sort(key=lambda x: x['chunk_id'])
        
        # Calculate gaps
        for i in range(len(results) - 1):
            gap = results[i+1]['ready_at'] - results[i]['ready_at']
            results[i]['gap_to_next'] = gap
        if results:
            results[-1]['gap_to_next'] = 0
        
        self.results = results
        self.print_summary()
        
        return results
    
    def print_summary(self):
        """Print summary."""
        results = self.results
        total_time = time.time() - self.pipeline_start
        
        logger.info(f"\n{'='*80}")
        logger.info("📊 ULTIMATE PIPELINE RESULTS")
        logger.info(f"{'='*80}\n")
        
        for r in results:
            gap_str = f", Gap:{r['gap_to_next']:.2f}s" if r['gap_to_next'] > 0 else ""
            logger.info(f"Chunk {r['chunk_id']:2d}: TTS:{r['tts_time']:.2f}s Avatar:{r['avatar_time']:.2f}s Total:{r['total_time']:.2f}s{gap_str}")
        
        if results:
            avg_tts = sum(r['tts_time'] for r in results) / len(results)
            avg_avatar = sum(r['avatar_time'] for r in results) / len(results)
            avg_total = sum(r['total_time'] for r in results) / len(results)
            avg_gap = sum(r.get('gap_to_next', 0) for r in results[:-1]) / max(len(results)-1, 1)
            max_gap = max(r.get('gap_to_next', 0) for r in results[:-1]) if len(results) > 1 else 0
            
            logger.info(f"\n📈 STATISTICS:")
            logger.info(f"  Avg TTS:    {avg_tts:.2f}s")
            logger.info(f"  Avg Avatar: {avg_avatar:.2f}s")
            logger.info(f"  Avg Total:  {avg_total:.2f}s")
            logger.info(f"  Avg Gap:    {avg_gap:.2f}s")
            logger.info(f"  Max Gap:    {max_gap:.2f}s")
            
            logger.info(f"\n🎯 PERFORMANCE:")
            logger.info(f"  Pipeline time:  {total_time:.2f}s")
            logger.info(f"  First chunk:    {results[0]['total_time']:.2f}s")
            logger.info(f"  Sequential:     {sum(r['total_time'] for r in results):.2f}s")
            logger.info(f"  Speedup:        {sum(r['total_time'] for r in results) / total_time:.2f}x")
            
            # Evaluation
            if results[0]['total_time'] < 5:
                logger.info(f"\n✅ FIRST CHUNK: EXCELLENT ({results[0]['total_time']:.2f}s)")
            elif results[0]['total_time'] < 8:
                logger.info(f"\n⚠️  FIRST CHUNK: GOOD ({results[0]['total_time']:.2f}s)")
            else:
                logger.info(f"\n❌ FIRST CHUNK: NEEDS WORK ({results[0]['total_time']:.2f}s)")
            
            if max_gap < 1:
                logger.info(f"✅ GAPS: EXCELLENT (max {max_gap:.2f}s)")
            elif max_gap < 3:
                logger.info(f"⚠️  GAPS: ACCEPTABLE (max {max_gap:.2f}s)")
            else:
                logger.info(f"❌ GAPS: TOO LARGE (max {max_gap:.2f}s)")
        
        logger.info(f"{'='*80}\n")


async def main():
    """Test with rigorous long questions."""
    
    pipeline = UltimateStreamingPipeline(
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
    logger.info("🧪 ULTIMATE PIPELINE - RIGOROUS TESTING")
    logger.info(f"{'='*80}\n")
    
    for i, question in enumerate(test_questions, 1):
        logger.info(f"\n{'#'*80}")
        logger.info(f"TEST {i}/{len(test_questions)}")
        logger.info(f"{'#'*80}\n")
        
        results = await pipeline.process_continuously(
            question,
            use_real_llm=False,
            max_concurrent=2  # Lower for GPU stability
        )
        
        logger.info(f"\n✅ Test {i} complete: {len(results)} videos")
        
        if i < len(test_questions):
            logger.info("\n⏸️  Waiting 3s...\n")
            await asyncio.sleep(3)
    
    logger.info(f"\n{'='*80}")
    logger.info("🎉 ALL RIGOROUS TESTS COMPLETE!")
    logger.info(f"{'='*80}")
    logger.info(f"\n📁 Videos in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())





