"""Article summarization using OpenClaw LLM."""
import os
import json
import requests
from typing import Optional


def summarize_article(content: str, title: str = "") -> Optional[str]:
    """
    Generate a 3-5 bullet point summary of article content.
    Returns markdown-formatted summary or None on error.
    """
    try:
        # Get OpenClaw gateway config from environment
        gateway_url = os.getenv("OPENCLAW_GATEWAY_URL", "http://172.18.0.1:18789")
        api_key = os.getenv("OPENCLAW_API_KEY", "")
        
        # Truncate content if too long (keep first 8000 chars for context)
        truncated_content = content[:8000] if len(content) > 8000 else content
        
        prompt = f"""Summarize this article in 3-5 concise bullet points (Executive Summary style).

Title: {title}

Content:
{truncated_content}

Provide only the bullet points, no introduction or conclusion."""

        headers = {
            "Content-Type": "application/json",
            "x-openclaw-agent-id": "main",
        }
        
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        payload = {
            "model": "openclaw",
            "messages": [
                {"role": "system", "content": "You create concise executive summaries."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        response = requests.post(
            f"{gateway_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            summary = data["choices"][0]["message"]["content"].strip()
            # Ensure it starts with bullet points
            if not summary.startswith("•") and not summary.startswith("-"):
                summary = "• " + summary.replace("\n", "\n• ")
            return summary
        
        return None
        
    except Exception as e:
        print(f"Summarization failed: {e}")
        return None


def format_summary_for_discord(title: str, summary: str, source_url: str) -> str:
    """
    Format summary for Discord message.
    """
    return f"**📄 Summary: {title}**\n\n{summary}\n\n*Source: <{source_url}>*"
