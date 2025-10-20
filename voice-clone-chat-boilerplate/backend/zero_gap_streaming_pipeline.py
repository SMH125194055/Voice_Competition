#!/usr/bin/env python3
"""
ZERO GAP Streaming Avatar Pipeline - TRUE CONTINUOUS STREAMING
==============================================================

This implements OVERLAPPING pipeline processing:
- Start next TTS IMMEDIATELY when previous TTS finishes
- Don't wait for avatar to complete
- Chunks arrive continuously with ZERO gaps
- True streaming queue for seamless playback

Author: AI Assistant
Date: 2025-10-20
"""

import asyncio
import time
import os
from typing import List, Dict, Optional
import logging
from collections import deque

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
OUTPUT_DIR = "zero_gap_outputs"
CHUNK_WORDS = 15

class ZeroGapStreamingPipeline:
    """
    TRUE continuous streaming with ZERO gaps.
    
    Strategy:
    1. Process TTS for chunk N
    2. IMMEDIATELY start TTS for chunk N+1 (don't wait for avatar)
    3. Avatar for chunk N processes in parallel
    4. Results arrive in perfect sequence with no gaps
    """
    
    def __init__(
        self,
        reference_audio: str,
        reference_image: str,
        output_dir: str = "zero_gap_outputs",
        device: str = "cuda:1"
    ):
        self.reference_audio = reference_audio
        self.reference_image = reference_image
        self.output_dir = output_dir
        self.device = device
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.results = []
        self.pipeline_start = None
        
        logger.info("🚀 ZERO GAP Pipeline initialized")
    
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
    
    async def process_chunk_pipeline(
        self,
        chunk_id: int,
        text: str,
        tts_queue: asyncio.Queue,
        avatar_queue: asyncio.Queue
    ):
        """
        Process one chunk in TRUE pipeline style:
        1. Do TTS
        2. Signal next chunk can start TTS
        3. Do Avatar (in parallel with next chunk's TTS)
        """
        chunk_start = time.time()
        
        logger.info(f"🔄 Chunk {chunk_id} TTS START: {text[:50]}...")
        
        # STEP 1: TTS (FAST - ~2s)
        tts_start = time.time()
        try:
            audio_path = await text_to_speech(
                text,
                mode="local",
                reference_audio_path=self.reference_audio
            )
            tts_time = time.time() - tts_start
            
            if not audio_path or not os.path.exists(audio_path):
                logger.error(f"❌ TTS failed chunk {chunk_id}")
                await tts_queue.put(None)  # Signal next can start
                await avatar_queue.put(None)
                return
            
            logger.info(f"✅ Chunk {chunk_id} TTS done in {tts_time:.2f}s")
            
            # IMMEDIATELY signal next chunk can start TTS
            await tts_queue.put(chunk_id)
            
        except Exception as e:
            logger.error(f"❌ TTS error chunk {chunk_id}: {e}")
            await tts_queue.put(None)
            await avatar_queue.put(None)
            return
        
        # STEP 2: Avatar (SLOWER - ~2s, but OVERLAPS with next TTS)
        avatar_start = time.time()
        try:
            video_path = await generate_avatar(
                audio_path,
                self.reference_image,
                output_dir=self.output_dir,
                fast_mode=False
            )
            avatar_time = time.time() - avatar_start
            
            if not video_path or not os.path.exists(video_path):
                logger.error(f"❌ Avatar failed chunk {chunk_id}")
                await avatar_queue.put(None)
                return
            
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
            
            logger.info(f"✅ Chunk {chunk_id} COMPLETE in {total_time:.2f}s (TTS:{tts_time:.2f}s Avatar:{avatar_time:.2f}s)")
            
            # Send to output queue
            await avatar_queue.put(result)
            
        except Exception as e:
            logger.error(f"❌ Avatar error chunk {chunk_id}: {e}")
            await avatar_queue.put(None)
    
    async def process_with_zero_gaps(
        self,
        question: str,
        use_real_llm: bool = False
    ) -> List[Dict]:
        """
        Process with ZERO GAPS using overlapping pipeline.
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"💬 QUESTION: {question}")
        logger.info(f"{'='*80}\n")
        
        self.pipeline_start = time.time()
        
        # Get LLM chunks
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
        logger.info("🚀 Processing with ZERO GAP overlapping pipeline...\n")
        
        # Create queues for coordination
        tts_queue = asyncio.Queue()
        avatar_queue = asyncio.Queue()
        
        # Start first chunk immediately
        await tts_queue.put(0)  # Signal chunk 0 can start
        
        # Create all processing coroutines
        async def process_all_chunks():
            tasks = []
            for i, chunk_text in enumerate(chunks):
                # Wait for signal that this chunk can start TTS
                async def process_when_ready(chunk_id, text):
                    # Wait for previous chunk's TTS to finish
                    await tts_queue.get()
                    await self.process_chunk_pipeline(chunk_id, text, tts_queue, avatar_queue)
                
                tasks.append(process_when_ready(i+1, chunk_text))
            
            await asyncio.gather(*tasks)
        
        # Start all tasks (they'll coordinate via queues)
        processing_task = asyncio.create_task(process_all_chunks())
        
        # Collect results as they arrive
        results = []
        for _ in range(len(chunks)):
            result = await avatar_queue.get()
            if result is not None:
                results.append(result)
        
        # Wait for all to complete
        await processing_task
        
        # Sort by chunk_id
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
        """Print summary with gap analysis."""
        results = self.results
        total_time = time.time() - self.pipeline_start
        
        logger.info(f"\n{'='*80}")
        logger.info("📊 ZERO GAP PIPELINE RESULTS")
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
            min_gap = min(r.get('gap_to_next', 0) for r in results[:-1]) if len(results) > 1 else 0
            
            logger.info(f"\n📈 STATISTICS:")
            logger.info(f"  Avg TTS:    {avg_tts:.2f}s")
            logger.info(f"  Avg Avatar: {avg_avatar:.2f}s")
            logger.info(f"  Avg Total:  {avg_total:.2f}s")
            logger.info(f"  Avg Gap:    {avg_gap:.2f}s")
            logger.info(f"  Min Gap:    {min_gap:.2f}s")
            logger.info(f"  Max Gap:    {max_gap:.2f}s")
            
            logger.info(f"\n🎯 PERFORMANCE:")
            logger.info(f"  Pipeline time:  {total_time:.2f}s")
            logger.info(f"  First chunk:    {results[0]['total_time']:.2f}s")
            logger.info(f"  Sequential:     {sum(r['total_time'] for r in results):.2f}s")
            logger.info(f"  Speedup:        {sum(r['total_time'] for r in results) / total_time:.2f}x")
            
            # Gap analysis
            gaps_below_1s = sum(1 for r in results[:-1] if r.get('gap_to_next', 0) < 1.0)
            gaps_below_05s = sum(1 for r in results[:-1] if r.get('gap_to_next', 0) < 0.5)
            
            logger.info(f"\n🎬 GAP ANALYSIS:")
            logger.info(f"  Gaps < 0.5s: {gaps_below_05s}/{len(results)-1} chunks")
            logger.info(f"  Gaps < 1.0s: {gaps_below_1s}/{len(results)-1} chunks")
            
            # Evaluation
            if results[0]['total_time'] < 5:
                logger.info(f"\n✅ FIRST CHUNK: EXCELLENT ({results[0]['total_time']:.2f}s)")
            else:
                logger.info(f"\n⚠️  FIRST CHUNK: {results[0]['total_time']:.2f}s")
            
            if max_gap < 0.5:
                logger.info(f"✅ GAPS: ZERO GAP! (max {max_gap:.2f}s) 🎉")
            elif max_gap < 1.0:
                logger.info(f"✅ GAPS: EXCELLENT (max {max_gap:.2f}s)")
            elif max_gap < 2.0:
                logger.info(f"⚠️  GAPS: ACCEPTABLE (max {max_gap:.2f}s)")
            else:
                logger.info(f"❌ GAPS: STILL TOO LARGE (max {max_gap:.2f}s)")
        
        logger.info(f"{'='*80}\n")


async def main():
    """Test with long questions and ZERO GAP target."""
    
    pipeline = ZeroGapStreamingPipeline(
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
    logger.info("🎯 ZERO GAP PIPELINE - RIGOROUS TESTING")
    logger.info(f"{'='*80}\n")
    
    for i, question in enumerate(test_questions, 1):
        logger.info(f"\n{'#'*80}")
        logger.info(f"TEST {i}/{len(test_questions)}")
        logger.info(f"{'#'*80}\n")
        
        results = await pipeline.process_with_zero_gaps(
            question,
            use_real_llm=False
        )
        
        logger.info(f"\n✅ Test {i} complete: {len(results)} videos")
        
        if i < len(test_questions):
            logger.info("\n⏸️  Waiting 3s...\n")
            await asyncio.sleep(3)
    
    logger.info(f"\n{'='*80}")
    logger.info("🎉 ZERO GAP TESTING COMPLETE!")
    logger.info(f"{'='*80}")
    logger.info(f"\n📁 Videos in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())

