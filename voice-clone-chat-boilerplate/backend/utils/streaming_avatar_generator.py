"""
Real-Time Streaming Avatar Generator with Parallel Chunk Processing
Achieves <5 second latency with smooth transitions between chunks
"""

import os
import sys
import asyncio
import logging
import librosa
import numpy as np
import math
import tempfile
import time
from typing import Optional, AsyncGenerator, Dict, List
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logger = logging.getLogger(__name__)

# Add Ditto to path
DITTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'ditto-talkinghead')
sys.path.insert(0, DITTO_PATH)

from stream_pipeline_offline import StreamSDK


class StreamingAvatarGenerator:
    """
    Parallel chunk-based video generation for real-time streaming
    Target: First chunk in <5 seconds, smooth transitions
    """
    
    def __init__(
        self,
        device='cuda',
        size=256,
        chunk_duration=3.0,  # 3-second chunks for smooth streaming
        overlap_duration=0.5,  # 0.5s overlap for smooth transitions
        max_parallel_chunks=3,  # Generate 3 chunks in parallel
        mode='offline'  # 'offline' or 'online'
    ):
        self.device = device
        self.size = size
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.max_parallel_chunks = max_parallel_chunks
        self.mode = mode
        self.initialized = False
        
        # Model paths
        self.data_root = os.path.join(DITTO_PATH, "checkpoints", "ditto_pytorch")
        self.cfg_pkl = os.path.join(DITTO_PATH, "checkpoints", "ditto_cfg", "v0.4_hubert_cfg_pytorch.pkl")
        
        # Thread pool for parallel chunk generation
        self.executor = ThreadPoolExecutor(max_workers=max_parallel_chunks)
        
        # Chunk cache
        self.chunk_cache = {}
        self.reference_image_cache = {}
        
        logger.info(f"🎬 StreamingAvatarGenerator initialized")
        logger.info(f"   Mode: {mode}")
        logger.info(f"   Chunk duration: {chunk_duration}s")
        logger.info(f"   Overlap: {overlap_duration}s")
        logger.info(f"   Max parallel: {max_parallel_chunks}")
    
    def initialize(self):
        """Initialize the generator"""
        if self.initialized:
            return
        
        try:
            logger.info("🚀 Initializing Streaming Avatar Generator...")
            # Pre-warm one SDK instance
            sdk = StreamSDK(self.cfg_pkl, self.data_root)
            self.initialized = True
            logger.info("✅ Streaming Avatar Generator ready")
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            raise
    
    def _split_audio_into_chunks(
        self, 
        audio_path: str
    ) -> List[Dict]:
        """
        Split audio into overlapping chunks for smooth transitions
        """
        audio, sr = librosa.load(audio_path, sr=16000)
        duration = len(audio) / sr
        
        chunk_samples = int(self.chunk_duration * sr)
        overlap_samples = int(self.overlap_duration * sr)
        step_samples = chunk_samples - overlap_samples
        
        chunks = []
        start = 0
        chunk_idx = 0
        
        while start < len(audio):
            end = min(start + chunk_samples, len(audio))
            chunk_audio = audio[start:end]
            
            # Calculate fade for smooth transitions
            fade_in = chunk_idx > 0  # Fade in for all chunks except first
            fade_out = end < len(audio)  # Fade out if not last chunk
            
            chunk_info = {
                'idx': chunk_idx,
                'audio': chunk_audio,
                'sr': sr,
                'start_time': start / sr,
                'end_time': end / sr,
                'duration': len(chunk_audio) / sr,
                'fade_in': fade_in,
                'fade_out': fade_out,
                'is_last': end >= len(audio)
            }
            
            chunks.append(chunk_info)
            
            if end >= len(audio):
                break
            
            start += step_samples
            chunk_idx += 1
        
        logger.info(f"📊 Split audio into {len(chunks)} chunks")
        logger.info(f"   Total duration: {duration:.2f}s")
        logger.info(f"   Chunk duration: {self.chunk_duration}s")
        logger.info(f"   Overlap: {self.overlap_duration}s")
        
        return chunks
    
    def _generate_single_chunk(
        self,
        chunk_info: Dict,
        image_path: str,
        output_dir: str,
        emotion: int = 4,
        pose: Dict = None,
        gaze: bool = True
    ) -> Optional[str]:
        """
        Generate a single video chunk (runs in thread pool)
        """
        try:
            chunk_idx = chunk_info['idx']
            chunk_audio = chunk_info['audio']
            sr = chunk_info['sr']
            
            logger.info(f"🎬 Generating chunk {chunk_idx} (duration: {chunk_info['duration']:.2f}s)")
            
            start_time = time.time()
            
            # Create temporary audio file for this chunk
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav', dir=output_dir)
            import soundfile as sf
            sf.write(temp_audio.name, chunk_audio, sr)
            
            # Output path for this chunk
            chunk_output = os.path.join(output_dir, f"chunk_{chunk_idx:04d}.mp4")
            temp_output = chunk_output.replace('.mp4', '_temp')
            
            # Initialize SDK for this chunk
            sdk = StreamSDK(self.cfg_pkl, self.data_root)
            
            # Calculate fade frames
            num_frames = math.ceil(len(chunk_audio) / sr * 25)
            fade_in_frames = 10 if chunk_info['fade_in'] else -1
            fade_out_frames = 10 if chunk_info['fade_out'] else -1
            
            # Setup
            pose_ctrl = pose or {}
            sdk.setup(
                image_path,
                temp_output,
                emo=emotion,
                drive_eye=gaze,
                overall_ctrl_info=pose_ctrl
            )
            
            # Configure with fade
            sdk.setup_Nd(
                N_d=num_frames,
                fade_in=fade_in_frames,
                fade_out=fade_out_frames,
                ctrl_info={}
            )
            
            # Generate
            aud_feat = sdk.wav2feat.wav2feat(chunk_audio)
            sdk.audio2motion_queue.put(aud_feat)
            sdk.close()
            
            # Add audio
            actual_temp = temp_output + ".tmp.mp4"
            ffmpeg_cmd = f'ffmpeg -loglevel error -y -i "{actual_temp}" -i "{temp_audio.name}" -map 0:v -map 1:a -c:v copy -c:a aac "{chunk_output}"'
            os.system(ffmpeg_cmd)
            
            # Cleanup
            if os.path.exists(actual_temp):
                os.unlink(actual_temp)
            os.unlink(temp_audio.name)
            
            elapsed = time.time() - start_time
            fps = num_frames / elapsed if elapsed > 0 else 0
            
            logger.info(f"✅ Chunk {chunk_idx} generated in {elapsed:.2f}s (FPS: {fps:.1f})")
            
            return chunk_output
            
        except Exception as e:
            logger.error(f"❌ Chunk {chunk_idx} failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def generate_streaming(
        self,
        audio_path: str,
        image_path: str,
        output_dir: str,
        emotion: int = 4,
        pose: Dict = None,
        gaze: bool = True
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate video chunks in parallel and stream them as they complete
        
        Yields:
            Dict with keys: chunk_idx, video_path, duration, is_last
        """
        if not self.initialized:
            self.initialize()
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Split audio into chunks
        chunks = self._split_audio_into_chunks(audio_path)
        
        total_start = time.time()
        
        # Generate chunks in parallel batches
        for batch_start in range(0, len(chunks), self.max_parallel_chunks):
            batch_end = min(batch_start + self.max_parallel_chunks, len(chunks))
            batch_chunks = chunks[batch_start:batch_end]
            
            logger.info(f"🔄 Processing batch {batch_start//self.max_parallel_chunks + 1} "
                       f"(chunks {batch_start}-{batch_end-1})")
            
            # Submit all chunks in this batch to thread pool
            loop = asyncio.get_event_loop()
            futures = []
            
            for chunk_info in batch_chunks:
                future = loop.run_in_executor(
                    self.executor,
                    self._generate_single_chunk,
                    chunk_info,
                    image_path,
                    output_dir,
                    emotion,
                    pose,
                    gaze
                )
                futures.append((chunk_info, future))
            
            # Wait for all chunks in batch to complete
            for chunk_info, future in futures:
                video_path = await future
                
                if video_path:
                    chunk_result = {
                        'chunk_idx': chunk_info['idx'],
                        'video_path': video_path,
                        'duration': chunk_info['duration'],
                        'start_time': chunk_info['start_time'],
                        'end_time': chunk_info['end_time'],
                        'is_last': chunk_info['is_last']
                    }
                    
                    yield chunk_result
        
        total_elapsed = time.time() - total_start
        total_duration = sum(c['duration'] for c in chunks)
        
        logger.info(f"🎉 Streaming generation complete!")
        logger.info(f"   Total time: {total_elapsed:.2f}s")
        logger.info(f"   Audio duration: {total_duration:.2f}s")
        logger.info(f"   Realtime factor: {total_duration / total_elapsed:.2f}x")
    
    async def generate_from_text_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        tts_func,
        image_path: str,
        output_dir: str,
        emotion: int = 4,
        pose: Dict = None,
        gaze: bool = True
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate video from streaming text (LLM response)
        
        Pipeline:
        1. Accumulate text chunks until we have enough for TTS (~100 chars or sentence end)
        2. Generate audio with TTS
        3. Immediately start video generation
        4. Stream video chunks as they complete
        
        This achieves true real-time: first video chunk ready in <5 seconds
        """
        if not self.initialized:
            self.initialize()
        
        os.makedirs(output_dir, exist_ok=True)
        
        text_buffer = ""
        sentence_endings = ['.', '!', '?', '\n']
        min_chunk_chars = 80  # Minimum characters before generating audio
        
        chunk_counter = 0
        
        async for text_chunk in text_stream:
            text_buffer += text_chunk
            
            # Check if we should generate audio chunk
            should_generate = (
                len(text_buffer) >= min_chunk_chars and 
                any(text_buffer.endswith(end) for end in sentence_endings)
            ) or len(text_buffer) > 200  # Force generation if too long
            
            if should_generate:
                logger.info(f"📝 Text chunk accumulated: {len(text_buffer)} chars")
                
                # Generate audio from text
                audio_path = os.path.join(output_dir, f"audio_chunk_{chunk_counter:04d}.wav")
                await tts_func(text_buffer, audio_path)
                
                logger.info(f"🎵 Audio generated: {audio_path}")
                
                # Generate video from audio (streaming)
                async for video_chunk in self.generate_streaming(
                    audio_path,
                    image_path,
                    output_dir,
                    emotion,
                    pose,
                    gaze
                ):
                    yield video_chunk
                
                # Clear buffer
                text_buffer = ""
                chunk_counter += 1
        
        # Process any remaining text
        if text_buffer.strip():
            logger.info(f"📝 Final text chunk: {len(text_buffer)} chars")
            
            audio_path = os.path.join(output_dir, f"audio_chunk_{chunk_counter:04d}.wav")
            await tts_func(text_buffer, audio_path)
            
            async for video_chunk in self.generate_streaming(
                audio_path,
                image_path,
                output_dir,
                emotion,
                pose,
                gaze
            ):
                yield video_chunk
    
    def clear_cache(self):
        """Clear chunk cache"""
        self.chunk_cache.clear()
        self.reference_image_cache.clear()
        logger.info("🧹 Cache cleared")
    
    def shutdown(self):
        """Shutdown executor"""
        self.executor.shutdown(wait=True)
        logger.info("🛑 Executor shutdown")


# Convenience functions for backward compatibility
async def generate_avatar_streaming(
    audio_path: str,
    image_path: str,
    output_dir: str,
    emotion: int = 4,
    pose: Dict = None,
    gaze: bool = True,
    chunk_duration: float = 3.0
) -> AsyncGenerator[Dict, None]:
    """
    Generate avatar video in streaming mode
    
    Returns:
        AsyncGenerator yielding video chunks as they complete
    """
    generator = StreamingAvatarGenerator(
        chunk_duration=chunk_duration,
        max_parallel_chunks=3
    )
    generator.initialize()
    
    async for chunk in generator.generate_streaming(
        audio_path, image_path, output_dir,
        emotion, pose, gaze
    ):
        yield chunk

