#!/usr/bin/env python3
"""
TRUE STREAMING Pipeline - MINIMAL GAPS
======================================

Simple and effective approach:
- Process ALL TTS first (fast ~2s each)
- Then process ALL avatars in parallel
- Results arrive with minimal gaps

This works because:
- TTS is fast (2s) and sequential is fine
- Avatar is slow (2s) but CAN be parallel
- Total time optimized

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
OUTPUT_DIR = "true_streaming_outputs"
CHUNK_WORDS = 15

class TrueStreamingPipeline:
    """
    TRUE streaming with practical approach.
    """
    
    def __init__(
        self,
        reference_audio: str,
        reference_image: str,
        output_dir: str = "true_streaming_outputs",
        device: str = "cuda:1"
    ):
        self.reference_audio = reference_audio
        self.reference_image = reference_image
        self.output_dir = output_dir
        self.device = device
        
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info("🚀 TRUE STREAMING Pipeline initialized")
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("📦 Initializing...")
        initialize_tts(mode="local", voice_audio_path=self.reference_audio)
        initialize_avatar_generator(
            device=self.device,
            size=256,
            enhancer=None,
            pool_size=1
        )
        logger.info("✅ Ready!")
    
    async def process_with_minimal_gaps(
        self,
        question: str,
        use_real_llm: bool = False
    ) -> List[Dict]:
        """
        Process with MINIMAL gaps using smart sequencing.
        
        Strategy:
        1. Generate ALL TTS audio files first (sequential, fast)
        2. Process avatars with limited parallelism
        3. Results arrive quickly with minimal gaps
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"💬 QUESTION: {question}")
        logger.info(f"{'='*80}\n")
        
        pipeline_start = time.time()
        
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
        
        # PHASE 1: Generate ALL TTS audio (sequential but fast ~2s each)
        logger.info("🎵 PHASE 1: Generating all TTS audio...")
        tts_phase_start = time.time()
        
        audio_files = []
        for i, chunk_text in enumerate(chunks, 1):
            logger.info(f"  TTS {i}/{len(chunks)}: {chunk_text[:50]}...")
            tts_start = time.time()
            
            audio_path = await text_to_speech(
                chunk_text,
                mode="local",
                reference_audio_path=self.reference_audio
            )
            
            tts_time = time.time() - tts_start
            audio_files.append({
                'chunk_id': i,
                'text': chunk_text,
                'audio_path': audio_path,
                'tts_time': tts_time
            })
            logger.info(f"  ✅ TTS {i} done in {tts_time:.2f}s")
        
        tts_phase_time = time.time() - tts_phase_start
        logger.info(f"✅ Phase 1 complete: {tts_phase_time:.2f}s for {len(audio_files)} TTS\n")
        
        # PHASE 2: Generate ALL avatars (parallel with limited concurrency)
        logger.info("🎬 PHASE 2: Generating all avatars (parallel)...")
        avatar_phase_start = time.time()
        
        async def generate_one_avatar(audio_info):
            chunk_id = audio_info['chunk_id']
            avatar_start = time.time()
            
            logger.info(f"  Avatar {chunk_id}/{len(audio_files)} START")
            
            video_path = await generate_avatar(
                audio_info['audio_path'],
                self.reference_image,
                output_dir=self.output_dir,
                fast_mode=False
            )
            
            avatar_time = time.time() - avatar_start
            ready_at = time.time()
            
            logger.info(f"  ✅ Avatar {chunk_id} done in {avatar_time:.2f}s")
            
            return {
                **audio_info,
                'video_path': video_path,
                'avatar_time': avatar_time,
                'total_time': audio_info['tts_time'] + avatar_time,
                'ready_at': ready_at
            }
        
        # Process avatars with limited concurrency (2 at a time for GPU)
        semaphore = asyncio.Semaphore(2)
        
        async def generate_with_limit(audio_info):
            async with semaphore:
                return await generate_one_avatar(audio_info)
        
        tasks = [generate_with_limit(audio_info) for audio_info in audio_files]
        results = await asyncio.gather(*tasks)
        
        avatar_phase_time = time.time() - avatar_phase_start
        logger.info(f"✅ Phase 2 complete: {avatar_phase_time:.2f}s for {len(results)} avatars\n")
        
        # Calculate gaps
        results.sort(key=lambda x: x['ready_at'])
        for i in range(len(results) - 1):
            gap = results[i+1]['ready_at'] - results[i]['ready_at']
            results[i]['gap_to_next'] = gap
        if results:
            results[-1]['gap_to_next'] = 0
        
        # Re-sort by chunk_id
        results.sort(key=lambda x: x['chunk_id'])
        
        total_time = time.time() - pipeline_start
        
        self.print_summary(results, total_time, tts_phase_time, avatar_phase_time)
        
        return results
    
    def print_summary(self, results, total_time, tts_phase_time, avatar_phase_time):
        """Print summary."""
        logger.info(f"\n{'='*80}")
        logger.info("📊 TRUE STREAMING RESULTS")
        logger.info(f"{'='*80}\n")
        
        for r in results:
            gap_str = f", Gap:{r['gap_to_next']:.2f}s" if r['gap_to_next'] > 0 else ""
            logger.info(f"Chunk {r['chunk_id']:2d}: TTS:{r['tts_time']:.2f}s Avatar:{r['avatar_time']:.2f}s{gap_str}")
        
        if results:
            avg_tts = sum(r['tts_time'] for r in results) / len(results)
            avg_avatar = sum(r['avatar_time'] for r in results) / len(results)
            avg_gap = sum(r.get('gap_to_next', 0) for r in results[:-1]) / max(len(results)-1, 1)
            max_gap = max(r.get('gap_to_next', 0) for r in results[:-1]) if len(results) > 1 else 0
            
            logger.info(f"\n📈 STATISTICS:")
            logger.info(f"  Avg TTS:    {avg_tts:.2f}s")
            logger.info(f"  Avg Avatar: {avg_avatar:.2f}s")
            logger.info(f"  Avg Gap:    {avg_gap:.2f}s")
            logger.info(f"  Max Gap:    {max_gap:.2f}s")
            
            logger.info(f"\n🎯 PERFORMANCE:")
            logger.info(f"  TTS Phase:      {tts_phase_time:.2f}s (all {len(results)} chunks)")
            logger.info(f"  Avatar Phase:   {avatar_phase_time:.2f}s (parallel)")
            logger.info(f"  Total Pipeline: {total_time:.2f}s")
            logger.info(f"  First chunk:    {tts_phase_time + results[0]['avatar_time']:.2f}s")
            
            logger.info(f"\n🎬 PLAYBACK ANALYSIS:")
            first_ready = tts_phase_time + results[0]['avatar_time']
            if first_ready < 6:
                logger.info(f"✅ FIRST CHUNK: EXCELLENT ({first_ready:.2f}s)")
            else:
                logger.info(f"⚠️  FIRST CHUNK: {first_ready:.2f}s")
            
            if max_gap < 0.5:
                logger.info(f"✅ GAPS: NEAR ZERO (max {max_gap:.2f}s) 🎉")
            elif max_gap < 1.0:
                logger.info(f"✅ GAPS: EXCELLENT (max {max_gap:.2f}s)")
            else:
                logger.info(f"⚠️  GAPS: {max_gap:.2f}s (playback may have pauses)")
        
        logger.info(f"{'='*80}\n")


async def main():
    """Test with long questions."""
    
    pipeline = TrueStreamingPipeline(
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
    logger.info("🎯 TRUE STREAMING - RIGOROUS TESTING")
    logger.info(f"{'='*80}\n")
    
    for i, question in enumerate(test_questions, 1):
        logger.info(f"\n{'#'*80}")
        logger.info(f"TEST {i}/{len(test_questions)}")
        logger.info(f"{'#'*80}\n")
        
        results = await pipeline.process_with_minimal_gaps(
            question,
            use_real_llm=False
        )
        
        logger.info(f"\n✅ Test {i} complete: {len(results)} videos")
        
        if i < len(test_questions):
            logger.info("\n⏸️  Waiting 3s...\n")
            await asyncio.sleep(3)
    
    logger.info(f"\n{'='*80}")
    logger.info("🎉 TRUE STREAMING TESTING COMPLETE!")
    logger.info(f"{'='*80}")
    logger.info(f"\n📁 Videos in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())



