"""
Text chunking utilities for streaming TTS.
Splits text into optimal chunks for progressive audio generation.
"""

import re
from typing import List, Tuple


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Simple sentence splitting on common punctuation
    sentences = re.split(r'([.!?]+\s+)', text)
    
    # Recombine sentences with their punctuation
    result = []
    for i in range(0, len(sentences), 2):
        if i + 1 < len(sentences):
            result.append(sentences[i] + sentences[i + 1])
        else:
            result.append(sentences[i])
    
    return [s.strip() for s in result if s.strip()]


def chunk_text_by_words(
    text: str, 
    min_words: int = 6, 
    max_words: int = 20,
    preserve_sentences: bool = True
) -> List[Tuple[str, int, int]]:
    """
    Split text into chunks of optimal size for streaming TTS.
    
    Args:
        text: Input text to chunk
        min_words: Minimum words per chunk
        max_words: Maximum words per chunk
        preserve_sentences: Try to keep sentences intact
        
    Returns:
        List of tuples: (chunk_text, start_char_index, end_char_index)
    """
    chunks = []
    
    if preserve_sentences:
        # First split into sentences
        sentences = split_into_sentences(text)
        
        current_chunk = []
        current_word_count = 0
        char_position = 0
        chunk_start = 0
        
        for sentence in sentences:
            sentence_words = sentence.split()
            sentence_word_count = len(sentence_words)
            
            # If adding this sentence exceeds max_words, finalize current chunk
            if current_word_count + sentence_word_count > max_words and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunk_end = char_position
                chunks.append((chunk_text, chunk_start, chunk_end))
                
                current_chunk = []
                current_word_count = 0
                chunk_start = char_position
            
            # Add sentence to current chunk
            current_chunk.extend(sentence_words)
            current_word_count += sentence_word_count
            char_position += len(sentence) + 1  # +1 for space
            
            # If chunk is at least min_words, consider finalizing
            if current_word_count >= min_words:
                # Check if next sentence would exceed max_words
                # If so, finalize now
                pass  # Continue accumulating until max_words
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append((chunk_text, chunk_start, len(text)))
    
    else:
        # Simple word-based chunking
        words = text.split()
        char_position = 0
        
        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunk_text = ' '.join(chunk_words)
            chunk_start = char_position
            char_position += len(chunk_text) + 1
            chunks.append((chunk_text, chunk_start, char_position))
    
    return chunks


def chunk_text_by_punctuation(
    text: str,
    max_chars: int = 150,
    preferred_breaks: str = '.!?,;:'
) -> List[Tuple[str, int, int]]:
    """
    Split text at natural break points (punctuation).
    
    Args:
        text: Input text
        max_chars: Maximum characters per chunk
        preferred_breaks: Punctuation marks to break on
        
    Returns:
        List of tuples: (chunk_text, start_char_index, end_char_index)
    """
    chunks = []
    current_chunk = ""
    chunk_start = 0
    
    i = 0
    while i < len(text):
        current_chunk += text[i]
        
        # Check if we hit a break point and chunk is reasonable size
        if text[i] in preferred_breaks and len(current_chunk) >= 30:
            # Look ahead to include trailing space
            if i + 1 < len(text) and text[i + 1] == ' ':
                current_chunk += ' '
                i += 1
            
            chunks.append((current_chunk.strip(), chunk_start, i + 1))
            current_chunk = ""
            chunk_start = i + 1
        
        # Force break if chunk too long
        elif len(current_chunk) >= max_chars:
            # Try to break at last space
            last_space = current_chunk.rfind(' ')
            if last_space > 0:
                chunks.append((current_chunk[:last_space].strip(), chunk_start, chunk_start + last_space))
                current_chunk = current_chunk[last_space + 1:]
                chunk_start = chunk_start + last_space + 1
            else:
                # No space found, hard break
                chunks.append((current_chunk.strip(), chunk_start, i + 1))
                current_chunk = ""
                chunk_start = i + 1
        
        i += 1
    
    # Add remaining text
    if current_chunk.strip():
        chunks.append((current_chunk.strip(), chunk_start, len(text)))
    
    return chunks


def get_word_timestamps(text: str, chunk_info: List[Tuple[str, int, int]]) -> List[dict]:
    """
    Generate approximate word-level timestamps for highlighting.
    
    Args:
        text: Full text
        chunk_info: List of (chunk_text, start_char, end_char)
        
    Returns:
        List of dicts with word, start_char, end_char, chunk_index
    """
    word_timestamps = []
    
    for chunk_idx, (chunk_text, chunk_start, chunk_end) in enumerate(chunk_info):
        words = chunk_text.split()
        char_pos = chunk_start
        
        for word in words:
            # Find word position in original text
            word_start = text.find(word, char_pos)
            if word_start != -1:
                word_end = word_start + len(word)
                word_timestamps.append({
                    'word': word,
                    'start_char': word_start,
                    'end_char': word_end,
                    'chunk_index': chunk_idx
                })
                char_pos = word_end
    
    return word_timestamps



