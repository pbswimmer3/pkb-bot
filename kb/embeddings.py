"""Embedding generation using sentence-transformers."""
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
import config

# Lazy-loaded model
_model = None


def get_model() -> SentenceTransformer:
    """Get or initialize the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for a single text."""
    model = get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts."""
    model = get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
