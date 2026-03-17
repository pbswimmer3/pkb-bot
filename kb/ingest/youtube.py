"""YouTube transcript extraction."""
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from typing import Optional, Dict
import re


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def extract_transcript(url: str) -> Optional[Dict]:
    """
    Extract transcript from YouTube video.
    Returns dict with title, content, and metadata.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None
    
    try:
        # Get transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Format as plain text
        formatter = TextFormatter()
        text = formatter.format_transcript(transcript_list)
        
        # Get video info (we'll use the URL as title placeholder)
        # In production, you might want to use yt-dlp or YouTube Data API for title
        title = f"YouTube Video ({video_id})"
        
        return {
            'title': title,
            'content': text,
            'author': None,
            'published_at': None,
            'metadata': {
                'video_id': video_id,
                'transcript_entries': len(transcript_list)
            }
        }
        
    except Exception as e:
        print(f"Error extracting YouTube transcript: {e}")
        return None


def extract_transcript_with_timestamps(url: str) -> Optional[Dict]:
    """Extract transcript with timestamps for better context."""
    video_id = extract_video_id(url)
    if not video_id:
        return None
    
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Format with timestamps
        formatted_lines = []
        for entry in transcript_list:
            start = int(entry['start'])
            minutes = start // 60
            seconds = start % 60
            timestamp = f"[{minutes:02d}:{seconds:02d}]"
            formatted_lines.append(f"{timestamp} {entry['text']}")
        
        text = '\n'.join(formatted_lines)
        
        return {
            'title': f"YouTube Video ({video_id})",
            'content': text,
            'author': None,
            'published_at': None,
            'metadata': {
                'video_id': video_id,
                'has_timestamps': True
            }
        }
        
    except Exception as e:
        print(f"Error extracting YouTube transcript: {e}")
        return None
