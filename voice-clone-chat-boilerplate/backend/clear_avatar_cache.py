#!/usr/bin/env python3
"""
Clear SadTalker avatar cache to force new cropping with shoulders.
This script clears all cached preprocessed images.
"""

import os
import shutil
import sys
import glob

def clear_avatar_cache():
    """Clear all SadTalker cache directories."""
    
    print("🧹 Clearing SadTalker avatar cache...")
    
    # Get backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Cache directories to clear
    cache_dirs = [
        # SadTalker cache directories
        os.path.join(backend_dir, 'Avatar', 'SadTalker', 'checkpoints'),
        os.path.join(backend_dir, 'Avatar', 'SadTalker', 'src', 'config'),
        
        # Output directories
        os.path.join(backend_dir, 'outputs'),
        os.path.join(backend_dir, 'outputs', 'idle_animations'),
        
        # Reference picture cache
        os.path.join(backend_dir, 'Avatar', 'References'),
        
        # Any temp directories
        os.path.join(backend_dir, 'temp'),
        os.path.join(backend_dir, 'tmp'),
    ]
    
    # Clear each directory
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                # Remove all files in directory
                for file_path in glob.glob(os.path.join(cache_dir, '*')):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"  ✅ Removed file: {os.path.basename(file_path)}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        print(f"  ✅ Removed directory: {os.path.basename(file_path)}")
                
                print(f"  🧹 Cleared: {cache_dir}")
            except Exception as e:
                print(f"  ⚠️  Could not clear {cache_dir}: {e}")
        else:
            print(f"  ℹ️  Directory not found: {cache_dir}")
    
    # Clear Python cache
    print("\n🐍 Clearing Python cache...")
    for root, dirs, files in os.walk(backend_dir):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                pycache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(pycache_path)
                    print(f"  ✅ Removed: {pycache_path}")
                except Exception as e:
                    print(f"  ⚠️  Could not remove {pycache_path}: {e}")
    
    print("\n✅ Avatar cache cleared!")
    print("🔄 Please restart the backend to apply new cropping settings.")
    print("📸 Re-upload your reference picture to force new preprocessing.")

if __name__ == "__main__":
    clear_avatar_cache()


