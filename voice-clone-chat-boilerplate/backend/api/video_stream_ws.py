"""
WebSocket Video Streaming API
Streams avatar videos directly without disk I/O
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
import asyncio
import logging
import json
import time
import os
import tempfile

from utils.ditto_streaming_generator import get_streaming_generator
from utils import text_to_speech, chat_with_llm_streaming, initialize_tts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stream", tags=["Video Streaming"])


@router.websocket("/video")
async def websocket_video_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time video streaming
    
    Client sends:
    {
        "type": "start",
        "question": "Your question here",
        "reference_image": "/path/to/image.jpg",
        "reference_audio": "/path/to/audio.wav"
    }
    
    Server streams back:
    - Binary video chunks
    - JSON status messages
    """
    await websocket.accept()
    logger.info("🔌 WebSocket connected")
    
    try:
        # Get streaming generator
        generator = get_streaming_generator()
        
        while True:
            # Receive request
            data = await websocket.receive_text()
            request = json.loads(data)
            
            if request.get("type") == "start":
                question = request["question"]
                reference_image = request["reference_image"]
                reference_audio = request["reference_audio"]
                
                logger.info(f"📝 Question: {question}")
                
                # Send started event
                await websocket.send_json({
                    "type": "started",
                    "message": "Pipeline started"
                })
                
                start_time = time.time()
                chunk_count = 0
                first_video_time = None
                
                # Initialize TTS
                mode = os.getenv("MODE", "local")
                initialize_tts(mode, reference_audio)
                
                # Process LLM response streaming
                text_buffer = ""
                min_chunk_chars = 80
                sentence_endings = ['.', '!', '?', '\n']
                
                async for llm_chunk in chat_with_llm_streaming(question):
                    text_buffer += llm_chunk
                    
                    # Check if we should process this chunk
                    should_process = (
                        len(text_buffer) >= min_chunk_chars and
                        any(text_buffer.endswith(end) for end in sentence_endings)
                    ) or len(text_buffer) > 200
                    
                    if should_process:
                        text = text_buffer.strip()
                        text_buffer = ""
                        
                        logger.info(f"🎙️ TTS: {text[:50]}...")
                        
                        # Generate audio
                        audio_path = await text_to_speech(
                            text=text,
                            mode=mode,
                            reference_audio_path=reference_audio
                        )
                        
                        if not audio_path or not os.path.exists(audio_path):
                            logger.error("TTS failed")
                            continue
                        
                        logger.info(f"🎬 Generating video chunk {chunk_count}...")
                        
                        # Generate video IN-MEMORY
                        video_start = time.time()
                        video_bytes = await asyncio.get_event_loop().run_in_executor(
                            None,
                            generator.generate_video_bytes,
                            audio_path,
                            reference_image
                        )
                        video_elapsed = time.time() - video_start
                        
                        if first_video_time is None:
                            first_video_time = time.time() - start_time
                            logger.info(f"🎉 FIRST VIDEO IN: {first_video_time:.2f}s")
                        
                        # Send video metadata
                        await websocket.send_json({
                            "type": "video_chunk",
                            "chunk_idx": chunk_count,
                            "size_bytes": len(video_bytes),
                            "size_mb": len(video_bytes) / 1024 / 1024,
                            "generation_time": video_elapsed,
                            "total_elapsed": time.time() - start_time,
                            "text": text
                        })
                        
                        # Send video data (binary)
                        await websocket.send_bytes(video_bytes)
                        
                        logger.info(f"✅ Video chunk {chunk_count} sent ({len(video_bytes)/1024/1024:.2f}MB in {video_elapsed:.2f}s)")
                        
                        chunk_count += 1
                        
                        # Cleanup temp audio
                        if os.path.exists(audio_path):
                            os.unlink(audio_path)
                
                # Send any remaining text
                if text_buffer.strip():
                    # ... (same process for final chunk)
                    pass
                
                # Send complete event
                total_time = time.time() - start_time
                await websocket.send_json({
                    "type": "complete",
                    "total_chunks": chunk_count,
                    "total_time": total_time,
                    "first_video_time": first_video_time
                })
                
                logger.info(f"🎊 Complete: {chunk_count} videos in {total_time:.2f}s")
    
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


@router.post("/test-generate")
async def test_generate():
    """
    HTTP endpoint to test in-memory video generation
    Returns the video directly as bytes
    """
    generator = get_streaming_generator()
    
    # Use test files
    reference_image = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/Avatar/References/ref_1761131562372.jpg"
    reference_audio = "/home/syedhuzaifa/Voice_Competition/voice-clone-chat-boilerplate/backend/audio/reference_voices/ref_1761118578.wav"
    
    # Generate short test audio
    import uuid
    test_audio_path = f"/tmp/test_audio_{uuid.uuid4().hex[:8]}.wav"
    
    # Use actual TTS
    mode = os.getenv("MODE", "local")
    initialize_tts(mode, reference_audio)
    
    audio_path = await text_to_speech(
        text="This is a test of in-memory video generation.",
        mode=mode,
        reference_audio_path=reference_audio
    )
    
    if not audio_path:
        return {"error": "TTS failed"}
    
    # Generate video in-memory
    logger.info("🎬 Generating test video in-memory...")
    start_time = time.time()
    
    video_bytes = await asyncio.get_event_loop().run_in_executor(
        None,
        generator.generate_video_bytes,
        audio_path,
        reference_image
    )
    
    elapsed = time.time() - start_time
    
    logger.info(f"✅ Generated {len(video_bytes)/1024/1024:.2f}MB in {elapsed:.2f}s")
    
    # Cleanup
    if os.path.exists(audio_path):
        os.unlink(audio_path)
    
    # Return video directly
    return Response(
        content=video_bytes,
        media_type="video/mp4",
        headers={
            "Content-Disposition": "inline; filename=test_video.mp4",
            "X-Generation-Time": str(elapsed),
            "X-Video-Size-MB": str(len(video_bytes)/1024/1024)
        }
    )


@router.get("/status")
async def streaming_status():
    """Check if streaming generator is ready"""
    try:
        generator = get_streaming_generator()
        return {
            "status": "ready",
            "initialized": generator.initialized,
            "mode": "in_memory_streaming",
            "disk_io": False
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

