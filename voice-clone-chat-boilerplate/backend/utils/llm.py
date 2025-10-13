"""
LLM utility for chat using Qlu AI library.
"""

import os
import logging
from typing import List, Dict, Optional, AsyncGenerator

logger = logging.getLogger(__name__)



async def chat_with_llm(
    message: str,
    model: str = "groq/llama-3.1-8b-instant",
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> str:
    """
    Send a message to the LLM and get a response using Qlu AI library.
    
    Args:
        message: User message
        model: Model name (e.g., "openai/gpt-4.1-mini-2025-04-14")
        system_prompt: Optional system prompt
        conversation_history: Optional list of previous messages
        temperature: Temperature for response randomness (0-1)
        max_tokens: Maximum tokens in response
        
    Returns:
        LLM response text
    """
    try:
        from qutils.llm.asynchronous import invoke
        
        # Get Qlu API configuration
        qlu_api_key = os.getenv("QLU_API_KEY")
        llm_environment = os.getenv("LLM_ENVIRONMENT", "local")
        gateway_url = os.getenv("LLM_PROXY_GATEWAY_URL")
        
        if not qlu_api_key:
            raise ValueError("QLU_API_KEY not set in environment")
        
        # Build messages array
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            # Default system prompt for voice assistant
            messages.append({
                "role": "system",
                "content": "You are a helpful voice assistant. Provide clear, concise, and natural responses suitable for speech synthesis."
            })
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        logger.info(f"Sending message to LLM (Qlu): {message[:100]}...")
        logger.info(f"Using model: {model}, environment: {llm_environment}")
        
        # Call Qlu AI library invoke function
        response_data = await invoke(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
            verbose=True
        )
        
        # Extract reply from response
        reply = response_data["choices"][0]["message"]["content"].strip()
        
        # Log token usage if available
        if "usage" in response_data:
            usage = response_data["usage"]
            logger.info(
                f"Token usage - Input: {usage.get('prompt_tokens', 0)}, "
                f"Output: {usage.get('completion_tokens', 0)}, "
                f"Total: {usage.get('total_tokens', 0)}"
            )
        
        logger.info(f"LLM response: {reply[:100]}...")
        
        return reply
        
    except Exception as e:
        logger.error(f"LLM chat failed: {e}")
        raise


async def chat_with_llm_streaming(
    message: str,
    model: str = "groq/llama-3.1-8b-instant",
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    chunk_size: int = 15  # Words per chunk
) -> AsyncGenerator[str, None]:
    """
    Stream LLM response in chunks for immediate audio generation.
    
    Yields text chunks as soon as they're available from the LLM.
    This allows parallel audio generation while LLM is still generating.
    
    Args:
        message: User message
        model: Model name
        system_prompt: Optional system prompt
        conversation_history: Optional conversation history
        temperature: Temperature for randomness
        max_tokens: Max tokens in response
        chunk_size: Words per chunk to yield
        
    Yields:
        Text chunks suitable for audio generation
    """
    try:
        from qutils.llm.asynchronous import invoke, stream
        
        # Get configuration
        qlu_api_key = os.getenv("QLU_API_KEY")
        
        if not qlu_api_key:
            raise ValueError("QLU_API_KEY not set in environment")
        
        # Build messages
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system",
                "content": "You are a helpful voice assistant. Provide clear, concise responses suitable for speech synthesis."
            })
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": message})
        
        logger.info(f"🚀 Streaming LLM request: {message[:100]}...")
        
        # Try TRUE streaming first using the stream() function
        try:
            logger.info("✅ Using Qlu stream() function")
            buffer = []
            word_count = 0
            
            # Use the dedicated stream() function from Qlu library
            async for chunk in stream(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=messages,
                verbose=False
            ):
                # Extract content from chunk (chunk is just the text string)
                content = str(chunk) if chunk else ''
                
                if content:
                    words = content.split()
                    buffer.extend(words)
                    word_count += len(words)
                    
                    # Yield chunks of specified size
                    while len(buffer) >= chunk_size:
                        chunk_text = ' '.join(buffer[:chunk_size])
                        buffer = buffer[chunk_size:]
                        logger.info(f"📤 Streaming chunk ({len(chunk_text)} chars): {chunk_text[:50]}...")
                        yield chunk_text
            
            # Yield remaining words
            if buffer:
                chunk_text = ' '.join(buffer)
                logger.info(f"📤 Final chunk ({len(chunk_text)} chars): {chunk_text[:50]}...")
                yield chunk_text
            
            logger.info(f"✅ Streaming complete ({word_count} words total)")
            return
                
        except Exception as stream_error:
            logger.warning(f"⚠️ Streaming failed, falling back to non-streaming: {stream_error}")
        
        # Fallback: Non-streaming mode (get full response and chunk it)
        logger.info("🔄 Using non-streaming mode with manual chunking")
        response_data = await invoke(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
            verbose=True  # Get full response object
        )
        
        # Extract full response - handle different response formats
        if isinstance(response_data, str):
            # Direct string response
            reply = response_data.strip()
        elif isinstance(response_data, dict):
            # Response object format
            if "choices" in response_data:
                reply = response_data["choices"][0]["message"]["content"].strip()
            elif "content" in response_data:
                reply = response_data["content"].strip()
            else:
                # Unknown format, try to extract text
                reply = str(response_data).strip()
        else:
            reply = str(response_data).strip()
        
        logger.info(f"📥 Got full response ({len(reply)} chars)")
        
        # Chunk the response manually
        words = reply.split()
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            logger.info(f"📤 Chunk {i//chunk_size + 1}: {chunk_text[:50]}...")
            yield chunk_text
        
        logger.info("✅ Chunking complete")
        
    except Exception as e:
        logger.error(f"❌ Streaming LLM failed: {e}")
        raise


