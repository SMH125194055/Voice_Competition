"""
Reference picture management for avatar generation.
"""

import os
import logging
import tempfile
import shutil
from typing import List, Optional, Dict
from PIL import Image

logger = logging.getLogger(__name__)

# Reference picture directory
REFERENCE_PICTURE_DIR = None

def initialize_reference_picture_dir(base_dir: str = None):
    """
    Initialize reference picture directory.
    
    Args:
        base_dir: Base directory for backend (default: auto-detect)
    """
    global REFERENCE_PICTURE_DIR
    
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(__file__))
    
    REFERENCE_PICTURE_DIR = os.path.join(base_dir, 'Avatar', 'References')
    os.makedirs(REFERENCE_PICTURE_DIR, exist_ok=True)
    
    logger.info(f"📁 Reference picture directory: {REFERENCE_PICTURE_DIR}")


def get_reference_picture_dir() -> str:
    """Get reference picture directory."""
    if REFERENCE_PICTURE_DIR is None:
        initialize_reference_picture_dir()
    return REFERENCE_PICTURE_DIR


def validate_image(image_path: str) -> bool:
    """
    Validate if image is suitable for avatar generation.
    
    Args:
        image_path: Path to image file
        
    Returns:
        True if valid, False otherwise
    """
    try:
        img = Image.open(image_path)
        
        # Check format
        if img.format not in ['JPEG', 'PNG', 'JPG']:
            logger.warning(f"Invalid format: {img.format}")
            return False
        
        # Check size (should be at least 256x256)
        width, height = img.size
        if width < 256 or height < 256:
            logger.warning(f"Image too small: {width}x{height}")
            return False
        
        # Check if image has face (basic check - has reasonable aspect ratio)
        # Allow wider range for portrait/landscape images
        aspect_ratio = width / height
        if aspect_ratio < 0.3 or aspect_ratio > 3.0:
            logger.warning(f"Unusual aspect ratio: {aspect_ratio}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Image validation error: {e}")
        return False


def save_reference_picture(
    temp_path: str,
    reference_id: str,
    optimize: bool = True
) -> Optional[str]:
    """
    Save reference picture to reference directory.
    
    Args:
        temp_path: Temporary file path
        reference_id: Unique ID for reference
        optimize: Whether to optimize image (resize if too large)
        
    Returns:
        Path to saved reference picture, or None if failed
    """
    try:
        ref_dir = get_reference_picture_dir()
        ref_path = os.path.join(ref_dir, f"{reference_id}.jpg")
        
        if optimize:
            # Optimize image for faster processing
            img = Image.open(temp_path)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large (max 1024x1024 for balance of quality/speed)
            max_size = 1024
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                logger.info(f"Resized image to {img.size}")
            
            # Save with optimization
            img.save(ref_path, 'JPEG', quality=90, optimize=True)
            logger.info(f"✅ Saved optimized reference picture: {ref_path}")
        else:
            # Just copy the file
            shutil.copy2(temp_path, ref_path)
            logger.info(f"✅ Saved reference picture: {ref_path}")
        
        return ref_path
        
    except Exception as e:
        logger.error(f"Failed to save reference picture: {e}")
        return None


def list_reference_pictures() -> List[Dict]:
    """
    List all available reference pictures.
    
    Returns:
        List of reference picture info dicts
    """
    try:
        ref_dir = get_reference_picture_dir()
        pictures = []
        
        for filename in os.listdir(ref_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(ref_dir, filename)
                
                # Get image info
                try:
                    img = Image.open(filepath)
                    width, height = img.size
                except:
                    width, height = 0, 0
                
                pictures.append({
                    'id': os.path.splitext(filename)[0],
                    'filename': filename,
                    'path': filepath,
                    'size': os.path.getsize(filepath),
                    'width': width,
                    'height': height
                })
        
        return pictures
        
    except Exception as e:
        logger.error(f"Failed to list reference pictures: {e}")
        return []


def get_reference_picture_path(reference_id: str) -> Optional[str]:
    """
    Get path to reference picture by ID.
    
    Args:
        reference_id: Reference picture ID
        
    Returns:
        Path to picture, or None if not found
    """
    ref_dir = get_reference_picture_dir()
    
    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
        filepath = os.path.join(ref_dir, f"{reference_id}{ext}")
        if os.path.exists(filepath):
            return filepath
    
    return None


def delete_reference_picture(reference_id: str) -> bool:
    """
    Delete reference picture by ID.
    
    Args:
        reference_id: Reference picture ID
        
    Returns:
        True if deleted, False if not found
    """
    try:
        ref_dir = get_reference_picture_dir()
        
        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
            filepath = os.path.join(ref_dir, f"{reference_id}{ext}")
            if os.path.exists(filepath):
                os.unlink(filepath)
                logger.info(f"🗑️ Deleted reference picture: {filepath}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to delete reference picture: {e}")
        return False


# Initialize on import
initialize_reference_picture_dir()


