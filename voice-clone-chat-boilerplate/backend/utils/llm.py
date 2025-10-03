"""
LLM utility for chat using OpenRouter API.
"""

import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


async def chat_with_llm(
    message: str,
    model: str = "openai/gpt-3.5-turbo",
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Send a message to the LLM and get a response.
    
    Args:
        message: User message
        model: Model name (e.g., "openai/gpt-3.5-turbo", "anthropic/claude-2")
        system_prompt: Optional system prompt
        conversation_history: Optional list of previous messages
        
    Returns:
        LLM response text
    """
    try:
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        
        # Create client with minimal parameters for compatibility
        client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            default_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "Voice Chat App"}
        )
        
        # Build messages array
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        logger.info(f"Sending message to LLM: {message[:100]}...")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        
        reply = response.choices[0].message.content.strip()
        logger.info(f"LLM response: {reply[:100]}...")
        
        return reply
        
    except Exception as e:
        logger.error(f"LLM chat failed: {e}")
        raise


