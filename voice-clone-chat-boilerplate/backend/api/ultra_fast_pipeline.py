"""
Ultra-Fast Parallel Pipeline
Target: <5s first video chunk
Strategy:
1. Smaller text chunks (20-30 chars) → Faster TTS
2. Parallel LLM + TTS + Video workers
3. Start video generation while LLM is still streaming
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import logging
import json
import time
import os
import queue
import threading

from utils.realtime_streaming_avatar import get_realtime_avatar
from utils import text_to_speech, chat_with_llm_streaming, initialize_tts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ultra-fast", tags=["Ultra-Fast Pipeline"])


class UltraFastOrchestrator:
    """
    Ultra-fast parallel processing
    - Process tiny chunks (5-10 words)
    - Start video ASAP
    """
    def __init__(self):
        self.text_queue = asyncio.Queue()
        self.audio_queue = asyncio.Queue()
        self.video_queue = asyncio.Queue()
        self.stop_event = asyncio.Event()
    
    async def llm_worker(self, question: str):
        """Worker 1: Stream LLM with TINY chunks"""
        try:
            logger.info("[LLM] Started")
            buffer = ""
            word_count = 0
            min_words = 5  # Very small chunks!
            
            async for chunk in chat_with_llm_streaming(question):
                buffer += chunk
                
                # Count words
                words = buffer.split()
                word_count = len(words)
                
                # Push tiny chunks quickly
                if word_count >= min_words or any(buffer.endswith(p) for p in ['.', '!', '?', '\n']):
                    text = buffer.strip()
                    if text:
                        logger.info(f"[LLM] → Text: {text[:30]}...")
                        await self.text_queue.put(('text', text))
                        buffer = ""
                        word_count = 0
            
            if buffer.strip():
                await self.text_queue.put(('text', buffer.strip()))
            
            await self.text_queue.put(('done', None))
            logger.info("[LLM] ✅ Complete")
        except Exception as e:
            logger.error(f"[LLM] ❌ Error: {e}")
            await self.text_queue.put(('error', str(e)))
    
    async def tts_worker(self, reference_audio: str):
        """Worker 2: Generate audio FAST"""
        try:
            logger.info("[TTS] Started")
            mode = os.getenv("MODE", "local")
            initialize_tts(mode, reference_audio)
            
            chunk_idx = 0
            
            while not self.stop_event.is_set():
                try:
                    msg_type, data = await asyncio.wait_for(self.text_queue.get(), timeout=1.0)
                    
                    if msg_type == 'done':
                        logger.info("[TTS] Done signal")
                        await self.audio_queue.put(('done', None))
                        break
                    
                    elif msg_type == 'error':
                        await self.audio_queue.put(('error', data))
                        break
                    
                    elif msg_type == 'text':
                        logger.info(f"[TTS] Processing: {data[:30]}...")
                        start = time.time()
                        
                        audio_path = await text_to_speech(
                            text=data,
                            mode=mode,
                            reference_audio_path=reference_audio
                        )
                        
                        if audio_path:
                            elapsed = time.time() - start
                            logger.info(f"[TTS] ✅ Audio {chunk_idx} in {elapsed:.2f}s")
                            await self.audio_queue.put(('audio', {
                                'path': audio_path,
                                'text': data,
                                'idx': chunk_idx
                            }))
                            chunk_idx += 1
                
                except asyncio.TimeoutError:
                    continue
            
            logger.info("[TTS] ✅ Complete")
        except Exception as e:
            logger.error(f"[TTS] ❌ Error: {e}")
            await self.audio_queue.put(('error', str(e)))
    
    async def video_worker(self, reference_image: str):
        """Worker 3: Stream video chunks"""
        try:
            logger.info("[Video] Started")
            avatar_gen = get_realtime_avatar()
            
            while not self.stop_event.is_set():
                try:
                    msg_type, data = await asyncio.wait_for(self.audio_queue.get(), timeout=1.0)
                    
                    if msg_type == 'done':
                        logger.info("[Video] Done signal")
                        await self.video_queue.put(('done', None))
                        break
                    
                    elif msg_type == 'error':
                        await self.video_queue.put(('error', data))
                        break
                    
                    elif msg_type == 'audio':
                        audio_path = data['path']
                        idx = data['idx']
                        text = data['text']
                        
                        logger.info(f"[Video] Streaming chunk {idx}...")
                        
                        async for video_bytes in avatar_gen.stream_video_chunks(
                            audio_path,
                            reference_image,
                            emotion=4,
                            gaze=True
                        ):
                            await self.video_queue.put(('chunk', {
                                'bytes': video_bytes,
                                'audio_idx': idx,
                                'text': text
                            }))
                        
                        # Cleanup
                        if os.path.exists(audio_path):
                            os.unlink(audio_path)
                
                except asyncio.TimeoutError:
                    continue
            
            logger.info("[Video] ✅ Complete")
        except Exception as e:
            logger.error(f"[Video] ❌ Error: {e}")
            await self.video_queue.put(('error', str(e)))
    
    async def stream_results(self, websocket: WebSocket):
        """Stream results to frontend"""
        first_chunk = True
        start_time = time.time()
        chunk_count = 0
        
        while not self.stop_event.is_set():
            try:
                msg_type, data = await asyncio.wait_for(self.video_queue.get(), timeout=1.0)
                
                if msg_type == 'done':
                    total_time = time.time() - start_time
                    await websocket.send_json({
                        'type': 'complete',
                        'chunks': chunk_count,
                        'total_time': total_time
                    })
                    break
                
                elif msg_type == 'error':
                    await websocket.send_json({
                        'type': 'error',
                        'message': data
                    })
                    break
                
                elif msg_type == 'chunk':
                    elapsed = time.time() - start_time
                    
                    if first_chunk:
                        logger.info(f"🎉 FIRST CHUNK IN: {elapsed:.2f}s")
                        first_chunk = False
                    
                    # Send metadata
                    await websocket.send_json({
                        'type': 'video_meta',
                        'chunk_idx': chunk_count,
                        'audio_idx': data['audio_idx'],
                        'size_kb': len(data['bytes']) / 1024,
                        'elapsed': elapsed,
                        'text': data['text']
                    })
                    
                    # Send binary
                    await websocket.send_bytes(data['bytes'])
                    
                    chunk_count += 1
                    logger.info(f"✅ Chunk {chunk_count} sent ({elapsed:.2f}s)")
            
            except asyncio.TimeoutError:
                continue


@router.websocket("/stream")
async def ultra_fast_stream(websocket: WebSocket):
    """Ultra-fast WebSocket endpoint"""
    await websocket.accept()
    logger.info("🔌 Ultra-fast WebSocket connected")
    
    try:
        # Receive request
        data = await websocket.receive_text()
        request = json.loads(data)
        
        if request.get("type") == "start":
            question = request["question"]
            reference_image = request["reference_image"]
            reference_audio = request["reference_audio"]
            
            logger.info(f"📝 Question: {question}")
            
            await websocket.send_json({
                'type': 'started',
                'message': 'Ultra-fast pipeline started'
            })
            
            # Create orchestrator
            orchestrator = UltraFastOrchestrator()
            
            # Start all workers in parallel
            workers = await asyncio.gather(
                orchestrator.llm_worker(question),
                orchestrator.tts_worker(reference_audio),
                orchestrator.video_worker(reference_image),
                orchestrator.stream_results(websocket),
                return_exceptions=True
            )
            
            logger.info("✅ Pipeline complete")
    
    except WebSocketDisconnect:
        logger.info("🔌 Disconnected")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


@router.get("/status")
async def ultra_fast_status():
    return {
        "status": "ready",
        "mode": "ultra_fast_parallel",
        "target": "<5s first chunk",
        "strategy": "Tiny chunks + parallel processing"
    }

