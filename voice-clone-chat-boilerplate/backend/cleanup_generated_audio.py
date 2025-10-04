"""
Cleanup utility to remove old generated audio files.
Run this periodically or manually to free up disk space.
"""

import os
import time
from pathlib import Path

# Directory containing generated audio files
GENERATED_AUDIO_DIR = Path(__file__).parent / "audio" / "generated"

# Delete files older than this (in seconds)
MAX_AGE = 24 * 60 * 60  # 24 hours


def cleanup_old_files(max_age_seconds=MAX_AGE):
    """
    Remove generated audio files older than max_age_seconds.
    
    Args:
        max_age_seconds: Maximum age in seconds (default: 24 hours)
    """
    if not GENERATED_AUDIO_DIR.exists():
        print(f"Directory not found: {GENERATED_AUDIO_DIR}")
        return
    
    current_time = time.time()
    deleted_count = 0
    freed_space = 0
    
    print(f"Scanning: {GENERATED_AUDIO_DIR}")
    print(f"Removing files older than {max_age_seconds / 3600:.1f} hours...")
    
    for file_path in GENERATED_AUDIO_DIR.glob("voice_*.wav"):
        try:
            # Check file age
            file_age = current_time - os.path.getmtime(file_path)
            
            if file_age > max_age_seconds:
                file_size = os.path.getsize(file_path)
                os.unlink(file_path)
                deleted_count += 1
                freed_space += file_size
                print(f"  Deleted: {file_path.name} (age: {file_age / 3600:.1f}h)")
        
        except Exception as e:
            print(f"  Error deleting {file_path.name}: {e}")
    
    if deleted_count > 0:
        print(f"\n✅ Cleanup complete!")
        print(f"   Files deleted: {deleted_count}")
        print(f"   Space freed: {freed_space / 1024 / 1024:.2f} MB")
    else:
        print("\n✅ No old files to clean up.")


def cleanup_all_files():
    """Remove ALL generated audio files (use with caution!)"""
    if not GENERATED_AUDIO_DIR.exists():
        print(f"Directory not found: {GENERATED_AUDIO_DIR}")
        return
    
    deleted_count = 0
    freed_space = 0
    
    print(f"⚠️  WARNING: Deleting ALL generated audio files from: {GENERATED_AUDIO_DIR}")
    
    for file_path in GENERATED_AUDIO_DIR.glob("voice_*.wav"):
        try:
            file_size = os.path.getsize(file_path)
            os.unlink(file_path)
            deleted_count += 1
            freed_space += file_size
            print(f"  Deleted: {file_path.name}")
        except Exception as e:
            print(f"  Error deleting {file_path.name}: {e}")
    
    if deleted_count > 0:
        print(f"\n✅ Cleanup complete!")
        print(f"   Files deleted: {deleted_count}")
        print(f"   Space freed: {freed_space / 1024 / 1024:.2f} MB")
    else:
        print("\n✅ No files to clean up.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Delete all files
        response = input("⚠️  Delete ALL generated audio files? (yes/no): ")
        if response.lower() == "yes":
            cleanup_all_files()
        else:
            print("Cancelled.")
    else:
        # Delete old files (default)
        cleanup_old_files()

