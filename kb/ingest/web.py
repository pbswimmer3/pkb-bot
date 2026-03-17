"""Web article extraction."""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
from urllib.parse import urlparse
import re
from .archive import get_archive_url_with_fallback


def extract_article(url: str) -> Optional[Dict]:
    """
    Extract article content from URL.
    Returns dict with title, content, author, published_at.
    """
    try:
        # Try archive.org first for paywall bypass
        url_to_fetch = get_archive_url_with_fallback(url)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url_to_fetch, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Extract title
        title = None
        if soup.find('meta', property='og:title'):
            title = soup.find('meta', property='og:title')['content']
        elif soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)
        elif soup.title:
            title = soup.title.get_text(strip=True)
        
        # Extract author
        author = None
        if soup.find('meta', attrs={'name': 'author'}):
            author = soup.find('meta', attrs={'name': 'author'})['content']
        elif soup.find('meta', property='article:author'):
            author = soup.find('meta', property='article:author')['content']
        
        # Extract published date
        published_at = None
        if soup.find('meta', property='article:published_time'):
            published_at = soup.find('meta', property='article:published_time')['content']
        elif soup.find('meta', attrs={'name': 'publishedDate'}):
            published_at = soup.find('meta', attrs={'name': 'publishedDate'})['content']
        
        # Extract main content
        content = extract_main_content(soup)
        
        if not content or len(content) < 100:
            return None
        
        return {
            'title': title or 'Untitled',
            'content': content,
            'author': author,
            'published_at': published_at
        }
        
    except Exception as e:
        print(f"Error extracting article from {url}: {e}")
        return None


def extract_main_content(soup: BeautifulSoup) -> str:
    """Extract main article content from BeautifulSoup object."""
    
    # Try common article containers
    article_tags = [
        soup.find('article'),
        soup.find('main'),
        soup.find('div', class_=re.compile('article|content|post|entry', re.I)),
        soup.find('div', id=re.compile('article|content|post|entry', re.I)),
    ]
    
    for tag in article_tags:
        if tag:
            text = tag.get_text(separator='\n', strip=True)
            if len(text) > 500:
                return clean_text(text)
    
    # Fallback: extract from body
    body = soup.find('body')
    if body:
        text = body.get_text(separator='\n', strip=True)
        return clean_text(text)
    
    # Last resort
    return clean_text(soup.get_text(separator='\n', strip=True))


def clean_text(text: str) -> str:
    """Clean extracted text."""
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Remove common ad/tracking text patterns
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip very short lines that are likely UI elements
        if len(line) < 3:
            continue
        # Skip common cookie/privacy notices
        if any(x in line.lower() for x in ['cookie', 'privacy policy', 'terms of service', 'subscribe to']):
            continue
        cleaned_lines.append(line)
    
    return '\n\n'.join(cleaned_lines)
