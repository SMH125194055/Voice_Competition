#!/usr/bin/env python3
"""
Avatar Pipeline Optimization Script
Goal: Achieve near real-time avatar generation through streaming and parallel processing

Strategy:
1. Start with baseline measurements
2. Apply progressive optimizations:
   - Reduce resolution (256 -> 128 -> 64)
   - Lower FPS (25 -> 15 -> 10)
   - Enable parallel chunk processing
   - Implement streaming queue
   - Optimize preprocessing caching
3. Test with real questions
4. Measure improvements
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import multiprocessing as mp
from queue import Queue
import json

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set environment for optimizations
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test questions
TEST_QUESTIONS = [
    "What are the pros and cons of living in America?",
    "How does climate change affect the economy?",
    "What is artificial intelligence?",
]

# Reference files
REFERENCE_AUDIO = "audio/Nafay_Org.mp3"
REFERENCE_IMAGE = "audio/Huzaifa.jpg"


class AvatarPipelineTester:
    def __init__(self):
        self.results = []
        self.baseline_time = None
        
    async def initialize_services(self):
        """Initialize all required services"""
        logger.info("🚀 Initializing services...")
        
        # Import after setting env vars
        from utils.tts import initialize_tts, text_to_speech
        from utils.avatar_generator import AvatarGenerator
        from utils.llm import chat_with_llm_streaming
        
        self.tts_init = initialize_tts
        self.tts_gen = text_to_speech
        self.llm_stream = chat_with_llm_streaming
        
        # Initialize TTS
        logger.info("📢 Initializing TTS...")
        initialize_tts("local", REFERENCE_AUDIO)
        
        # Initialize avatar generator with default settings first
        logger.info("🎬 Initializing Avatar Generator (baseline)...")
        self.avatar_gen = AvatarGenerator(
            device="cuda:1",
            size=256,  # Start with baseline
            preload=True
        )
        
        logger.info("✅ Services initialized!")
        
    async def test_baseline(self, question: str) -> Dict:
        """Test with current settings (baseline)"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 BASELINE TEST: {question}")
        logger.info(f"{'='*80}")
        
        start_time = time.time()
        metrics = {
            'question': question,
            'config': 'baseline_256px_25fps',
            'chunks': [],
            'total_time': 0,
            'first_chunk_time': 0,
            'avg_chunk_time': 0,
            'gaps': []
        }
        
        # Stream LLM response
        logger.info("🤖 Getting LLM response...")
        llm_start = time.time()
        full_response = ""
        chunks = []
        
        async for chunk in self.llm_stream(question):
            full_response += chunk
            # Split into sentences for chunking
            if chunk.endswith(('.', '!', '?', ':')):
                chunks.append(full_response)
                full_response = ""
        
        if full_response:
            chunks.append(full_response)
            
        llm_time = time.time() - llm_start
        logger.info(f"✅ LLM response: {len(chunks)} chunks in {llm_time:.2f}s")
        
        # Process each chunk
        last_chunk_end = time.time()
        
        for i, chunk_text in enumerate(chunks[:3]):  # Test first 3 chunks
            chunk_start = time.time()
            logger.info(f"\n🎵 Processing chunk {i+1}/{len(chunks[:3])}")
            logger.info(f"   Text: {chunk_text[:80]}...")
            
            # Generate TTS
            tts_start = time.time()
            audio_path = await self.tts_gen(chunk_text)
            tts_time = time.time() - tts_start
            logger.info(f"   ⏱️  TTS: {tts_time:.2f}s")
            
            if not audio_path or not os.path.exists(audio_path):
                logger.error(f"   ❌ TTS failed for chunk {i+1}")
                continue
                
            # Generate avatar
            avatar_start = time.time()
            video_path = await asyncio.to_thread(
                self.avatar_gen.generate_video,
                audio_path,
                REFERENCE_IMAGE
            )
            avatar_time = time.time() - avatar_start
            logger.info(f"   ⏱️  Avatar: {avatar_time:.2f}s")
            
            chunk_total = time.time() - chunk_start
            gap = chunk_start - last_chunk_end
            
            metrics['chunks'].append({
                'index': i,
                'tts_time': tts_time,
                'avatar_time': avatar_time,
                'total_time': chunk_total,
                'gap': gap
            })
            
            if i == 0:
                metrics['first_chunk_time'] = chunk_total
                
            metrics['gaps'].append(gap)
            last_chunk_end = time.time()
            
            logger.info(f"   ✅ Chunk {i+1} complete: {chunk_total:.2f}s (gap: {gap:.2f}s)")
        
        metrics['total_time'] = time.time() - start_time
        metrics['avg_chunk_time'] = sum(c['total_time'] for c in metrics['chunks']) / len(metrics['chunks'])
        metrics['avg_gap'] = sum(metrics['gaps']) / len(metrics['gaps']) if metrics['gaps'] else 0
        
        logger.info(f"\n📊 BASELINE RESULTS:")
        logger.info(f"   Total time: {metrics['total_time']:.2f}s")
        logger.info(f"   First chunk: {metrics['first_chunk_time']:.2f}s")
        logger.info(f"   Avg chunk: {metrics['avg_chunk_time']:.2f}s")
        logger.info(f"   Avg gap: {metrics['avg_gap']:.2f}s")
        
        self.baseline_time = metrics['first_chunk_time']
        self.results.append(metrics)
        return metrics
    
    async def test_optimized(self, question: str, config: Dict) -> Dict:
        """Test with optimized settings"""
        logger.info(f"\n{'='*80}")
        logger.info(f"⚡ OPTIMIZED TEST: {config['name']}")
        logger.info(f"   Settings: {config['size']}px, {config['fps']}fps")
        logger.info(f"{'='*80}")
        
        # Reinitialize avatar generator with new settings
        logger.info("🔄 Reinitializing avatar generator...")
        self.avatar_gen = AvatarGenerator(
            device="cuda:1",
            size=config['size'],
            preload=True
        )
        
        start_time = time.time()
        metrics = {
            'question': question,
            'config': config['name'],
            'settings': config,
            'chunks': [],
            'total_time': 0,
            'first_chunk_time': 0,
            'avg_chunk_time': 0,
            'gaps': []
        }
        
        # Stream LLM response
        logger.info("🤖 Getting LLM response...")
        full_response = ""
        chunks = []
        
        async for chunk in self.llm_stream(question):
            full_response += chunk
            if chunk.endswith(('.', '!', '?', ':')):
                chunks.append(full_response)
                full_response = ""
        
        if full_response:
            chunks.append(full_response)
        
        logger.info(f"✅ LLM response: {len(chunks)} chunks")
        
        # Process chunks
        last_chunk_end = time.time()
        
        for i, chunk_text in enumerate(chunks[:3]):
            chunk_start = time.time()
            logger.info(f"\n🎵 Processing chunk {i+1}/{len(chunks[:3])}")
            
            # TTS
            tts_start = time.time()
            audio_path = await self.tts_gen(chunk_text)
            tts_time = time.time() - tts_start
            logger.info(f"   ⏱️  TTS: {tts_time:.2f}s")
            
            if not audio_path or not os.path.exists(audio_path):
                logger.error(f"   ❌ TTS failed for chunk {i+1}")
                continue
            
            # Avatar with optimized settings
            avatar_start = time.time()
            video_path = await asyncio.to_thread(
                self.avatar_gen.generate_video,
                audio_path,
                REFERENCE_IMAGE
            )
            avatar_time = time.time() - avatar_start
            logger.info(f"   ⏱️  Avatar: {avatar_time:.2f}s")
            
            chunk_total = time.time() - chunk_start
            gap = chunk_start - last_chunk_end
            
            metrics['chunks'].append({
                'index': i,
                'tts_time': tts_time,
                'avatar_time': avatar_time,
                'total_time': chunk_total,
                'gap': gap
            })
            
            if i == 0:
                metrics['first_chunk_time'] = chunk_total
            
            metrics['gaps'].append(gap)
            last_chunk_end = time.time()
            
            improvement = ((self.baseline_time - chunk_total) / self.baseline_time * 100) if self.baseline_time else 0
            logger.info(f"   ✅ Chunk {i+1}: {chunk_total:.2f}s (gap: {gap:.2f}s) [Improvement: {improvement:+.1f}%]")
        
        metrics['total_time'] = time.time() - start_time
        metrics['avg_chunk_time'] = sum(c['total_time'] for c in metrics['chunks']) / len(metrics['chunks'])
        metrics['avg_gap'] = sum(metrics['gaps']) / len(metrics['gaps']) if metrics['gaps'] else 0
        
        improvement = ((self.baseline_time - metrics['first_chunk_time']) / self.baseline_time * 100) if self.baseline_time else 0
        
        logger.info(f"\n📊 OPTIMIZED RESULTS:")
        logger.info(f"   Total time: {metrics['total_time']:.2f}s")
        logger.info(f"   First chunk: {metrics['first_chunk_time']:.2f}s")
        logger.info(f"   Avg chunk: {metrics['avg_chunk_time']:.2f}s")
        logger.info(f"   Avg gap: {metrics['avg_gap']:.2f}s")
        logger.info(f"   🎯 Improvement: {improvement:+.1f}%")
        
        self.results.append(metrics)
        return metrics
    
    def print_summary(self):
        """Print summary of all tests"""
        logger.info(f"\n{'='*80}")
        logger.info("📋 OPTIMIZATION SUMMARY")
        logger.info(f"{'='*80}\n")
        
        for result in self.results:
            logger.info(f"Config: {result['config']}")
            logger.info(f"  First chunk: {result['first_chunk_time']:.2f}s")
            logger.info(f"  Avg chunk:   {result['avg_chunk_time']:.2f}s")
            logger.info(f"  Avg gap:     {result['avg_gap']:.2f}s")
            if self.baseline_time:
                improvement = ((self.baseline_time - result['first_chunk_time']) / self.baseline_time * 100)
                logger.info(f"  Improvement: {improvement:+.1f}%")
            logger.info("")
        
        # Save results
        results_file = "optimization_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"💾 Results saved to {results_file}")


async def main():
    """Main optimization pipeline"""
    logger.info("🚀 Avatar Pipeline Optimization Started")
    logger.info("="*80)
    
    tester = AvatarPipelineTester()
    
    # Initialize services
    await tester.initialize_services()
    
    # Test question
    question = TEST_QUESTIONS[0]
    
    # 1. Baseline test (256px, 25fps)
    await tester.test_baseline(question)
    
    # 2. Optimization levels
    optimizations = [
        {'name': 'opt_128px_25fps', 'size': 128, 'fps': 25},
        {'name': 'opt_128px_15fps', 'size': 128, 'fps': 15},
        {'name': 'opt_96px_15fps', 'size': 96, 'fps': 15},
        {'name': 'opt_64px_10fps', 'size': 64, 'fps': 10},
    ]
    
    for opt_config in optimizations:
        await tester.test_optimized(question, opt_config)
    
    # Print summary
    tester.print_summary()
    
    logger.info("\n✅ Optimization complete!")


if __name__ == "__main__":
    asyncio.run(main())

