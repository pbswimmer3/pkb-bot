"""Ingestion handlers for different content types."""
from kb.database import insert_document, insert_chunk, update_entities
from kb.embeddings import generate_embeddings
from kb.entities import extract_entities, extract_entities_batch
from kb.chunking import chunk_text
from typing import Dict, Optional
import re


def process_and_store(
    url: str,
    source_type: str,
    title: Optional[str],
    content: str,
    author: Optional[str] = None,
    published_at: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> int:
    """
    Process content: chunk, extract entities, generate embeddings, store.
    Returns document ID.
    """
    # Insert document
    doc_id = insert_document(
        url=url,
        source_type=source_type,
        title=title,
        content=content,
        author=author,
        published_at=published_at,
        metadata=metadata
    )
    
    # Chunk content
    chunks = chunk_text(content)
    
    if not chunks:
        return doc_id
    
    # Extract entities for all chunks
    chunk_entities = extract_entities_batch(chunks)
    
    # Generate embeddings for all chunks
    chunk_embeddings = generate_embeddings(chunks)
    
    # Store chunks with embeddings
    all_entities = []
    for i, (chunk_text_content, embedding, entities) in enumerate(zip(chunks, chunk_embeddings, chunk_entities)):
        insert_chunk(
            document_id=doc_id,
            content=chunk_text_content,
            chunk_index=i,
            embedding=embedding,
            entities=entities
        )
        all_entities.extend(entities)
    
    # Update entity table
    if all_entities:
        update_entities(all_entities, doc_id)
    
    return doc_id


def extract_url_from_text(text: str) -> Optional[str]:
    """Extract URL from text."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    match = re.search(url_pattern, text)
    return match.group(0) if match else None


def detect_source_type(url: str) -> str:
    """Detect source type from URL."""
    url_lower = url.lower()
    
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif url_lower.endswith('.pdf'):
        return 'pdf'
    else:
        return 'article'
