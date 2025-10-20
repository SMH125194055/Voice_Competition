#!/usr/bin/env python3
"""
Quick Avatar Optimization Test
Tests different resolution/quality settings to find optimal speed
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test files
AUDIO_FILE = "audio/Nafay_Org.mp3"  # Use existing audio for quick test
IMAGE_FILE = "audio/Huzaifa.jpg"

async def test_avatar_generation(size: int, label: str):
    """Test avatar generation with specific size"""
    from utils.avatar_generator import initialize_avatar_generator, generate_avatar
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing: {label} (size={size}px)")
    logger.info(f"{'='*80}")
    
    try:
        # Initialize generator with specific size
        init_start = time.time()
        initialize_avatar_generator(
            device="cuda:1",
            size=size,
            enhancer=None,  # Disable enhancer for speed
            pool_size=1  # Single instance for testing
        )
        init_time = time.time() - init_start
        logger.info(f"✅ Initialization: {init_time:.2f}s")
        
        # Generate video
        gen_start = time.time()
        video_path = await generate_avatar(
            AUDIO_FILE,
            IMAGE_FILE,
            fast_mode=False
        )
        gen_time = time.time() - gen_start
        
        total_time = time.time() - init_start
        
        # Check if video was created
        if video_path and os.path.exists(video_path):
            video_size = os.path.getsize(video_path) / 1024 / 1024  # MB
            logger.info(f"✅ Video generated: {video_path}")
            logger.info(f"   File size: {video_size:.2f} MB")
            logger.info(f"   Generation time: {gen_time:.2f}s")
            logger.info(f"   Total time: {total_time:.2f}s")
            return {
                'label': label,
                'size': size,
                'init_time': init_time,
                'gen_time': gen_time,
                'total_time': total_time,
                'video_size_mb': video_size,
                'success': True
            }
        else:
            logger.error(f"❌ Video generation failed")
            return {
                'label': label,
                'size': size,
                'success': False
            }
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'label': label,
            'size': size,
            'success': False,
            'error': str(e)
        }

async def main():
    logger.info("🚀 Avatar Optimization Test Started")
    logger.info("="*80)
    
    # Test configurations - progressively lower quality
    configs = [
        (256, "Baseline (256px - Current)"),
        (128, "Optimized 1 (128px)"),
        (96, "Optimized 2 (96px - SadTalker default)"),
        (64, "Optimized 3 (64px - Fastest)"),
    ]
    
    results = []
    baseline_time = None
    
    for size, label in configs:
        result = await test_avatar_generation(size, label)
        results.append(result)
        
        if result.get('success') and baseline_time is None:
            baseline_time = result['gen_time']
        
        # Calculate improvement
        if result.get('success') and baseline_time:
            improvement = ((baseline_time - result['gen_time']) / baseline_time) * 100
            logger.info(f"🎯 Improvement vs baseline: {improvement:+.1f}%")
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Print summary
    logger.info(f"\n{'='*80}")
    logger.info("📊 OPTIMIZATION SUMMARY")
    logger.info(f"{'='*80}\n")
    
    for result in results:
        if result.get('success'):
            improvement = ((baseline_time - result['gen_time']) / baseline_time) * 100 if baseline_time else 0
            logger.info(f"{result['label']}:")
            logger.info(f"  Generation: {result['gen_time']:.2f}s")
            logger.info(f"  File size:  {result['video_size_mb']:.2f} MB")
            logger.info(f"  Improvement: {improvement:+.1f}%")
        else:
            logger.info(f"{result['label']}: FAILED")
        logger.info("")
    
    logger.info("✅ Optimization test complete!")

if __name__ == "__main__":
    asyncio.run(main())

