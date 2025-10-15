"""
Avatar generation configuration.
Can be overridden by environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Avatar generation settings
AVATAR_ENABLED = os.getenv("AVATAR_ENABLED", "true").lower() == "true"
AVATAR_MODEL = os.getenv("AVATAR_MODEL", "sadtalker")
AVATAR_DEVICE = os.getenv("AVATAR_DEVICE", "cuda")
AVATAR_SIZE = int(os.getenv("AVATAR_SIZE", "256"))
AVATAR_ENHANCER = os.getenv("AVATAR_ENHANCER", "gfpgan")
AVATAR_DEFAULT_IMAGE = os.getenv("AVATAR_DEFAULT_IMAGE", "Avatar/References/Huzaifa.jpg")
AVATAR_MODE = os.getenv("AVATAR_MODE", "fast")

# Avatar output directory
AVATAR_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "Avatar", "output")
os.makedirs(AVATAR_OUTPUT_DIR, exist_ok=True)

def get_avatar_config() -> dict:
    """Get avatar configuration as dict."""
    return {
        "enabled": AVATAR_ENABLED,
        "model": AVATAR_MODEL,
        "device": AVATAR_DEVICE,
        "size": AVATAR_SIZE,
        "enhancer": AVATAR_ENHANCER if AVATAR_ENHANCER.lower() != "none" else None,
        "default_image": AVATAR_DEFAULT_IMAGE,
        "mode": AVATAR_MODE,
        "output_dir": AVATAR_OUTPUT_DIR
    }


