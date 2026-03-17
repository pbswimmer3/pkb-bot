"""Hybrid search with time-aware and source-weighted ranking."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import numpy as np
from rank_bm25 import BM25Okapi
import re

from kb.database import search_similar_chunks, search_keyword, get_db
from kb.embeddings import generate_embedding
import config


def tokenize(text: str) -> List[str]:
    """Simple tokenization for BM25."""
    return re.findall(r'\b[a-zA-Z]+\b', text.lower())


def calculate_time_score(ingested_at: Optional[str], published_at: Optional[str]) -> float:
    """
    Calculate time-based relevance score.
    Recent documents get higher scores, decaying exponentially.
    """
    date_str = published_at or ingested_at
    if not date_str:
        return 0.5  # Neutral score for undated content
    
    try:
        # Parse the date
        if 'T' in date_str:
            doc_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            doc_date = datetime.strptime(date_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
        
        now = datetime.now(doc_date.tzinfo if doc_date.tzinfo else None)
        age_days = (now - doc_date).days
        
        # Exponential decay
        decay_constant = 1.0 / config.TIME_DECAY_DAYS
        score = np.exp(-decay_constant * age_days)
        
        return float(score)
    except (ValueError, TypeError):
        return 0.5


def get_source_weight(source_type: str) -> float:
    """Get weight for source type."""
    return config.SOURCE_WEIGHTS.get(source_type, 1.0)


def hybrid_search(
    query: str,
    limit: int = None,
    semantic_weight: float = 0.6,
    keyword_weight: float = 0.4,
    time_weight: float = 0.15,
    source_weight_factor: float = 0.1
) -> List[Dict]:
    """
    Perform hybrid search combining semantic and keyword search.
    
    Args:
        query: Search query
        limit: Number of results to return
        semantic_weight: Weight for semantic search (0-1)
        keyword_weight: Weight for keyword search (0-1)
        time_weight: How much to boost recent content (0-1)
        source_weight_factor: How much source type affects ranking (0-1)
    """
    limit = limit or config.DEFAULT_SEARCH_LIMIT
    
    # Get semantic search results
    query_embedding = generate_embedding(query)
    semantic_results = search_similar_chunks(query_embedding, limit=limit * 3)
    
    # Get keyword search results
    keyword_results = search_keyword(query, limit=limit * 3)
    
    # Combine and deduplicate by document ID
    doc_scores: Dict[int, Dict] = {}
    
    # Process semantic results
    for i, result in enumerate(semantic_results):
        doc_id = result["document_id"]
        # Convert distance to similarity (sqlite-vec returns L2 distance)
        # Normalize: closer to 0 = better, so we invert
        distance = result.get("distance", 1.0)
        semantic_score = 1.0 / (1.0 + distance)  # Convert to 0-1 range
        
        if doc_id not in doc_scores:
            doc_scores[doc_id] = {
                "document_id": doc_id,
                "url": result["url"],
                "title": result["title"],
                "source_type": result["source_type"],
                "ingested_at": result["ingested_at"],
                "published_at": result.get("published_at"),
                "semantic_score": semantic_score,
                "keyword_score": 0.0,
                "chunks": []
            }
        else:
            doc_scores[doc_id]["semantic_score"] = max(
                doc_scores[doc_id]["semantic_score"], semantic_score
            )
        
        doc_scores[doc_id]["chunks"].append({
            "content": result["content"],
            "chunk_index": result["chunk_index"],
            "distance": distance
        })
    
    # Process keyword results
    for i, result in enumerate(keyword_results):
        doc_id = result["id"]
        # BM25 rank is lower = better, so invert it
        rank = result.get("rank", i + 1)
        keyword_score = 1.0 / (1.0 + abs(rank) / 10.0)  # Normalize
        
        if doc_id not in doc_scores:
            doc_scores[doc_id] = {
                "document_id": doc_id,
                "url": result["url"],
                "title": result["title"],
                "source_type": result["source_type"],
                "ingested_at": result["ingested_at"],
                "published_at": result.get("published_at"),
                "semantic_score": 0.0,
                "keyword_score": keyword_score,
                "chunks": []
            }
        else:
            doc_scores[doc_id]["keyword_score"] = max(
                doc_scores[doc_id]["keyword_score"], keyword_score
            )
    
    # Calculate final scores
    results = []
    for doc_id, data in doc_scores.items():
        # Base combined score
        combined_score = (
            semantic_weight * data["semantic_score"] +
            keyword_weight * data["keyword_score"]
        )
        
        # Time boost
        time_score = calculate_time_score(data["ingested_at"], data["published_at"])
        time_boost = 1.0 + (time_weight * time_score)
        
        # Source weight
        source_weight = get_source_weight(data["source_type"])
        source_multiplier = 1.0 + (source_weight_factor * (source_weight - 0.5))
        
        # Final score
        final_score = combined_score * time_boost * source_multiplier
        
        results.append({
            "document_id": doc_id,
            "url": data["url"],
            "title": data["title"],
            "source_type": data["source_type"],
            "score": final_score,
            "semantic_score": data["semantic_score"],
            "keyword_score": data["keyword_score"],
            "time_score": time_score,
            "chunks": sorted(data["chunks"], key=lambda x: x["distance"])[:3]  # Top 3 chunks
        })
    
    # Sort by final score and return top results
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def semantic_search_only(query: str, limit: int = None) -> List[Dict]:
    """Perform semantic search only."""
    limit = limit or config.DEFAULT_SEARCH_LIMIT
    query_embedding = generate_embedding(query)
    results = search_similar_chunks(query_embedding, limit=limit)
    
    # Group by document
    doc_results: Dict[int, Dict] = {}
    for r in results:
        doc_id = r["document_id"]
        if doc_id not in doc_results:
            doc_results[doc_id] = {
                "document_id": doc_id,
                "url": r["url"],
                "title": r["title"],
                "source_type": r["source_type"],
                "ingested_at": r["ingested_at"],
                "distance": r["distance"],
                "chunks": []
            }
        doc_results[doc_id]["chunks"].append({
            "content": r["content"],
            "chunk_index": r["chunk_index"]
        })
    
    return list(doc_results.values())


def search_by_entity(entity_name: str, limit: int = None) -> List[Dict]:
    """Search for documents containing a specific entity."""
    limit = limit or config.DEFAULT_SEARCH_LIMIT
    
    conn = get_db()
    cursor = conn.execute(
        """
        SELECT DISTINCT d.* FROM documents d
        JOIN chunks c ON c.document_id = d.id
        WHERE c.entities LIKE ?
        ORDER BY d.ingested_at DESC
        LIMIT ?
        """,
        (f'%"text": "{entity_name}"%', limit)
    )
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results
