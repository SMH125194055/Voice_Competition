#!/usr/bin/env python3
"""
Force clear ALL SadTalker and avatar caches to apply new shoulder cropping.
This script will clear both memory cache and file cache.
"""

import os
import shutil
import sys
import glob
import tempfile

def clear_all_caches():
    """Clear all possible cache locations."""
    
    print("🧹 FORCE CLEARING ALL AVATAR CACHES...")
    print("=" * 50)
    
    # Get backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Clear temp directories
    print("\n🗂️  Clearing temp directories...")
    temp_patterns = [
        '/tmp/sadtalker_cache_*',
        '/tmp/avatar_*',
        '/tmp/*sadtalker*',
        os.path.join(backend_dir, 'temp'),
        os.path.join(backend_dir, 'tmp'),
    ]
    
    for pattern in temp_patterns:
        for path in glob.glob(pattern):
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    print(f"  ✅ Removed file: {path}")
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    print(f"  ✅ Removed directory: {path}")
            except Exception as e:
                print(f"  ⚠️  Could not remove {path}: {e}")
    
    # 2. Clear outputs directory
    print("\n📁 Clearing outputs directory...")
    outputs_dir = os.path.join(backend_dir, 'outputs')
    if os.path.exists(outputs_dir):
        try:
            shutil.rmtree(outputs_dir)
            os.makedirs(outputs_dir, exist_ok=True)
            os.makedirs(os.path.join(outputs_dir, 'idle_animations'), exist_ok=True)
            print(f"  ✅ Cleared: {outputs_dir}")
        except Exception as e:
            print(f"  ⚠️  Could not clear outputs: {e}")
    
    # 3. Clear reference pictures (force re-upload)
    print("\n🖼️  Clearing reference pictures...")
    ref_dir = os.path.join(backend_dir, 'Avatar', 'References')
    if os.path.exists(ref_dir):
        for file_path in glob.glob(os.path.join(ref_dir, '*')):
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"  ✅ Removed: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"  ⚠️  Could not remove {file_path}: {e}")
    
    # 4. Clear Python cache
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
    
    # 5. Clear any SadTalker specific caches
    print("\n🎬 Clearing SadTalker caches...")
    sadtalker_dirs = [
        os.path.join(backend_dir, 'Avatar', 'SadTalker', 'checkpoints'),
        os.path.join(backend_dir, 'Avatar', 'SadTalker', 'src', 'config'),
    ]
    
    for cache_dir in sadtalker_dirs:
        if os.path.exists(cache_dir):
            # Only clear cache files, not model files
            for file_path in glob.glob(os.path.join(cache_dir, '*cache*')):
                try:
                    os.remove(file_path)
                    print(f"  ✅ Removed cache: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"  ⚠️  Could not remove {file_path}: {e}")
    
    print("\n" + "=" * 50)
    print("✅ ALL CACHES CLEARED!")
    print("\n📋 NEXT STEPS:")
    print("1. 🔄 Restart the backend server")
    print("2. 📸 Re-upload your reference picture")
    print("3. ✨ Generate new idle animation")
    print("4. 🎥 Start new conversation")
    print("\n🎯 Your avatar will now show FULL shoulders!")

if __name__ == "__main__":
    clear_all_caches()


