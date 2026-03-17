"""PDF text extraction."""
import fitz  # PyMuPDF
from typing import Optional, Dict
import io


def extract_pdf(content: bytes, filename: str = "document.pdf") -> Optional[Dict]:
    """
    Extract text from PDF bytes.
    Returns dict with title, content, and metadata.
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        
        # Extract metadata
        metadata = doc.metadata
        title = metadata.get('title') or filename
        author = metadata.get('author')
        
        # Extract text from all pages
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
        
        doc.close()
        
        full_text = '\n\n'.join(text_parts)
        
        if not full_text.strip():
            return None
        
        return {
            'title': title,
            'content': full_text,
            'author': author,
            'published_at': None,
            'metadata': {
                'filename': filename,
                'page_count': len(doc),
                'pdf_metadata': metadata
            }
        }
        
    except Exception as e:
        print(f"Error extracting PDF {filename}: {e}")
        return None


def extract_pdf_from_file(filepath: str) -> Optional[Dict]:
    """Extract text from PDF file."""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        filename = filepath.split('/')[-1]
        return extract_pdf(content, filename)
    except Exception as e:
        print(f"Error reading PDF file {filepath}: {e}")
        return None
