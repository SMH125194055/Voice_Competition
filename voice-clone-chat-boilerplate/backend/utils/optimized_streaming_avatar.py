"""
Ultra-Optimized Real-Time Streaming Avatar Generator
Target: First chunk in <3 seconds with smooth transitions
Strategy: SDK reuse, smaller chunks, immediate returns, parallel processing
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
import queue
import threading
from typing import Optional, AsyncGenerator, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Add Ditto to path
DITTO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Avatar', 'ditto-talkinghead')
sys.path.insert(0, DITTO_PATH)

from stream_pipeline_offline import StreamSDK


class OptimizedStreamingAvatar:
    """
    Ultra-fast streaming avatar with <3 second first chunk latency
    
    Key optimizations:
    1. SDK pre-warming and reuse (saves ~6s)
    2. Smaller chunks (2s instead of 3s)
    3. Immediate chunk return (don't wait for batch)
    4. Thread pool for true parallelism
    5. Chunk queue for smooth delivery
    """
    
    def __init__(
        self,
        device='cuda',
        chunk_duration=2.0,  # Smaller chunks = faster first response
        overlap_duration=0.3,
        max_parallel_workers=3
    ):
        self.device = device
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration
        self.max_parallel_workers = max_parallel_workers
        
        # Model paths
        self.data_root = os.path.join(DITTO_PATH, "checkpoints", "ditto_pytorch")
        self.cfg_pkl = os.path.join(DITTO_PATH, "checkpoints", "ditto_cfg", "v0.4_hubert_cfg_pytorch.pkl")
        
        # Pre-warmed SDK pool for reuse
        self.sdk_pool = queue.Queue(maxsize=max_parallel_workers)
        self.sdk_initialized = False
        
        # Worker threads
        self.workers = []
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.shutdown_event = threading.Event()
        
        logger.info(f"🚀 OptimizedStreamingAvatar initialized")
        logger.info(f"   Chunk: {chunk_duration}s, Overlap: {overlap_duration}s")
        logger.info(f"   Workers: {max_parallel_workers}")
    
    def _init_sdk_pool(self):
        """Pre-warm SDK instances for immediate use"""
        if self.sdk_initialized:
            return
        
        logger.info(f"🔥 Pre-warming {self.max_parallel_workers} SDK instances...")
        start = time.time()
        
        for i in range(self.max_parallel_workers):
            sdk = StreamSDK(self.cfg_pkl, self.data_root)
            self.sdk_pool.put(sdk)
            logger.info(f"   SDK {i+1}/{self.max_parallel_workers} ready")
        
        elapsed = time.time() - start
        logger.info(f"✅ SDK pool ready in {elapsed:.2f}s")
        self.sdk_initialized = True
    
    def _worker_thread(self, worker_id: int):
        """Worker thread that processes chunks"""
        logger.info(f"Worker {worker_id} started")
        
        while not self.shutdown_event.is_set():
            try:
                # Get task with timeout
                task = self.task_queue.get(timeout=0.1)
                if task is None:  # Shutdown signal
                    break
                
                # Get SDK from pool
                sdk = self.sdk_pool.get()
                
                try:
                    # Process chunk
                    result = self._generate_chunk_sync(task, sdk, worker_id)
                    self.result_queue.put(result)
                finally:
                    # Return SDK to pool
                    self.sdk_pool.put(sdk)
                    self.task_queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                self.result_queue.put({'error': str(e)})
        
        logger.info(f"Worker {worker_id} stopped")
    
    def _start_workers(self):
        """Start worker threads"""
        if self.workers:
            return  # Already started
        
        for i in range(self.max_parallel_workers):
            worker = threading.Thread(target=self._worker_thread, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"✅ {self.max_parallel_workers} workers started")
    
    def _generate_chunk_sync(self, task: Dict, sdk: StreamSDK, worker_id: int) -> Dict:
        """Generate a single chunk synchronously"""
        try:
            chunk_info = task['chunk_info']
            image_path = task['image_path']
            output_dir = task['output_dir']
            emotion = task.get('emotion', 4)
            pose = task.get('pose', {})
            gaze = task.get('gaze', True)
            
            chunk_idx = chunk_info['idx']
            chunk_audio = chunk_info['audio']
            sr = chunk_info['sr']
            
            logger.info(f"[Worker {worker_id}] Processing chunk {chunk_idx}...")
            
            start_time = time.time()
            
            # Create temporary audio
            temp_audio_path = os.path.join(output_dir, f"temp_audio_{chunk_idx}_{time.time()}.wav")
            import soundfile as sf
            sf.write(temp_audio_path, chunk_audio, sr)
            
            # Output path
            chunk_output = os.path.join(output_dir, f"chunk_{chunk_idx:04d}.mp4")
            temp_output = chunk_output.replace('.mp4', f'_temp_{time.time()}')
            
            # Calculate fade
            num_frames = math.ceil(len(chunk_audio) / sr * 25)
            fade_in = 8 if chunk_info.get('fade_in') else -1
            fade_out = 8 if chunk_info.get('fade_out') else -1
            
            # Setup (reuse SDK)
            sdk.setup(
                image_path,
                temp_output,
                emo=emotion,
                drive_eye=gaze,
                overall_ctrl_info=pose
            )
            
            sdk.setup_Nd(
                N_d=num_frames,
                fade_in=fade_in,
                fade_out=fade_out,
                ctrl_info={}
            )
            
            # Generate
            aud_feat = sdk.wav2feat.wav2feat(chunk_audio)
            sdk.audio2motion_queue.put(aud_feat)
            sdk.close()
            
            # Add audio
            actual_temp = temp_output + ".tmp.mp4"
            ffmpeg_cmd = f'ffmpeg -loglevel error -y -i "{actual_temp}" -i "{temp_audio_path}" -map 0:v -map 1:a -c:v copy -c:a aac "{chunk_output}"'
            os.system(ffmpeg_cmd)
            
            # Cleanup
            if os.path.exists(actual_temp):
                os.unlink(actual_temp)
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            
            elapsed = time.time() - start_time
            
            logger.info(f"[Worker {worker_id}] ✅ Chunk {chunk_idx} done in {elapsed:.2f}s")
            
            return {
                'chunk_idx': chunk_idx,
                'video_path': chunk_output,
                'duration': chunk_info['duration'],
                'start_time': chunk_info['start_time'],
                'end_time': chunk_info['end_time'],
                'is_last': chunk_info['is_last'],
                'generation_time': elapsed,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"[Worker {worker_id}] ❌ Chunk {chunk_idx} failed: {e}")
            return {
                'chunk_idx': chunk_idx,
                'error': str(e)
            }
    
    def _generate_single_chunk_sync(
        self,
        audio_path: str,
        image_path: str,
        output_dir: str,
        emotion: int = 4,
        pose: Dict = None,
        gaze: bool = True
    ) -> Dict:
        """
        Synchronous single-chunk generation for simple cases
        """
        # Initialize if needed
        if not self.sdk_initialized:
            self._init_sdk_pool()
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Load audio
        audio, sr = librosa.load(audio_path, sr=16000)
        duration = len(audio) / sr
        
        # Prepare task
        chunk_info = {
            'idx': 0,
            'audio': audio,
            'sr': sr,
            'duration': duration,
            'start_time': 0.0,
            'end_time': duration,
            'fade_in': False,
            'fade_out': False,
            'is_last': True
        }
        
        task = {
            'chunk_info': chunk_info,
            'image_path': image_path,
            'output_dir': output_dir,
            'emotion': emotion,
            'pose': pose or {},
            'gaze': gaze
        }
        
        # Get SDK and generate
        sdk = self.sdk_pool.get()
        try:
            result = self._generate_chunk_sync(task, sdk, 0)
            return result
        finally:
            self.sdk_pool.put(sdk)
    
    def _split_audio(self, audio_path: str) -> List[Dict]:
        """Split audio into optimized chunks"""
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
            
            chunks.append({
                'idx': chunk_idx,
                'audio': chunk_audio,
                'sr': sr,
                'start_time': start / sr,
                'end_time': end / sr,
                'duration': len(chunk_audio) / sr,
                'fade_in': chunk_idx > 0,
                'fade_out': end < len(audio),
                'is_last': end >= len(audio)
            })
            
            if end >= len(audio):
                break
            
            start += step_samples
            chunk_idx += 1
        
        logger.info(f"📊 {len(chunks)} chunks ({self.chunk_duration}s each)")
        return chunks
    
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
        Generate video chunks with ultra-low latency
        Returns chunks as soon as they complete (not in order)
        """
        # Initialize
        if not self.sdk_initialized:
            self._init_sdk_pool()
        
        self._start_workers()
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Split audio
        chunks = self._split_audio(audio_path)
        total_chunks = len(chunks)
        
        logger.info(f"🚀 Starting generation of {total_chunks} chunks...")
        
        # Submit all chunks to queue
        for chunk_info in chunks:
            task = {
                'chunk_info': chunk_info,
                'image_path': image_path,
                'output_dir': output_dir,
                'emotion': emotion,
                'pose': pose or {},
                'gaze': gaze
            }
            self.task_queue.put(task)
        
        # Collect results as they complete (out of order is OK for speed)
        completed = 0
        seen_chunks = set()
        
        while completed < total_chunks:
            try:
                # Check for completed chunks (non-blocking with short timeout)
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.result_queue.get(timeout=0.1)
                )
                
                if result and 'error' not in result:
                    chunk_idx = result['chunk_idx']
                    
                    if chunk_idx not in seen_chunks:
                        seen_chunks.add(chunk_idx)
                        completed += 1
                        
                        logger.info(f"📦 Chunk {chunk_idx} ready ({completed}/{total_chunks})")
                        yield result
                
            except queue.Empty:
                await asyncio.sleep(0.1)
                continue
            except Exception as e:
                logger.error(f"Error collecting results: {e}")
                break
        
        logger.info(f"✅ All {total_chunks} chunks generated")
    
    def shutdown(self):
        """Shutdown workers and cleanup"""
        logger.info("🛑 Shutting down...")
        self.shutdown_event.set()
        
        # Signal workers to stop
        for _ in range(self.max_parallel_workers):
            self.task_queue.put(None)
        
        # Wait for workers
        for worker in self.workers:
            worker.join(timeout=2)
        
        logger.info("✅ Shutdown complete")


# Main function for testing
async def quick_test():
    """Quick test to measure first chunk latency"""
    REFERENCE_IMAGE = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/Avatar/References/ref_1761131562372.jpg"
    REFERENCE_AUDIO = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/audio/reference_voices/ref_1761118578.wav"
    OUTPUT_DIR = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/Avatar/ditto-talkinghead/optimized_test"
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    logger.info("="*80)
    logger.info("🎯 OPTIMIZED STREAMING TEST - TARGET: <3 SECONDS")
    logger.info("="*80)
    
    generator = OptimizedStreamingAvatar(
        chunk_duration=2.0,  # 2 second chunks
        overlap_duration=0.3,
        max_parallel_workers=3
    )
    
    start_time = time.time()
    first_chunk_time = None
    chunk_count = 0
    
    async for chunk in generator.generate_streaming(
        REFERENCE_AUDIO,
        REFERENCE_IMAGE,
        OUTPUT_DIR,
        emotion=4,
        pose={},
        gaze=True
    ):
        chunk_count += 1
        elapsed = time.time() - start_time
        
        if first_chunk_time is None:
            first_chunk_time = elapsed
            logger.info(f"\n🎉 FIRST CHUNK READY IN: {first_chunk_time:.2f}s\n")
        
        logger.info(f"Chunk {chunk['chunk_idx']}: {elapsed:.2f}s from start")
    
    total_time = time.time() - start_time
    
    logger.info(f"\n{'='*80}")
    logger.info("📊 RESULTS")
    logger.info(f"{'='*80}")
    logger.info(f"First chunk: {first_chunk_time:.2f}s")
    logger.info(f"Total time: {total_time:.2f}s")
    logger.info(f"Chunks: {chunk_count}")
    
    if first_chunk_time <= 3.0:
        logger.info(f"\n🎉 SUCCESS! First chunk in {first_chunk_time:.2f}s (<3s target)")
    elif first_chunk_time <= 5.0:
        logger.info(f"\n✅ GOOD! First chunk in {first_chunk_time:.2f}s (<5s target)")
    else:
        logger.info(f"\n⚠️ NEEDS MORE OPTIMIZATION: {first_chunk_time:.2f}s")
    
    generator.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    asyncio.run(quick_test())

