"""LLM integration for RAG queries via OpenClaw gateway."""
import os
import json
import aiohttp
from typing import List, Dict, Optional

# OpenClaw gateway configuration
OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://host.docker.internal:18789")
OPENCLAW_API_KEY = os.getenv("OPENCLAW_API_KEY", "")
OPENCLAW_AGENT_ID = os.getenv("OPENCLAW_AGENT_ID", "main")

# Default model for RAG synthesis
# Use "openclaw" to let the gateway handle model routing internally
DEFAULT_RAG_MODEL = os.getenv("RAG_MODEL", "openclaw")


async def call_openclaw_llm(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = 0.3,
    max_tokens: int = 1500
) -> Optional[str]:
    """
    Call OpenClaw gateway for LLM completion.
    
    Args:
        messages: List of {role: str, content: str} dicts
        model: Model identifier (defaults to DEFAULT_RAG_MODEL)
        temperature: Sampling temperature
        max_tokens: Max response tokens
    
    Returns:
        Generated text or None on error
    """
    model = model or DEFAULT_RAG_MODEL
    
    # OpenClaw uses a simpler API format
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-openclaw-agent-id": OPENCLAW_AGENT_ID,
    }
    if OPENCLAW_API_KEY:
        headers["Authorization"] = f"Bearer {OPENCLAW_API_KEY}"

    # Only one correct endpoint for OpenClaw gateway
    endpoints = [
        f"{OPENCLAW_GATEWAY_URL}/v1/chat/completions",
    ]
    
    last_error = None
    for endpoint in endpoints:
        try:
            print(f"Trying OpenClaw endpoint: {endpoint}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    print(f"Response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"Response data keys: {data.keys() if isinstance(data, dict) else 'not dict'}")
                        # Handle different response formats
                        if "choices" in data:
                            return data["choices"][0].get("message", {}).get("content")
                        elif "response" in data:
                            return data["response"]
                        elif "content" in data:
                            return data["content"]
                        else:
                            return str(data)
                    else:
                        error_text = await response.text()
                        print(f"OpenClaw LLM error: {response.status} - {error_text[:200]}")
                        last_error = f"{response.status}: {error_text[:200]}"
        except Exception as e:
            print(f"Error with endpoint {endpoint}: {e}")
            last_error = str(e)
            continue
    
    print(f"All endpoints failed. Last error: {last_error}")
    return None


def build_rag_prompt(query: str, chunks: List[Dict]) -> str:
    """
    Build RAG prompt with retrieved context.
    
    Args:
        query: User's natural language question
        chunks: Retrieved chunks with content, source, title, url
    
    Returns:
        Formatted prompt for LLM
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source_type", "unknown")
        title = chunk.get("title", "Untitled")
        content = chunk.get("content", "")
        url = chunk.get("url", "")
        
        context_parts.append(
            f"[{i}] Source: {source} | Title: {title}\n"
            f"URL: {url}\n"
            f"Content: {content[:800]}...\n"
        )
    
    context = "\n---\n".join(context_parts)
    
    prompt = f"""You are a helpful research assistant answering questions based on the user's personal knowledge base.

## Retrieved Context
{context}

## User Question
{query}

## Instructions
1. Answer the question using ONLY the provided context
2. If the context doesn't contain enough information, say so clearly
3. Cite sources using [1], [2], etc. when referencing information
4. Be concise but thorough
5. If multiple sources conflict, note the discrepancy

## Answer"""
    
    return prompt


async def rag_query(
    query: str,
    chunks: List[Dict],
    model: str = None
) -> Dict:
    """
    Perform RAG query: synthesize answer from retrieved chunks.
    
    Args:
        query: User's natural language question
        chunks: Retrieved chunks from hybrid_search
        model: Optional model override
    
    Returns:
        Dict with answer, citations, and metadata
    """
    if not chunks:
        return {
            "answer": "I couldn't find any relevant documents in your knowledge base to answer this question.",
            "citations": [],
            "sources": [],
            "model_used": None
        }
    
    # Build prompt with context
    prompt = build_rag_prompt(query, chunks)
    
    # Call LLM
    messages = [
        {"role": "system", "content": "You are a helpful research assistant. Answer based only on the provided context."},
        {"role": "user", "content": prompt}
    ]
    
    answer = await call_openclaw_llm(messages, model=model)
    
    if not answer:
        return {
            "answer": "Sorry, I encountered an error generating the answer. The search results are available above.",
            "citations": [],
            "sources": [],
            "model_used": None,
            "error": True
        }
    
    # Extract unique sources for citation list
    sources = []
    seen_urls = set()
    for chunk in chunks:
        url = chunk.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append({
                "title": chunk.get("title", "Untitled"),
                "url": url,
                "source_type": chunk.get("source_type", "unknown")
            })
    
    return {
        "answer": answer,
        "citations": list(range(1, len(sources) + 1)),
        "sources": sources,
        "model_used": model or DEFAULT_RAG_MODEL
    }


async def rewrite_query_for_search(original_query: str, model: str = None) -> str:
    """
    Use LLM to rewrite vague/ambiguous queries into better search terms.
    
    Args:
        original_query: User's raw query
        model: Optional model override
    
    Returns:
        Optimized search query
    """
    # Simple heuristic: if query is very short or lacks keywords, rewrite
    if len(original_query.split()) >= 4 and any(c.isalpha() for c in original_query):
        # Likely specific enough
        return original_query
    
    messages = [
        {"role": "system", "content": "You optimize search queries for semantic search. Expand abbreviations, add synonyms, and clarify intent. Output ONLY the optimized query, nothing else."},
        {"role": "user", "content": f"Original query: {original_query}\n\nOptimized search query:"}
    ]
    
    rewritten = await call_openclaw_llm(messages, model=model, temperature=0.1, max_tokens=100)
    
    return rewritten.strip() if rewritten else original_query
