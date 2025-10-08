"""
Voice Activity Detection utilities using Silero VAD.
Provides advanced VAD capabilities for audio preprocessing.
"""

import os
import sys
import torch
import numpy as np
import tempfile
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Add silero-vad to path
SILERO_VAD_PATH = os.path.join(os.path.dirname(__file__), '..', 'silero-vad', 'src')
if SILERO_VAD_PATH not in sys.path:
    sys.path.insert(0, SILERO_VAD_PATH)

try:
    from silero_vad import load_silero_vad, get_speech_timestamps, read_audio
    SILERO_VAD_AVAILABLE = True
    logger.info("Silero VAD loaded successfully")
except ImportError as e:
    logger.warning(f"Silero VAD not available: {e}")
    SILERO_VAD_AVAILABLE = False


class VADProcessor:
    """Voice Activity Detection processor using Silero VAD."""
    
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if SILERO_VAD_AVAILABLE:
            try:
                self.model = load_silero_vad()
                self.model.to(self.device)
                logger.info(f"VAD model loaded on {self.device}")
            except Exception as e:
                logger.error(f"Failed to load VAD model: {e}")
                self.model = None
    
    def is_available(self) -> bool:
        """Check if VAD is available."""
        return self.model is not None
    
    def detect_speech_segments(
        self, 
        audio_path: str,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
        window_size_samples: int = 512,
        speech_pad_ms: int = 30
    ) -> List[dict]:
        """
        Detect speech segments in audio file.
        
        Args:
            audio_path: Path to audio file
            threshold: Speech threshold (0.0 to 1.0)
            min_speech_duration_ms: Minimum speech duration to consider
            min_silence_duration_ms: Minimum silence duration between segments
            window_size_samples: Window size for VAD processing
            speech_pad_ms: Padding around speech segments
            
        Returns:
            List of speech segments with start/end timestamps
        """
        if not self.is_available():
            logger.warning("VAD not available, returning full audio as speech")
            return [{'start': 0, 'end': -1, 'confidence': 1.0}]
        
        try:
            # Read audio file (silero-vad expects 16kHz)
            wav = read_audio(audio_path, sampling_rate=16000)
            
            # Get speech timestamps
            speech_timestamps = get_speech_timestamps(
                wav,
                self.model,
                threshold=threshold,
                min_speech_duration_ms=min_speech_duration_ms,
                min_silence_duration_ms=min_silence_duration_ms,
                window_size_samples=window_size_samples,
                speech_pad_ms=speech_pad_ms,
                return_seconds=False  # Return in samples
            )
            
            # Convert to seconds and add confidence
            segments = []
            for ts in speech_timestamps:
                segments.append({
                    'start': ts['start'] / 16000,  # Convert samples to seconds
                    'end': ts['end'] / 16000,
                    'confidence': 1.0  # Silero VAD doesn't provide confidence scores
                })
            
            logger.info(f"Detected {len(segments)} speech segments")
            return segments
            
        except Exception as e:
            logger.error(f"VAD processing error: {e}")
            return [{'start': 0, 'end': -1, 'confidence': 1.0}]
    
    def has_speech(
        self,
        audio_path: str,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250
    ) -> Tuple[bool, float]:
        """
        Check if audio contains speech.
        
        Args:
            audio_path: Path to audio file
            threshold: Speech threshold
            min_speech_duration_ms: Minimum speech duration
            
        Returns:
            Tuple of (has_speech, speech_duration_seconds)
        """
        segments = self.detect_speech_segments(
            audio_path,
            threshold=threshold,
            min_speech_duration_ms=min_speech_duration_ms
        )
        
        if not segments:
            return False, 0.0
        
        # Calculate total speech duration
        total_duration = sum(seg['end'] - seg['start'] for seg in segments if seg['end'] > 0)
        
        return len(segments) > 0, total_duration
    
    def extract_speech_audio(
        self,
        audio_path: str,
        output_path: Optional[str] = None,
        threshold: float = 0.5,
        merge_segments: bool = True
    ) -> Optional[str]:
        """
        Extract speech portions from audio.
        
        Args:
            audio_path: Input audio path
            output_path: Output audio path (optional)
            threshold: Speech threshold
            merge_segments: Whether to merge all speech segments
            
        Returns:
            Path to extracted audio file or None
        """
        if not self.is_available():
            logger.warning("VAD not available, returning original audio")
            return audio_path
        
        try:
            from pydub import AudioSegment
            
            # Detect speech segments
            segments = self.detect_speech_segments(audio_path, threshold=threshold)
            
            if not segments:
                logger.warning("No speech detected in audio")
                return None
            
            # Load audio
            audio = AudioSegment.from_file(audio_path)
            
            # Extract speech segments
            speech_parts = []
            for seg in segments:
                start_ms = int(seg['start'] * 1000)
                end_ms = int(seg['end'] * 1000) if seg['end'] > 0 else len(audio)
                speech_parts.append(audio[start_ms:end_ms])
            
            # Merge or keep separate
            if merge_segments and speech_parts:
                output_audio = speech_parts[0]
                for part in speech_parts[1:]:
                    output_audio += part
            else:
                output_audio = speech_parts[0] if speech_parts else audio
            
            # Save to file
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                output_path = temp_file.name
                temp_file.close()
            
            output_audio.export(output_path, format="wav")
            logger.info(f"Extracted speech saved to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error extracting speech: {e}")
            return audio_path


# Global VAD processor instance
_vad_processor = None


def get_vad_processor() -> VADProcessor:
    """Get or create global VAD processor instance."""
    global _vad_processor
    if _vad_processor is None:
        _vad_processor = VADProcessor()
    return _vad_processor


# Convenience functions
def detect_speech(audio_path: str, threshold: float = 0.5) -> List[dict]:
    """Detect speech segments in audio file."""
    vad = get_vad_processor()
    return vad.detect_speech_segments(audio_path, threshold=threshold)


def has_speech(audio_path: str, threshold: float = 0.5) -> Tuple[bool, float]:
    """Check if audio contains speech."""
    vad = get_vad_processor()
    return vad.has_speech(audio_path, threshold=threshold)


def clean_audio(audio_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """Remove silence and extract only speech from audio."""
    vad = get_vad_processor()
    return vad.extract_speech_audio(audio_path, output_path=output_path)




