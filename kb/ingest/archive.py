"""Wayback Machine integration for paywall bypass."""
import requests
import time
from typing import Optional
from urllib.parse import quote


def get_archive_url(url: str) -> Optional[str]:
    """
    Get Wayback Machine archive URL for a given URL.
    Returns the archive URL if available, None otherwise.
    """
    try:
        # Wayback Machine availability API
        # Returns the closest snapshot to now
        encoded_url = quote(url, safe='')
        api_url = f"https://archive.org/wayback/available?url={encoded_url}"
        
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'archived_snapshots' in data and 'closest' in data['archived_snapshots']:
            snapshot = data['archived_snapshots']['closest']
            if snapshot.get('available') and snapshot.get('url'):
                return snapshot['url']
        
        return None
        
    except Exception as e:
        print(f"Archive lookup failed for {url}: {e}")
        return None


def get_archive_url_with_fallback(url: str) -> str:
    """
    Get archive URL or return original URL if no archive exists.
    Logs when fallback is used.
    """
    archive_url = get_archive_url(url)
    
    if archive_url:
        print(f"[Archive] Using Wayback Machine: {url}")
        return archive_url
    else:
        print(f"[Archive] No archive found, using direct: {url}")
        return url


def save_to_archive(url: str) -> bool:
    """
    Submit URL to Wayback Machine for archiving.
    Returns True if submission accepted.
    """
    try:
        # Wayback Machine save page now
        save_url = f"https://web.archive.org/save/{url}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(save_url, headers=headers, timeout=30, allow_redirects=True)
        # 200 or 302 usually means success
        return response.status_code in [200, 302]
        
    except Exception as e:
        print(f"Archive save failed for {url}: {e}")
        return False
