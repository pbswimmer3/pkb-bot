"""Text chunking with semantic boundaries."""
from typing import List, Dict
import re
import config


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Chunk text with semantic awareness.
    Tries to break at sentence boundaries when possible.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        
        # Try to find a good break point
        # Look for sentence endings within the last 20% of the chunk
        search_start = end - int(chunk_size * 0.2)
        search_text = text[search_start:end]
        
        # Find the last sentence ending
        sentence_end = -1
        for match in re.finditer(r'[.!?]\s+', search_text):
            sentence_end = match.end()
        
        if sentence_end > 0:
            end = search_start + sentence_end
        else:
            # Try to break at a space
            space_idx = text.rfind(' ', search_start, end)
            if space_idx > search_start:
                end = space_idx + 1
        
        chunks.append(text[start:end].strip())
        start = end - overlap
    
    return chunks


def chunk_with_metadata(text: str, chunk_size: int = None, overlap: int = None) -> List[Dict]:
    """Chunk text and return with position metadata."""
    chunks = chunk_text(text, chunk_size, overlap)
    return [
        {
            "content": chunk,
            "index": i,
            "start_char": sum(len(c) for c in chunks[:i]),
            "end_char": sum(len(c) for c in chunks[:i+1])
        }
        for i, chunk in enumerate(chunks)
    ]
