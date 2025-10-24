"""
Parallel Pipeline for Real-Time Avatar Generation
LLM → Voice Cloner → Avatar Generation (all running in parallel with queues)

Architecture:
    LLM Worker → [Text Queue] → Voice Worker → [Audio Queue] → Avatar Worker → [Video Queue] → Frontend
    
All components run simultaneously with producer-consumer pattern for <5s latency
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import queue
import threading
import logging
import os
import sys
import json
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

# Add paths
BACKEND_PATH = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BACKEND_PATH)

from utils import chat_with_llm_streaming, text_to_speech
from utils.optimized_streaming_avatar import OptimizedStreamingAvatar

# Global avatar generator (shared across requests to avoid repeated warmup)
_global_avatar_generator = None

def get_global_avatar_generator():
    """Get or create the global avatar generator"""
    global _global_avatar_generator
    if _global_avatar_generator is None:
        logger.info("🔥 Initializing global avatar generator...")
        _global_avatar_generator = OptimizedStreamingAvatar(
            chunk_duration=2.0,
            overlap_duration=0.3,
            max_parallel_workers=3
        )
        _global_avatar_generator._init_sdk_pool()
        logger.info("✅ Global avatar generator ready")
    return _global_avatar_generator


class ParallelPipelineRequest(BaseModel):
    """Request for parallel pipeline"""
    question: str
    reference_image: Optional[str] = None
    reference_audio: Optional[str] = None
    emotion: Optional[int] = 4
    pose: Optional[dict] = None
    gaze: Optional[bool] = True


class ParallelPipelineOrchestrator:
    """
    Orchestrates parallel pipeline with queues
    
    Flow:
    1. LLM Worker: Generate text → Text Queue
    2. Voice Worker: Text Queue → Generate audio → Audio Queue  
    3. Avatar Worker: Audio Queue → Generate video → Video Queue
    4. Main: Video Queue → Stream to frontend
    """
    
    def __init__(self):
        self.text_queue = queue.Queue(maxsize=10)
        self.audio_queue = queue.Queue(maxsize=10)
        self.video_queue = queue.Queue(maxsize=10)
        
        self.stop_event = threading.Event()
        self.workers = []
        
        self.session_id = str(uuid.uuid4())[:8]
        self.output_dir = os.path.join(BACKEND_PATH, "generated_videos", "parallel", self.session_id)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Use global avatar generator (shared across requests)
        self.avatar_generator = get_global_avatar_generator()
        
        logger.info(f"🎬 Parallel Pipeline initialized (session: {self.session_id})")
    
    def start(self, question: str, reference_image: str, reference_audio: str, emotion: int, pose: dict, gaze: bool):
        """Start all workers"""
        self.stop_event.clear()
        
        # Start LLM worker
        llm_worker = threading.Thread(
            target=self._llm_worker,
            args=(question,),
            daemon=True
        )
        llm_worker.start()
        self.workers.append(llm_worker)
        
        # Start Voice worker
        voice_worker = threading.Thread(
            target=self._voice_worker,
            args=(reference_audio,),
            daemon=True
        )
        voice_worker.start()
        self.workers.append(voice_worker)
        
        # Start Avatar worker
        avatar_worker = threading.Thread(
            target=self._avatar_worker,
            args=(reference_image, emotion, pose, gaze),
            daemon=True
        )
        avatar_worker.start()
        self.workers.append(avatar_worker)
        
        logger.info(f"✅ All workers started")
    
    def _llm_worker(self, question: str):
        """
        Worker 1: LLM Text Generation
        Generates text and pushes to text queue in chunks
        """
        try:
            logger.info("[LLM Worker] Started")
            
            text_buffer = ""
            min_chunk_chars = 80  # Minimum chars before passing to voice
            sentence_endings = ['.', '!', '?', '\n']
            
            # Stream from LLM - use sync wrapper for async generator
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                async def process_llm_stream():
                    nonlocal text_buffer
                    async for chunk in chat_with_llm_streaming(question):
                        if self.stop_event.is_set():
                            logger.info("[LLM Worker] Stopped by user")
                            break
                        
                        text_buffer += chunk
                        
                        # Check if we should push to voice queue
                        should_push = (
                            len(text_buffer) >= min_chunk_chars and 
                            any(text_buffer.endswith(end) for end in sentence_endings)
                        ) or len(text_buffer) > 200
                        
                        if should_push:
                            logger.info(f"[LLM Worker] → Text Queue: {len(text_buffer)} chars")
                            self.text_queue.put({
                                'type': 'text',
                                'content': text_buffer.strip()
                            })
                            text_buffer = ""
                
                loop.run_until_complete(process_llm_stream())
            finally:
                loop.close()
            
            # Push remaining text
            if text_buffer.strip():
                logger.info(f"[LLM Worker] → Text Queue (final): {len(text_buffer)} chars")
                self.text_queue.put({
                    'type': 'text',
                    'content': text_buffer.strip()
                })
            
            # Signal completion
            self.text_queue.put({'type': 'done'})
            logger.info("[LLM Worker] ✅ Complete")
            
        except Exception as e:
            logger.error(f"[LLM Worker] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            self.text_queue.put({'type': 'error', 'message': str(e)})
    
    def _voice_worker(self, reference_audio: str):
        """
        Worker 2: Voice Cloning
        Takes text from queue, generates audio, pushes to audio queue
        """
        try:
            logger.info("[Voice Worker] Started")
            
            # Ensure TTS is initialized
            from utils.tts import initialize_tts
            import os as os_module
            mode = os_module.getenv("MODE", "local")
            initialize_tts(mode, reference_audio)
            logger.info(f"[Voice Worker] TTS initialized (mode={mode})")
            
            chunk_idx = 0
            
            while not self.stop_event.is_set():
                try:
                    # Get text from queue (with timeout)
                    item = self.text_queue.get(timeout=0.5)
                    
                    if item['type'] == 'done':
                        logger.info("[Voice Worker] Received done signal")
                        self.audio_queue.put({'type': 'done'})
                        break
                    
                    elif item['type'] == 'error':
                        logger.error(f"[Voice Worker] Received error from LLM")
                        self.audio_queue.put(item)
                        break
                    
                    elif item['type'] == 'text':
                        text = item['content']
                        logger.info(f"[Voice Worker] Processing: {text[:50]}...")
                        
                        start_time = time.time()
                        
                        # Use asyncio to run the async text_to_speech function
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            audio_path = loop.run_until_complete(
                                text_to_speech(
                                    text=text,
                                    mode="local",
                                    reference_audio_path=reference_audio
                                )
                            )
                        finally:
                            loop.close()
                        
                        elapsed = time.time() - start_time
                        
                        if audio_path and os.path.exists(audio_path):
                            logger.info(f"[Voice Worker] → Audio Queue: chunk_{chunk_idx} ({elapsed:.2f}s)")
                            self.audio_queue.put({
                                'type': 'audio',
                                'path': audio_path,
                                'text': text,
                                'chunk_idx': chunk_idx
                            })
                            chunk_idx += 1
                        else:
                            logger.error(f"[Voice Worker] Failed to generate audio")
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"[Voice Worker] Error processing: {e}")
                    continue
            
            logger.info("[Voice Worker] ✅ Complete")
            
        except Exception as e:
            logger.error(f"[Voice Worker] ❌ Error: {e}")
            self.audio_queue.put({'type': 'error', 'message': str(e)})
    
    def _avatar_worker(self, reference_image: str, emotion: int, pose: dict, gaze: bool):
        """
        Worker 3: Avatar Generation
        Takes audio from queue, generates video, pushes to video queue
        """
        try:
            logger.info("[Avatar Worker] Started")
            
            # Start workers (pool is already warmed up in __init__)
            self.avatar_generator._start_workers()
            logger.info("[Avatar Worker] Workers ready")
            
            while not self.stop_event.is_set():
                try:
                    # Get audio from queue
                    item = self.audio_queue.get(timeout=0.5)
                    
                    if item['type'] == 'done':
                        logger.info("[Avatar Worker] Received done signal")
                        self.video_queue.put({'type': 'done'})
                        break
                    
                    elif item['type'] == 'error':
                        logger.error(f"[Avatar Worker] Received error")
                        self.video_queue.put(item)
                        break
                    
                    elif item['type'] == 'audio':
                        audio_path = item['path']
                        chunk_idx = item['chunk_idx']
                        text = item['text']
                        
                        logger.info(f"[Avatar Worker] Processing audio chunk {chunk_idx}...")
                        
                        # Generate video using sync method
                        start_time = time.time()
                        
                        # Use the underlying sync generation
                        result = self.avatar_generator._generate_single_chunk_sync(
                            audio_path,
                            reference_image,
                            self.output_dir,
                            emotion=emotion,
                            pose=pose,
                            gaze=gaze
                        )
                        
                        elapsed = time.time() - start_time
                        
                        if result and not result.get('error'):
                            logger.info(f"[Avatar Worker] → Video Queue: video chunk ({elapsed:.2f}s)")
                            
                            self.video_queue.put({
                                'type': 'video',
                                'video_path': result['video_path'],
                                'duration': result['duration'],
                                'chunk_idx': 0,  # Single chunk
                                'audio_chunk_idx': chunk_idx,
                                'text': text,
                                'generation_time': elapsed,
                                'is_last': False
                            })
                        else:
                            logger.error(f"[Avatar Worker] Video generation failed: {result.get('error') if result else 'No result'}")
                
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"[Avatar Worker] Error processing: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            logger.info("[Avatar Worker] ✅ Complete")
            
        except Exception as e:
            logger.error(f"[Avatar Worker] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            self.video_queue.put({'type': 'error', 'message': str(e)})
    
    def stop(self):
        """Stop all workers and clear queues"""
        logger.info("🛑 Stopping pipeline...")
        self.stop_event.set()
        
        # Clear queues
        self._clear_queue(self.text_queue)
        self._clear_queue(self.audio_queue)
        self._clear_queue(self.video_queue)
        
        # Wait for workers
        for worker in self.workers:
            worker.join(timeout=2)
        
        # Shutdown avatar generator
        self.avatar_generator.shutdown()
        
        logger.info("✅ Pipeline stopped")
    
    def _clear_queue(self, q: queue.Queue):
        """Clear all items from queue"""
        while not q.empty():
            try:
                q.get_nowait()
            except queue.Empty:
                break
    
    async def stream_results(self):
        """Stream video results as they become available"""
        try:
            # Yield startup event immediately
            yield {
                'event': 'started',
                'session_id': self.session_id,
                'message': 'Pipeline started'
            }
            
            first_video = True
            video_count = 0
            start_time = time.time()
            
            while not self.stop_event.is_set():
                try:
                    # Get video from queue (with timeout)
                    item = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.video_queue.get(timeout=0.5)
                    )
                    
                    if item['type'] == 'done':
                        logger.info(f"[Pipeline] ✅ Complete: {video_count} videos in {time.time() - start_time:.2f}s")
                        yield {
                            'event': 'complete',
                            'total_videos': video_count,
                            'total_time': time.time() - start_time
                        }
                        break
                    
                    elif item['type'] == 'error':
                        logger.error(f"[Pipeline] Error: {item['message']}")
                        yield {
                            'event': 'error',
                            'message': item['message']
                        }
                        break
                    
                    elif item['type'] == 'video':
                        video_count += 1
                        elapsed = time.time() - start_time
                        
                        if first_video:
                            first_video = False
                            logger.info(f"🎉 FIRST VIDEO READY IN: {elapsed:.2f}s")
                        
                        # Create video URL
                        video_filename = os.path.basename(item['video_path'])
                        video_url = f"/generated_videos/parallel/{self.session_id}/{video_filename}"
                        
                        yield {
                            'event': 'video_chunk',
                            'video_url': video_url,
                            'duration': item['duration'],
                            'chunk_idx': item['chunk_idx'],
                            'audio_chunk_idx': item['audio_chunk_idx'],
                            'text': item['text'],
                            'generation_time': item['generation_time'],
                            'total_elapsed': elapsed,
                            'session_id': self.session_id
                        }
                        
                        logger.info(f"[Pipeline] Video {video_count} sent to frontend ({elapsed:.2f}s)")
                
                except queue.Empty:
                    await asyncio.sleep(0.1)
                    continue
                except Exception as e:
                    logger.error(f"[Pipeline] Stream error: {e}")
                    yield {
                        'event': 'error',
                        'message': str(e)
                    }
                    break
        
        finally:
            self.stop()


@router.post("/api/parallel-pipeline/generate")
async def generate_parallel_pipeline(request: ParallelPipelineRequest):
    """
    Generate avatar video using parallel pipeline with queues
    
    Pipeline: LLM → Voice → Avatar (all running in parallel)
    Returns: SSE stream of video chunks as they're generated
    """
    try:
        # Get reference files
        if request.reference_image:
            image_path = request.reference_image
        else:
            image_path = os.path.join(BACKEND_PATH, "Avatar/References/ref_1761131562372.jpg")
        
        if request.reference_audio:
            audio_path = request.reference_audio
        else:
            audio_path = os.path.join(BACKEND_PATH, "audio/reference_voices/ref_1761118578.wav")
        
        logger.info(f"🚀 Starting parallel pipeline for: {request.question[:50]}...")
        
        # Create orchestrator
        orchestrator = ParallelPipelineOrchestrator()
        
        # Start pipeline
        orchestrator.start(
            question=request.question,
            reference_image=image_path,
            reference_audio=audio_path,
            emotion=request.emotion,
            pose=request.pose or {},
            gaze=request.gaze
        )
        
        # Stream results
        async def sse_stream():
            """Generate Server-Sent Events"""
            try:
                logger.info("[SSE] Starting SSE stream...")
                async for result in orchestrator.stream_results():
                    data = f"data: {json.dumps(result)}\n\n"
                    logger.info(f"[SSE] Sending: {result.get('event', 'unknown')}")
                    yield data
                logger.info("[SSE] Stream complete")
            except Exception as e:
                logger.error(f"[SSE] Stream error: {e}")
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(
            sse_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )
    
    except Exception as e:
        logger.error(f"❌ Parallel pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/parallel-pipeline/stop")
async def stop_parallel_pipeline(session_id: str):
    """Stop a running pipeline and clear all queues"""
    # Note: In production, you'd track active orchestrators by session_id
    # For now, this is a placeholder
    return {"status": "stopped", "session_id": session_id}


@router.get("/api/parallel-pipeline/status")
async def get_pipeline_status():
    """Get parallel pipeline status"""
    return {
        "status": "ready",
        "pipeline_type": "parallel_queues",
        "components": ["llm", "voice_cloner", "avatar_generator"],
        "mode": "real_time_streaming"
    }

