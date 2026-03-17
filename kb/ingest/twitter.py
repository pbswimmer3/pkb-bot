"""X/Twitter thread extraction."""
import requests
from typing import Optional, Dict, List
import re
import config


def extract_tweet_id(url: str) -> Optional[str]:
    """Extract tweet ID from URL."""
    patterns = [
        r'twitter\.com/\w+/status/(\d+)',
        r'x\.com/\w+/status/(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def extract_thread(url: str) -> Optional[Dict]:
    """
    Extract full thread from X/Twitter URL.
    Returns dict with title, content (full thread), and metadata.
    """
    tweet_id = extract_tweet_id(url)
    if not tweet_id:
        return None
    
    # Try using X API v2 if token is available
    if config.X_BEARER_TOKEN:
        return extract_thread_via_api(tweet_id)
    else:
        # Fallback: extract just the single tweet info via scraping
        return extract_single_tweet(tweet_id, url)


def extract_thread_via_api(tweet_id: str) -> Optional[Dict]:
    """Extract thread using X API v2."""
    try:
        import tweepy
        
        client = tweepy.Client(config.X_BEARER_TOKEN)
        
        # Get the initial tweet to find conversation_id
        tweet = client.get_tweet(
            tweet_id,
            tweet_fields=['conversation_id', 'created_at', 'author_id', 'text']
        )
        
        if not tweet.data:
            return None
        
        conversation_id = tweet.data.conversation_id
        author_id = tweet.data.author_id
        
        # Search for all tweets in the conversation by the same author
        tweets = []
        
        # Get the root tweet
        tweets.append({
            'id': tweet.data.id,
            'text': tweet.data.text,
            'created_at': tweet.data.created_at,
            'author_id': author_id
        })
        
        # Search for replies in the conversation
        query = f"conversation_id:{conversation_id} from:{author_id}"
        
        try:
            response = client.search_recent_tweets(
                query=query,
                tweet_fields=['created_at', 'author_id', 'referenced_tweets'],
                max_results=100
            )
            
            if response.data:
                for t in response.data:
                    if t.id != tweet_id:  # Avoid duplicate
                        tweets.append({
                            'id': t.id,
                            'text': t.text,
                            'created_at': t.created_at,
                            'author_id': t.author_id
                        })
        except Exception as e:
            print(f"Warning: Could not fetch thread replies: {e}")
        
        # Sort by creation time
        tweets.sort(key=lambda x: x['created_at'])
        
        # Combine all tweets
        thread_text = '\n\n'.join([f"[{i+1}] {t['text']}" for i, t in enumerate(tweets)])
        
        # Get author info
        author = None
        try:
            users = client.get_users(ids=[author_id])
            if users.data:
                author = users.data[0].username
        except:
            pass
        
        return {
            'title': f"Thread by @{author or 'unknown'}",
            'content': thread_text,
            'author': author,
            'published_at': tweets[0]['created_at'] if tweets else None,
            'metadata': {
                'tweet_id': tweet_id,
                'conversation_id': conversation_id,
                'tweet_count': len(tweets),
                'tweet_ids': [t['id'] for t in tweets]
            }
        }
        
    except Exception as e:
        print(f"Error extracting thread via API: {e}")
        return None


def extract_single_tweet(tweet_id: str, url: str) -> Optional[Dict]:
    """
    Fallback: extract single tweet info.
    This is a basic implementation - for full thread extraction,
    X API access is required.
    """
    # Try to fetch the tweet page for basic info
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        # Extract basic info from meta tags
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = None
        if soup.find('meta', property='og:title'):
            title = soup.find('meta', property='og:title')['content']
        
        description = None
        if soup.find('meta', property='og:description'):
            description = soup.find('meta', property='og:description')['content']
        
        content = description or f"Tweet ID: {tweet_id}"
        
        return {
            'title': title or 'X Post',
            'content': content,
            'author': None,
            'published_at': None,
            'metadata': {
                'tweet_id': tweet_id,
                'note': 'Full thread extraction requires X API access'
            }
        }
        
    except Exception as e:
        print(f"Error extracting tweet: {e}")
        return {
            'title': 'X Post',
            'content': f"Tweet URL: {url}",
            'author': None,
            'published_at': None,
            'metadata': {'tweet_id': tweet_id}
        }
