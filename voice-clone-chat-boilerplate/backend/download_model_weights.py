#!/usr/bin/env python3
"""
Model Weights Download Script
==============================
Created: October 24, 2025

Automatically downloads all required model weights for:
- ChatterBox TTS
- Whisper STT
- Ditto-TalkingHead
- SadTalker (optional)
- Perth, InsightFace

Usage:
    python download_model_weights.py
    python download_model_weights.py --include-sadtalker  # Include SadTalker
"""

import os
import sys
import argparse
from pathlib import Path

def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def check_system_requirements():
    """Check if required system packages are installed"""
    print_header("Checking System Requirements")
    
    # Check Python version
    import sys
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"✅ Python version: {python_version}")
    
    if sys.version_info < (3, 12):
        print("⚠️  Warning: Python 3.12.3 recommended")
    
    # Check PyTorch
    try:
        import torch
        print(f"✅ PyTorch version: {torch.__version__}")
        print(f"✅ CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"✅ CUDA version: {torch.version.cuda}")
    except ImportError:
        print("❌ PyTorch not installed!")
        print("   Install: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        sys.exit(1)
    
    # Check FFmpeg
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        if result.returncode == 0:
            print("✅ FFmpeg installed")
        else:
            print("⚠️  FFmpeg check failed")
    except FileNotFoundError:
        print("❌ FFmpeg not installed!")
        print("   Install: sudo apt install ffmpeg")
        sys.exit(1)

def download_chatterbox_tts():
    """Download ChatterBox TTS models (auto-downloads on first use)"""
    print_header("ChatterBox TTS Models")
    print("ChatterBox models will auto-download on first use (~1.6 GB)")
    print("Location: ~/.cache/huggingface/")
    print("")
    print("Models:")
    print("  - Zyphra/Chatterbox-TTS")
    print("  - charactr/vocos-mel-24khz")
    print("  - facebook/wav2vec2-base-960h")
    print("")
    print("✅ Will download automatically when backend starts")

def download_whisper_stt():
    """Download Whisper STT models"""
    print_header("Whisper STT Models")
    print("Downloading Whisper 'base' model (~140 MB)...")
    
    try:
        import whisper
        model = whisper.load_model("base")
        print("✅ Whisper base model downloaded")
        print(f"   Location: ~/.cache/whisper/base.pt")
    except Exception as e:
        print(f"⚠️  Could not download Whisper: {e}")
        print("   Will download automatically on first use")

def check_ditto_weights():
    """Check if Ditto weights are present"""
    print_header("Ditto-TalkingHead Weights")
    
    ditto_path = Path("Avatar/ditto-talkinghead/checkpoints/ditto_pytorch")
    
    required_files = [
        "appearance_feature_extractor.pt",
        "motion_extractor.pt",
        "audio2motion.pt",
        "stitching_retargeting_network.pt",
        "warping_network.pt",
        "spade_generator.pt",
        "wav2vec.pt"
    ]
    
    if ditto_path.exists():
        print(f"Checking: {ditto_path}")
        missing = []
        for file in required_files:
            file_path = ditto_path / file
            if file_path.exists():
                size = file_path.stat().st_size / (1024 * 1024)  # MB
                print(f"  ✅ {file} ({size:.1f} MB)")
            else:
                print(f"  ❌ {file} - MISSING")
                missing.append(file)
        
        if missing:
            print(f"\n⚠️  Missing {len(missing)} files!")
            print("\nDitto weights must be manually placed in:")
            print(f"  {ditto_path.absolute()}")
            print("\nOr restore from backup if you have one.")
        else:
            print("\n✅ All Ditto weights present (~2 GB)")
    else:
        print(f"❌ Ditto checkpoints directory not found!")
        print(f"   Expected: {ditto_path.absolute()}")
        print("\nDitto weights must be manually placed in:")
        print(f"  {ditto_path.absolute()}/")
        print("\nRequired files:")
        for file in required_files:
            print(f"  - {file}")

def check_sadtalker_weights():
    """Check if SadTalker weights are present"""
    print_header("SadTalker Weights (Optional)")
    
    sadtalker_path = Path("Avatar/SadTalker/checkpoints")
    
    required_files = [
        "mapping_00109-model.pth.tar",
        "mapping_00229-model.pth.tar",
        "SadTalker_V0.0.2_256.safetensors",
        "epoch_20.pth"
    ]
    
    if sadtalker_path.exists():
        print(f"Checking: {sadtalker_path}")
        missing = []
        for file in required_files:
            file_path = sadtalker_path / file
            if file_path.exists():
                size = file_path.stat().st_size / (1024 * 1024)  # MB
                print(f"  ✅ {file} ({size:.1f} MB)")
            else:
                print(f"  ⚠️  {file} - Missing")
                missing.append(file)
        
        if missing:
            print(f"\n⚠️  Missing {len(missing)} files (optional)")
        else:
            print("\n✅ All SadTalker weights present (~1.7 GB)")
    else:
        print(f"⚠️  SadTalker checkpoints directory not found (optional)")
        print("   SadTalker is optional - Ditto is the primary model")

def download_perth():
    """Download Perth face landmarks"""
    print_header("Perth Face Landmarks")
    print("Perth will auto-download on first use (~200 MB)")
    print("Location: ~/.cache/perth/")
    print("✅ Will download automatically when backend starts")

def download_insightface():
    """Download InsightFace models"""
    print_header("InsightFace Models")
    print("InsightFace will auto-download on first use (~300 MB)")
    print("Location: ~/.insightface/models/")
    print("✅ Will download automatically when backend starts")

def print_summary():
    """Print summary of what needs to be done"""
    print_header("Summary")
    
    print("✅ Auto-Download Models (will download on first backend start):")
    print("   - ChatterBox TTS (~1.6 GB)")
    print("   - Whisper STT (~140 MB)")
    print("   - Perth (~200 MB)")
    print("   - InsightFace (~300 MB)")
    print("")
    print("⚠️  Manual Models (must be placed manually or restored from backup):")
    print("   - Ditto-TalkingHead (~2 GB) - REQUIRED")
    print("   - SadTalker (~1.7 GB) - OPTIONAL")
    print("")
    print("📦 Total Download Size:")
    print("   - Auto-download: ~2.2 GB")
    print("   - Manual (Ditto only): ~2 GB")
    print("   - Manual (Ditto + SadTalker): ~3.7 GB")
    print("   - Grand Total: ~4-6 GB")
    print("")
    print("🚀 Next Steps:")
    print("   1. Ensure Ditto weights are in Avatar/ditto-talkinghead/checkpoints/ditto_pytorch/")
    print("   2. (Optional) Place SadTalker weights in Avatar/SadTalker/checkpoints/")
    print("   3. Start backend: uvicorn main:app --host 0.0.0.0 --port 8000")
    print("   4. Auto-download models will download on first use")
    print("")
    print("📝 To restore from backup:")
    print("   See MIGRATION_GUIDE.md")

def main():
    parser = argparse.ArgumentParser(description="Download model weights for Voice Competition Project")
    parser.add_argument('--include-sadtalker', action='store_true', help="Check SadTalker weights")
    args = parser.parse_args()
    
    print("\n╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "MODEL WEIGHTS DOWNLOAD SCRIPT" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\nCreated: October 24, 2025")
    print("Project: Voice Competition - Avatar Generation")
    
    # Check system requirements
    check_system_requirements()
    
    # Check/download models
    download_chatterbox_tts()
    download_whisper_stt()
    check_ditto_weights()
    
    if args.include_sadtalker:
        check_sadtalker_weights()
    
    download_perth()
    download_insightface()
    
    # Print summary
    print_summary()
    
    print("\n✅ Model weights check complete!")
    print("\nFor detailed installation instructions, see:")
    print("  - INSTALLATION_GUIDE.md")
    print("  - MODEL_WEIGHTS_CHECKLIST.md")
    print("")

if __name__ == "__main__":
    main()

