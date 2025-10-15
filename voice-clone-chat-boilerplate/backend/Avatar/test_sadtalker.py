#!/usr/bin/env python3
"""
Test script to generate avatar video using SadTalker
"""
import os
import sys

# Add SadTalker to path
sadtalker_path = os.path.join(os.path.dirname(__file__), 'SadTalker')
sys.path.insert(0, sadtalker_path)

# Set paths
REFERENCE_IMAGE = os.path.join(os.path.dirname(__file__), 'References', 'Huzaifa.jpg')
AUDIO_FILE = os.path.join(os.path.dirname(__file__), '..', 'audio/reference_voices', 'ref_1760022239.wav')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 60)
print("SadTalker Avatar Generation Test")
print("=" * 60)
print(f"Reference Image: {REFERENCE_IMAGE}")
print(f"Audio File: {AUDIO_FILE}")
print(f"Output Directory: {OUTPUT_DIR}")
print("=" * 60)

# Check if files exist
if not os.path.exists(REFERENCE_IMAGE):
    print(f"ERROR: Reference image not found at {REFERENCE_IMAGE}")
    sys.exit(1)

if not os.path.exists(AUDIO_FILE):
    print(f"ERROR: Audio file not found at {AUDIO_FILE}")
    sys.exit(1)

# Change to SadTalker directory for execution
os.chdir(sadtalker_path)

# Import and run inference
from inference import main
from argparse import Namespace

# Create arguments with absolute paths
checkpoint_dir = os.path.join(sadtalker_path, 'checkpoints')
config_dir = os.path.join(sadtalker_path, 'src', 'config')

args = Namespace(
    driven_audio=AUDIO_FILE,
    source_image=REFERENCE_IMAGE,
    result_dir=OUTPUT_DIR,
    checkpoint_dir=checkpoint_dir,
    config_dir=config_dir,
    size=256,  # Use 256 for faster processing
    old_version=False,
    preprocess='crop',
    still=True,  # Enable still mode for better full body generation
    expression_scale=1.0,
    pose_style=0,
    batch_size=2,
    enhancer='gfpgan',  # Use GFPGAN enhancer
    background_enhancer=None,
    device='cuda',
    ref_eyeblink=None,
    ref_pose=None,
    input_yaw=None,
    input_pitch=None,
    input_roll=None,
    face3dvis=False,
    verbose=True
)

print("\nStarting video generation...")
print("This may take a few minutes depending on your GPU...\n")

try:
    main(args)
    print("\n" + "=" * 60)
    print("SUCCESS! Video generated successfully!")
    print(f"Check the output directory: {OUTPUT_DIR}")
    print("=" * 60)
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

