#!/usr/bin/env python3
"""
Parallel Streaming Avatar Pipeline - MAXIMUM PERFORMANCE
=========================================================

This implements PARALLEL processing to eliminate gaps between chunks:
- TTS and Avatar generation run in parallel for multiple chunks
- First chunk starts immediately while others process
- No gaps between video playback

Author: AI Assistant
Date: 2025-10-20
"""

import asyncio
import time
import os
from typing import List, Dict, Optional
import logging
from concurrent.futures import ThreadPoolExecutor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import pipeline components
from utils.tts import initialize_tts, text_to_speech
from utils.avatar_generator import initialize_avatar_generator, generate_avatar
from utils.llm import chat_with_llm_streaming

# Configuration
AUDIO_REF = "audio/Nafay_Org.mp3"
IMAGE_FILE = "audio/Huzaifa.jpg"
OUTPUT_DIR = "parallel_outputs"
CHUNK_WORDS = 15

class ParallelStreamingPipeline:
    """
    Advanced pipeline with PARALLEL chunk processing.
    """
    
    def __init__(
        self,
        reference_audio: str,
        reference_image: str,
        output_dir: str = "parallel_outputs",
        device: str = "cuda:1",
        max_parallel: int = 3
    ):
        self.reference_audio = reference_audio
        self.reference_image = reference_image
        self.output_dir = output_dir
        self.device = device
        self.max_parallel = max_parallel
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.stats = {
            'chunks_processed': 0,
            'total_tts_time': 0,
            'total_avatar_time': 0,
            'total_pipeline_time': 0,
            'first_chunk_time': 0,
            'chunk_times': []
        }
        
        logger.info(f"🚀 Parallel Pipeline initialized (max {max_parallel} concurrent chunks)")
    
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
        
        logger.info("✅ All components ready!")
    
    async def process_single_chunk(
        self,
        chunk_id: int,
        text: str,
        chunk_start_time: float
    ) -> Dict:
        """Process one chunk: TTS → Avatar."""
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
                logger.error(f"❌ TTS failed for chunk {chunk_id}")
                return None
            
            # Avatar
            avatar_start = time.time()
            video_path = await generate_avatar(
                audio_path,
                self.reference_image,
                output_dir=self.output_dir,
                fast_mode=False
            )
            avatar_time = time.time() - avatar_start
            
            if not video_path or not os.path.exists(video_path):
                logger.error(f"❌ Avatar failed for chunk {chunk_id}")
                return None
            
            total_time = time.time() - chunk_start_time
            
            result = {
                'chunk_id': chunk_id,
                'text': text,
                'video_path': video_path,
                'tts_time': tts_time,
                'avatar_time': avatar_time,
                'total_time': total_time,
                'ready_at': time.time()
            }
            
            logger.info(f"✅ Chunk {chunk_id} ready: {total_time:.2f}s (TTS: {tts_time:.2f}s, Avatar: {avatar_time:.2f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing chunk {chunk_id}: {e}")
            return None
    
    async def process_with_parallel(
        self,
        question: str,
        use_real_llm: bool = False
    ) -> List[Dict]:
        """
        Process LLM response with PARALLEL chunk processing.
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
                    logger.info(f"   📝 LLM chunk {len(chunks)}: {chunk[:50]}...")
            except Exception as e:
                logger.error(f"❌ LLM error: {e}")
                logger.info("🔄 Falling back to simulated response...")
                use_real_llm = False
        
        if not use_real_llm:
            # Simulated responses for testing
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
            
            # Select response based on question
            if "india" in question.lower() and "pakistan" in question.lower():
                full_response = responses["india and pakistan"]
            else:
                full_response = responses["america"]
            
            logger.info("🤖 Using simulated LLM response for testing...")
            words = full_response.split()
            chunks = [" ".join(words[i:i+CHUNK_WORDS]) for i in range(0, len(words), CHUNK_WORDS)]
        
        logger.info(f"✅ Got {len(chunks)} chunks from LLM\n")
        
        # Process chunks in parallel batches
        results = []
        semaphore = asyncio.Semaphore(self.max_parallel)
        
        async def process_with_semaphore(chunk_id, text):
            async with semaphore:
                chunk_start = time.time()
                logger.info(f"🔄 Starting chunk {chunk_id}/{len(chunks)}: {text[:50]}...")
                result = await self.process_single_chunk(chunk_id, text, chunk_start)
                return result
        
        # Create all tasks
        tasks = [
            process_with_semaphore(i+1, chunk_text)
            for i, chunk_text in enumerate(chunks)
        ]
        
        # Wait for all to complete
        logger.info(f"\n🚀 Processing {len(tasks)} chunks with max {self.max_parallel} parallel...\n")
        completed_results = await asyncio.gather(*tasks)
        
        # Filter out None results and sort by chunk_id
        results = [r for r in completed_results if r is not None]
        results.sort(key=lambda x: x['chunk_id'])
        
        pipeline_time = time.time() - pipeline_start
        
        # Calculate gaps
        for i in range(len(results) - 1):
            gap = results[i+1]['ready_at'] - results[i]['ready_at']
            results[i]['gap_to_next'] = gap
        if results:
            results[-1]['gap_to_next'] = 0
        
        # Update stats
        self.stats['chunks_processed'] = len(results)
        self.stats['total_pipeline_time'] = pipeline_time
        if results:
            self.stats['first_chunk_time'] = results[0]['total_time']
            self.stats['total_tts_time'] = sum(r['tts_time'] for r in results)
            self.stats['total_avatar_time'] = sum(r['avatar_time'] for r in results)
            self.stats['chunk_times'] = [r['total_time'] for r in results]
        
        self.print_summary(results, pipeline_time)
        
        return results
    
    def print_summary(self, results: List[Dict], total_time: float):
        """Print detailed performance summary."""
        logger.info(f"\n{'='*80}")
        logger.info("📊 PARALLEL PIPELINE PERFORMANCE SUMMARY")
        logger.info(f"{'='*80}\n")
        
        for r in results:
            gap_str = f", Gap: {r['gap_to_next']:.2f}s" if r['gap_to_next'] > 0 else ""
            logger.info(f"Chunk {r['chunk_id']:2d}: TTS {r['tts_time']:.2f}s + Avatar {r['avatar_time']:.2f}s = {r['total_time']:.2f}s{gap_str}")
        
        if results:
            avg_tts = sum(r['tts_time'] for r in results) / len(results)
            avg_avatar = sum(r['avatar_time'] for r in results) / len(results)
            avg_total = sum(r['total_time'] for r in results) / len(results)
            avg_gap = sum(r.get('gap_to_next', 0) for r in results[:-1]) / max(len(results)-1, 1)
            
            logger.info(f"\nAVERAGES:")
            logger.info(f"  TTS:    {avg_tts:.2f}s")
            logger.info(f"  Avatar: {avg_avatar:.2f}s")
            logger.info(f"  Total:  {avg_total:.2f}s")
            logger.info(f"  Gap:    {avg_gap:.2f}s")
            
            logger.info(f"\nKEY METRICS:")
            logger.info(f"  Total pipeline time: {total_time:.2f}s")
            logger.info(f"  First chunk ready:   {results[0]['total_time']:.2f}s")
            logger.info(f"  Sequential time:     {sum(r['total_time'] for r in results):.2f}s")
            logger.info(f"  Speedup factor:      {sum(r['total_time'] for r in results) / total_time:.2f}x")
            
            # Check if gaps are acceptable
            max_gap = max(r.get('gap_to_next', 0) for r in results[:-1]) if len(results) > 1 else 0
            
            if results[0]['total_time'] < 5:
                logger.info(f"\n✅ EXCELLENT! First chunk in {results[0]['total_time']:.2f}s")
            elif results[0]['total_time'] < 10:
                logger.info(f"\n⚠️  GOOD! First chunk in {results[0]['total_time']:.2f}s")
            else:
                logger.info(f"\n❌ SLOW! First chunk in {results[0]['total_time']:.2f}s")
            
            if max_gap < 2:
                logger.info(f"✅ NO GAPS! Max gap between chunks: {max_gap:.2f}s")
            elif max_gap < 5:
                logger.info(f"⚠️  SMALL GAPS! Max gap: {max_gap:.2f}s")
            else:
                logger.info(f"❌ LARGE GAPS! Max gap: {max_gap:.2f}s")
        
        logger.info(f"{'='*80}\n")


async def main():
    """Test the parallel pipeline with long questions."""
    
    pipeline = ParallelStreamingPipeline(
        reference_audio=AUDIO_REF,
        reference_image=IMAGE_FILE,
        output_dir=OUTPUT_DIR,
        device="cuda:1",
        max_parallel=3  # Process 3 chunks simultaneously
    )
    
    await pipeline.initialize()
    
    # Test questions
    test_questions = [
        "Tell me the difference between India and Pakistan?",
        "What are the pros and cons of living in America?"
    ]
    
    logger.info(f"\n{'='*80}")
    logger.info("🧪 RIGOROUS TESTING WITH LONG QUESTIONS")
    logger.info(f"{'='*80}\n")
    
    for i, question in enumerate(test_questions, 1):
        logger.info(f"\n{'#'*80}")
        logger.info(f"TEST {i}/{len(test_questions)}")
        logger.info(f"{'#'*80}\n")
        
        results = await pipeline.process_with_parallel(
            question,
            use_real_llm=False  # Set to True to use actual LLM
        )
        
        logger.info(f"\n✅ Test {i} complete: {len(results)} videos generated")
        
        # Small delay between tests
        if i < len(test_questions):
            logger.info("\n⏸️  Waiting 2s before next test...\n")
            await asyncio.sleep(2)
    
    logger.info(f"\n{'='*80}")
    logger.info("🎉 ALL TESTS COMPLETE!")
    logger.info(f"{'='*80}")
    logger.info(f"\n📁 All videos saved in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())





