#!/usr/bin/env python3
"""
Test script to verify avatar model switching between SadTalker and Ditto.
Tests both models with the same reference image and audio.
"""

import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import avatar generator
from utils.avatar_generator import initialize_avatar_generator, generate_avatar, get_avatar_generator

async def test_avatar_model(model_name, reference_image, reference_audio, output_dir):
    """Test a specific avatar model."""
    
    logger.info("=" * 80)
    logger.info(f"🎬 Testing {model_name.upper()} Avatar Model")
    logger.info("=" * 80)
    
    # Set environment variable
    os.environ['AVATAR_MODEL'] = model_name
    
    try:
        # Initialize generator
        logger.info(f"Initializing {model_name} generator...")
        success = initialize_avatar_generator(
            device=None,  # Use AVATAR_DEVICE from env
            size=256,
            enhancer=None  # Disable face enhancement for faster testing
        )
        
        if not success:
            logger.error(f"❌ Failed to initialize {model_name}")
            return False
        
        generator = get_avatar_generator()
        if generator is None:
            logger.error(f"❌ Generator not available for {model_name}")
            return False
        
        logger.info(f"✅ {model_name} initialized successfully")
        logger.info(f"Generator type: {type(generator).__name__}")
        
        # Generate avatar video
        logger.info(f"Generating avatar video with {model_name}...")
        logger.info(f"  Reference Image: {reference_image}")
        logger.info(f"  Reference Audio: {reference_audio}")
        logger.info(f"  Output Directory: {output_dir}")
        
        import time
        start_time = time.time()
        
        video_path = await generate_avatar(
            audio_path=reference_audio,
            image_path=reference_image,
            output_dir=output_dir,
            fast_mode=True,
            preprocess='crop',
            pic_size=256,
            enable_enhancer=False  # Disable for faster testing
        )
        
        elapsed_time = time.time() - start_time
        
        if video_path and os.path.exists(video_path):
            file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
            logger.info("=" * 80)
            logger.info(f"✅ SUCCESS! {model_name.upper()} video generated!")
            logger.info(f"📹 Output: {video_path}")
            logger.info(f"📊 Size: {file_size:.2f} MB")
            logger.info(f"⏱️  Generation Time: {elapsed_time:.2f} seconds")
            logger.info("=" * 80)
            return True
        else:
            logger.error(f"❌ {model_name} video generation failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing {model_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    
    # Reference files
    reference_image = "Avatar/References/ref_1761131562372.jpg"
    reference_audio = "audio/reference_voices/ref_1761118578.wav"
    
    # Check if files exist
    if not os.path.exists(reference_image):
        logger.error(f"Reference image not found: {reference_image}")
        return
    
    if not os.path.exists(reference_audio):
        logger.error(f"Reference audio not found: {reference_audio}")
        return
    
    logger.info("╔═══════════════════════════════════════════════════════════╗")
    logger.info("║      AVATAR MODEL SWITCHING TEST                         ║")
    logger.info("╚═══════════════════════════════════════════════════════════╝")
    logger.info("")
    logger.info(f"Reference Image: {reference_image}")
    logger.info(f"Reference Audio: {reference_audio}")
    logger.info("")
    
    # Test both models
    results = {}
    
    # Test 1: SadTalker
    output_dir_sadtalker = "outputs/test_sadtalker"
    os.makedirs(output_dir_sadtalker, exist_ok=True)
    results['sadtalker'] = await test_avatar_model(
        'sadtalker',
        reference_image,
        reference_audio,
        output_dir_sadtalker
    )
    
    # Clear generator between tests
    import importlib
    import utils.avatar_generator as av_gen
    av_gen._avatar_generator = None
    
    print("\n" + "="*80 + "\n")
    
    # Test 2: Ditto
    output_dir_ditto = "outputs/test_ditto"
    os.makedirs(output_dir_ditto, exist_ok=True)
    results['ditto'] = await test_avatar_model(
        'ditto',
        reference_image,
        reference_audio,
        output_dir_ditto
    )
    
    # Final summary
    logger.info("")
    logger.info("╔═══════════════════════════════════════════════════════════╗")
    logger.info("║      TEST RESULTS SUMMARY                                 ║")
    logger.info("╚═══════════════════════════════════════════════════════════╝")
    logger.info("")
    logger.info(f"SadTalker: {'✅ PASSED' if results['sadtalker'] else '❌ FAILED'}")
    logger.info(f"Ditto:     {'✅ PASSED' if results['ditto'] else '❌ FAILED'}")
    logger.info("")
    
    if all(results.values()):
        logger.info("🎉 ALL TESTS PASSED! Both avatar models work correctly.")
        logger.info("")
        logger.info("🔄 To switch models, set AVATAR_MODEL in .env:")
        logger.info("   AVATAR_MODEL=sadtalker  # Use SadTalker")
        logger.info("   AVATAR_MODEL=ditto      # Use Ditto-TalkingHead")
    else:
        logger.error("⚠️ Some tests failed. Check logs above for details.")
    
    logger.info("")
    logger.info("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

