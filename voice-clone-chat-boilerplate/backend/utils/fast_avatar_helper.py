"""
Fast Avatar Helper - Drop-in replacement for your loop
Optimizes avatar generation by reusing reference image setup
"""
import os
import sys
import logging
import librosa
import math

logger = logging.getLogger(__name__)

# Add Ditto to path
DITTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'ditto-talkinghead')
sys.path.insert(0, DITTO_PATH)

from stream_pipeline_offline import StreamSDK


class FastAvatarHelper:
    """
    Simple helper to speed up avatar generation in your loop
    
    Usage:
        # Outside loop (initialize once)
        helper = FastAvatarHelper(reference_image)
        helper.initialize()
        
        # In your loop
        for audio_path in audio_files:
            video_path = helper.generate_video(audio_path, output_dir)
            # Use video_path...
        
        # After loop
        helper.cleanup()
    """
    def __init__(self, reference_image: str, emotion: int = 4, gaze: bool = True):
        self.reference_image = reference_image
        self.emotion = emotion
        self.gaze = gaze
        self.sdk = None
        self.initialized = False
        
        # Use PyTorch models
        self.data_root = os.path.join(DITTO_PATH, "checkpoints", "ditto_pytorch")
        self.cfg_pkl = os.path.join(DITTO_PATH, "checkpoints", "ditto_cfg", "v0.4_hubert_cfg_pytorch.pkl")
        
        # Temp path for reference setup
        self.temp_reference_path = None
    
    def initialize(self):
        """
        Initialize SDK and setup reference image ONCE
        Call this BEFORE your loop
        """
        if self.initialized:
            return
        
        logger.info("[FastAvatar] Initializing SDK...")
        self.sdk = StreamSDK(self.cfg_pkl, self.data_root)
        
        # Setup reference image ONCE
        import tempfile
        self.temp_reference_path = os.path.join(tempfile.gettempdir(), "fast_avatar_ref")
        
        logger.info("[FastAvatar] Setting up reference image (ONE TIME)...")
        self.sdk.setup(
            self.reference_image,
            self.temp_reference_path,
            emo=self.emotion,
            drive_eye=self.gaze,
            overall_ctrl_info={}
        )
        
        self.initialized = True
        logger.info("[FastAvatar] ✅ Ready! (Reference image pre-processed)")
    
    def generate_video(self, audio_path: str, output_dir: str) -> str:
        """
        Generate video from audio (FAST - reuses reference!)
        
        Args:
            audio_path: Path to audio file
            output_dir: Directory to save video
        
        Returns:
            Path to generated video
        """
        if not self.initialized:
            raise RuntimeError("Call initialize() first!")
        
        import uuid
        import time
        
        start_time = time.time()
        
        # Load audio
        audio, sr = librosa.load(audio_path, sr=16000)
        num_frames = math.ceil(len(audio) / sr * 25)
        
        # Setup frame count (FAST - no image processing!)
        self.sdk.setup_Nd(
            N_d=num_frames,
            fade_in=-1,
            fade_out=-1,
            ctrl_info={}
        )
        
        # Generate video
        aud_feat = self.sdk.wav2feat.wav2feat(audio)
        self.sdk.audio2motion_queue.put(aud_feat)
        self.sdk.close()
        
        # Add audio with FFmpeg
        video_no_audio = self.temp_reference_path + ".tmp.mp4"
        
        # Output path
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"avatar_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        
        ffmpeg_cmd = f'ffmpeg -loglevel error -y -i "{video_no_audio}" -i "{audio_path}" -map 0:v -map 1:a -c:v copy -c:a aac "{output_path}"'
        os.system(ffmpeg_cmd)
        
        elapsed = time.time() - start_time
        logger.info(f"[FastAvatar] ✅ Generated video in {elapsed:.2f}s")
        
        return output_path
    
    def cleanup(self):
        """
        Cleanup resources
        Call this AFTER your loop
        """
        if self.temp_reference_path and os.path.exists(self.temp_reference_path + ".tmp.mp4"):
            try:
                os.unlink(self.temp_reference_path + ".tmp.mp4")
            except:
                pass
        
        self.sdk = None
        self.initialized = False
        logger.info("[FastAvatar] Cleaned up")


# Convenience function for single video generation
def generate_fast_avatar(
    audio_path: str,
    reference_image: str,
    output_dir: str,
    emotion: int = 4,
    gaze: bool = True
) -> str:
    """
    Generate a single video (convenience function)
    
    For loops, use FastAvatarHelper class instead for better performance!
    """
    helper = FastAvatarHelper(reference_image, emotion, gaze)
    helper.initialize()
    
    try:
        return helper.generate_video(audio_path, output_dir)
    finally:
        helper.cleanup()

