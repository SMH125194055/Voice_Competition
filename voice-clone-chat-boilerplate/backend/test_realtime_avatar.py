#!/usr/bin/env python3
"""
Real-time Avatar Generation Test
Progressive optimization to achieve near-realtime performance

Strategy:
1. Disable face enhancer (GFPGAN) - saves 2-3 seconds
2. Use still mode (less head movement) - faster inference
3. Reduce preprocessing quality
4. Test with actual question pipeline
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test question
TEST_QUESTION = "What are the pros and cons of living in America?"

# Reference files
AUDIO_REF = "audio/Nafay_Org.mp3"
IMAGE_REF = "audio/Huzaifa.jpg"

async def test_full_pipeline():
    """Test the complete pipeline: STT -> LLM -> TTS -> Avatar"""
    from utils.tts import initialize_tts, text_to_speech
    from utils.llm import chat_with_llm_streaming
    from utils.avatar_generator import initialize_avatar_generator, generate_avatar
    
    logger.info("🚀 REALTIME AVATAR PIPELINE TEST")
    logger.info("="*80)
    logger.info(f"Question: {TEST_QUESTION}")
    logger.info("="*80)
    
    # Initialize services
    logger.info("\n📢 Initializing TTS...")
    tts_start = time.time()
    initialize_tts("local", AUDIO_REF)
    logger.info(f"✅ TTS initialized in {time.time() - tts_start:.2f}s")
    
    logger.info("\n🎬 Initializing Avatar Generator (NO ENHANCER for speed)...")
    avatar_start = time.time()
    initialize_avatar_generator(
        device="cuda:1",
        size=256,
        enhancer=None,  # 🚀 SPEED: Disable enhancer
        pool_size=1
    )
    logger.info(f"✅ Avatar initialized in {time.time() - avatar_start:.2f}s")
    
    # Get LLM response (simulated for testing)
    logger.info("\n🤖 Using simulated LLM response...")
    llm_start = time.time()
    
    # Simulated response about pros and cons of living in America
    full_response = (
        "Living in America has several advantages. First, there are many economic opportunities and career growth potential. "
        "The country has a strong economy with diverse industries. Second, America offers high quality education and research facilities. "
        "However, there are also disadvantages to consider. Healthcare costs can be very expensive compared to other countries. "
        "Income inequality is a significant issue in many regions. Additionally, work-life balance can be challenging with long working hours."
    )
    
    # Split into chunks of ~15 words
    words = full_response.split()
    chunks = []
    for i in range(0, len(words), 15):
        chunk = " ".join(words[i:i+15])
        chunks.append(chunk)
        logger.info(f"  📦 Chunk {len(chunks)}: {chunk[:60]}...")
    
    llm_time = time.time() - llm_start
    logger.info(f"✅ LLM simulation complete: {len(chunks)} chunks in {llm_time:.2f}s")
    logger.info(f"   Full response: {full_response[:200]}...")
    
    # Process first 3 chunks to measure timing
    logger.info(f"\n🎭 Processing first 3 chunks...")
    logger.info("="*80)
    
    chunk_metrics = []
    last_chunk_end = time.time()
    
    for i, text in enumerate(chunks[:3]):
        chunk_start = time.time()
        gap_from_last = chunk_start - last_chunk_end
        
        logger.info(f"\n📊 CHUNK {i+1}/3")
        logger.info(f"   Text: {text[:80]}...")
        logger.info(f"   Gap from last: {gap_from_last:.2f}s")
        
        # Generate TTS
        tts_chunk_start = time.time()
        audio_path = await text_to_speech(text, mode="local", reference_audio_path=AUDIO_REF)
        tts_time = time.time() - tts_chunk_start
        logger.info(f"   🎵 TTS: {tts_time:.2f}s -> {audio_path}")
        
        if not audio_path or not os.path.exists(audio_path):
            logger.error(f"   ❌ TTS failed!")
            continue
        
        # Generate avatar (NO ENHANCER)
        avatar_chunk_start = time.time()
        video_path = await generate_avatar(
            audio_path,
            IMAGE_REF,
            output_dir="avatar_outputs",
            fast_mode=False
        )
        avatar_time = time.time() - avatar_chunk_start
        logger.info(f"   🎬 Avatar: {avatar_time:.2f}s -> {video_path}")
        
        chunk_total = time.time() - chunk_start
        
        metrics = {
            'chunk_num': i + 1,
            'text_length': len(text),
            'tts_time': tts_time,
            'avatar_time': avatar_time,
            'total_time': chunk_total,
            'gap': gap_from_last
        }
        chunk_metrics.append(metrics)
        
        logger.info(f"   ✅ TOTAL: {chunk_total:.2f}s (TTS: {tts_time:.2f}s + Avatar: {avatar_time:.2f}s)")
        
        last_chunk_end = time.time()
    
    # Print summary
    logger.info(f"\n{'='*80}")
    logger.info("📊 PIPELINE PERFORMANCE SUMMARY")
    logger.info(f"{'='*80}\n")
    
    for m in chunk_metrics:
        logger.info(f"Chunk {m['chunk_num']}:")
        logger.info(f"  TTS:        {m['tts_time']:.2f}s")
        logger.info(f"  Avatar:     {m['avatar_time']:.2f}s")
        logger.info(f"  Total:      {m['total_time']:.2f}s")
        logger.info(f"  Gap:        {m['gap']:.2f}s")
        logger.info("")
    
    avg_total = sum(m['total_time'] for m in chunk_metrics) / len(chunk_metrics)
    avg_avatar = sum(m['avatar_time'] for m in chunk_metrics) / len(chunk_metrics)
    avg_gap = sum(m['gap'] for m in chunk_metrics[1:]) / len(chunk_metrics[1:]) if len(chunk_metrics) > 1 else 0
    
    logger.info(f"AVERAGES:")
    logger.info(f"  Total per chunk: {avg_total:.2f}s")
    logger.info(f"  Avatar time:     {avg_avatar:.2f}s")
    logger.info(f"  Gap between:     {avg_gap:.2f}s")
    logger.info("")
    
    # Calculate if we're near realtime
    first_chunk_time = chunk_metrics[0]['total_time']
    logger.info(f"🎯 REALTIME ANALYSIS:")
    logger.info(f"   First chunk ready: {first_chunk_time:.2f}s")
    
    if first_chunk_time < 3.0:
        logger.info(f"   ✅ EXCELLENT! Near realtime (<3s)")
    elif first_chunk_time < 5.0:
        logger.info(f"   ✅ GOOD! Acceptable for production (<5s)")
    elif first_chunk_time < 10.0:
        logger.info(f"   ⚠️  MODERATE. Could be improved (<10s)")
    else:
        logger.info(f"   ❌ SLOW. Needs optimization (>{first_chunk_time:.1f}s)")
    
    logger.info(f"\n✅ Pipeline test complete!")

async def main():
    await test_full_pipeline()

if __name__ == "__main__":
    asyncio.run(main())

