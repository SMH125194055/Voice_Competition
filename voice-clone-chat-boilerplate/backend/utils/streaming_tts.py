"""
Streaming TTS utility for real-time voice responses.
Generates and yields audio in chunks for progressive playback.
"""

import os
import logging
import tempfile
import torch
import torchaudio as ta
from typing import Optional, Generator, AsyncGenerator
import asyncio

logger = logging.getLogger(__name__)


async def stream_text_to_speech(
    text: str, 
    chatterbox_model, 
    reference_audio_path: Optional[str] = None,
    chunk_duration: float = 5.0  # seconds per chunk
) -> AsyncGenerator[bytes, None]:
    """
    Generate speech audio in chunks for streaming.
    
    Args:
        text: Text to synthesize
        chatterbox_model: Loaded ChatterBox model
        reference_audio_path: Path to reference audio for voice cloning
        chunk_duration: Duration of each audio chunk in seconds
        
    Yields:
        Audio chunks as bytes
    """
    try:
        logger.info(f"Starting streaming TTS for text: {text[:50]}...")
        
        # Generate full audio (ChatterBox doesn't support true streaming yet)
        # But we can split it into chunks after generation
        if reference_audio_path and os.path.exists(reference_audio_path):
            logger.info(f"Using reference voice: {reference_audio_path}")
            wav = chatterbox_model.generate(
                text,
                audio_prompt_path=reference_audio_path,
                temperature=0.1,
                cfg_weight=0.1,
                repetition_penalty=1.1,
            )
        else:
            logger.info("Using default voice")
            wav = chatterbox_model.generate(text)
        
        # Get sample rate
        sr = chatterbox_model.sr
        
        # Calculate samples per chunk
        samples_per_chunk = int(chunk_duration * sr)
        
        # Split audio into chunks
        audio_tensor = wav.squeeze(0)  # Remove batch dimension
        total_samples = audio_tensor.shape[0]
        
        logger.info(f"Audio generated: {total_samples} samples, splitting into {chunk_duration}s chunks")
        
        # Yield chunks
        for start_idx in range(0, total_samples, samples_per_chunk):
            end_idx = min(start_idx + samples_per_chunk, total_samples)
            chunk = audio_tensor[start_idx:end_idx].unsqueeze(0)  # Add batch dimension back
            
            # Save chunk to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_path = temp_file.name
            temp_file.close()
            
            ta.save(temp_path, chunk, sr)
            
            # Read chunk as bytes
            with open(temp_path, 'rb') as f:
                chunk_bytes = f.read()
            
            # Cleanup temp file
            os.unlink(temp_path)
            
            # Yield chunk
            chunk_num = (start_idx // samples_per_chunk) + 1
            total_chunks = (total_samples + samples_per_chunk - 1) // samples_per_chunk
            logger.info(f"Yielding chunk {chunk_num}/{total_chunks} ({len(chunk_bytes)} bytes)")
            
            yield chunk_bytes
            
            # Small delay to simulate streaming (remove in production)
            await asyncio.sleep(0.1)
        
        logger.info("Streaming TTS complete")
        
    except Exception as e:
        logger.error(f"Streaming TTS failed: {e}")
        raise


def split_text_into_sentences(text: str) -> list:
    """
    Split text into sentences for progressive generation.
    
    Args:
        text: Input text
        
    Returns:
        List of sentences
    """
    import re
    
    # Split by sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Filter empty strings
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences


async def stream_text_to_speech_by_sentence(
    text: str,
    chatterbox_model,
    reference_audio_path: Optional[str] = None
) -> AsyncGenerator[tuple[str, bytes], None]:
    """
    Generate speech sentence by sentence for faster perceived response.
    
    Args:
        text: Full text to synthesize
        chatterbox_model: Loaded ChatterBox model
        reference_audio_path: Path to reference audio
        
    Yields:
        Tuples of (sentence_text, audio_bytes)
    """
    sentences = split_text_into_sentences(text)
    
    logger.info(f"Splitting into {len(sentences)} sentences for progressive generation")
    
    for idx, sentence in enumerate(sentences, 1):
        logger.info(f"Generating sentence {idx}/{len(sentences)}: {sentence[:30]}...")
        
        try:
            # Generate audio for this sentence
            if reference_audio_path and os.path.exists(reference_audio_path):
                wav = chatterbox_model.generate(
                    sentence,
                    audio_prompt_path=reference_audio_path,
                    temperature=0.1,
                    cfg_weight=0.1,
                    repetition_penalty=1.1,
                )
            else:
                wav = chatterbox_model.generate(sentence)
            
            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            temp_path = temp_file.name
            temp_file.close()
            
            ta.save(temp_path, wav, chatterbox_model.sr)
            
            # Read as bytes
            with open(temp_path, 'rb') as f:
                audio_bytes = f.read()
            
            # Cleanup
            os.unlink(temp_path)
            
            # Yield sentence and its audio
            yield (sentence, audio_bytes)
            
        except Exception as e:
            logger.error(f"Failed to generate sentence {idx}: {e}")
            # Continue with next sentence
            continue
    
    logger.info("Sentence-by-sentence generation complete")


