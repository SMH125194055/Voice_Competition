#!/usr/bin/env python3
"""
Simple test for ChatterBox and SadTalker functionality.
"""

import os
import sys
import logging
import asyncio

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_chatterbox():
    """Test ChatterBox TTS."""
    try:
        from utils.tts import initialize_tts, text_to_speech
        
        logger.info("Testing ChatterBox TTS...")
        
        # Initialize TTS
        initialize_tts('local', 'audio/Nafay_Org.mp3')
        
        # Check if TTS model was initialized
        from utils.tts import tts_model
        if not tts_model:
            logger.error("Failed to initialize ChatterBox TTS")
            return False
        
        logger.info("✅ ChatterBox TTS initialized successfully")
        
        # Test speech generation
        test_text = "Hello, this is a test of the voice cloning system."
        logger.info(f"Generating speech for: '{test_text}'")
        
        # Generate speech
        audio_path = await text_to_speech(test_text, 'local', 'audio/Nafay_Org.mp3')
        if audio_path and os.path.exists(audio_path):
            logger.info(f"✅ Speech generated successfully: {audio_path}")
            return True
        else:
            logger.error("❌ Failed to generate speech")
            return False
            
    except Exception as e:
        logger.error(f"❌ ChatterBox TTS test failed: {e}")
        return False

async def test_sadtalker():
    """Test SadTalker avatar generation."""
    try:
        from utils.avatar_generator import initialize_avatar_generator, generate_avatar
        
        logger.info("Testing SadTalker avatar generation...")
        
        # Initialize avatar generator
        avatar_generator = initialize_avatar_generator()
        if not avatar_generator:
            logger.error("❌ Failed to initialize SadTalker avatar generator")
            return False
        
        logger.info("✅ SadTalker avatar generator initialized successfully")
        
        # Test avatar generation
        source_image = "audio/Huzaifa.jpg"
        driving_audio = "audio/Nafay_Org.mp3"
        
        if not os.path.exists(source_image):
            logger.error(f"❌ Source image not found: {source_image}")
            return False
            
        if not os.path.exists(driving_audio):
            logger.error(f"❌ Driving audio not found: {driving_audio}")
            return False
        
        logger.info(f"Generating avatar video with image: {source_image} and audio: {driving_audio}")
        
        # Generate avatar video
        video_path = await generate_avatar(source_image, driving_audio, avatar_generator)
        if video_path and os.path.exists(video_path):
            logger.info(f"✅ Avatar video generated successfully: {video_path}")
            return True
        else:
            logger.error("❌ Failed to generate avatar video")
            return False
            
    except Exception as e:
        logger.error(f"❌ SadTalker avatar test failed: {e}")
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Starting simple test...")
    
    # Test ChatterBox
    logger.info("=" * 50)
    logger.info("Testing ChatterBox TTS...")
    tts_success = await test_chatterbox()
    
    # Test SadTalker
    logger.info("=" * 50)
    logger.info("Testing SadTalker Avatar...")
    avatar_success = await test_sadtalker()
    
    # Results
    logger.info("=" * 50)
    logger.info("Test Results:")
    logger.info(f"ChatterBox TTS: {'✅ PASS' if tts_success else '❌ FAIL'}")
    logger.info(f"SadTalker Avatar: {'✅ PASS' if avatar_success else '❌ FAIL'}")
    
    if tts_success and avatar_success:
        logger.info("🎉 All tests passed! The system is ready for use.")
    else:
        logger.error("⚠️ Some tests failed. Please check the logs above.")
    
    return tts_success and avatar_success

if __name__ == "__main__":
    asyncio.run(main())
