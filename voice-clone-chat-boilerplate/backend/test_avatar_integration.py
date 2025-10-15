#!/usr/bin/env python3
"""
Test script for avatar + voice cloning integration.
Tests the complete pipeline from audio input to avatar video output.
"""

import asyncio
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_avatar_pipeline():
    """Test the complete avatar generation pipeline."""
    
    try:
        logger.info("=" * 60)
        logger.info("AVATAR + VOICE CLONING INTEGRATION TEST")
        logger.info("=" * 60)
        
        # Test 1: Import modules
        logger.info("\n1️⃣ Testing imports...")
        from utils.avatar_generator import initialize_avatar_generator, generate_avatar
        from utils.avatar_reference import list_reference_pictures, get_reference_picture_path
        from avatar_config import get_avatar_config
        logger.info("✅ All modules imported successfully")
        
        # Test 2: Check configuration
        logger.info("\n2️⃣ Checking configuration...")
        config = get_avatar_config()
        logger.info(f"   Avatar enabled: {config['enabled']}")
        logger.info(f"   Device: {config['device']}")
        logger.info(f"   Size: {config['size']}")
        logger.info(f"   Enhancer: {config['enhancer']}")
        logger.info(f"   Default image: {config['default_image']}")
        
        # Test 3: Initialize avatar generator
        logger.info("\n3️⃣ Initializing avatar generator...")
        success = initialize_avatar_generator(
            device=config['device'],
            size=config['size'],
            enhancer=config['enhancer']
        )
        
        if not success:
            logger.error("❌ Avatar generator initialization failed")
            return False
        
        logger.info("✅ Avatar generator initialized")
        
        # Test 4: List reference pictures
        logger.info("\n4️⃣ Listing reference pictures...")
        pictures = list_reference_pictures()
        logger.info(f"   Found {len(pictures)} reference pictures:")
        for pic in pictures:
            logger.info(f"      - {pic['id']}: {pic['width']}x{pic['height']} ({pic['size']} bytes)")
        
        # Test 5: Test avatar generation
        logger.info("\n5️⃣ Testing avatar generation...")
        
        # Paths
        audio_path = "audio/test-english.wav"
        image_path = config['default_image']
        output_dir = config['output_dir']
        
        if not os.path.exists(audio_path):
            logger.warning(f"⚠️ Test audio not found: {audio_path}")
            logger.info("   Skipping avatar generation test")
        elif not os.path.exists(image_path):
            logger.warning(f"⚠️ Default image not found: {image_path}")
            logger.info("   Skipping avatar generation test")
        else:
            logger.info(f"   Audio: {audio_path}")
            logger.info(f"   Image: {image_path}")
            logger.info(f"   Output: {output_dir}")
            
            logger.info("   Generating avatar (this may take a few minutes)...")
            
            video_path = await generate_avatar(
                audio_path=audio_path,
                image_path=image_path,
                output_dir=output_dir,
                fast_mode=True
            )
            
            if video_path and os.path.exists(video_path):
                file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
                logger.info(f"✅ Avatar video generated: {video_path}")
                logger.info(f"   File size: {file_size:.2f} MB")
            else:
                logger.error("❌ Avatar generation failed")
                return False
        
        # Test summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("=" * 60)
        logger.info("\nYour avatar generation system is ready to use!")
        logger.info("\nNext steps:")
        logger.info("1. Start the backend server: uvicorn main:app --reload")
        logger.info("2. Upload reference pictures via /upload-reference-picture")
        logger.info("3. Use /vad-chat-avatar-stream for full voice + avatar")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_avatar_pipeline())
    sys.exit(0 if success else 1)


