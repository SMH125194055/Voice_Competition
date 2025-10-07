"""
LLM utility for chat using Qlu AI library.
"""

import os
import logging
from typing import List, Dict, Optional

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


