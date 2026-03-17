"""Database operations for knowledge base."""
import sqlite3
import json
import sqlite_vec
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from config import DATABASE_PATH, EMBEDDING_DIMENSION


def get_db() -> sqlite3.Connection:
    """Get database connection with vec extension loaded."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_db()
    
    # Documents table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            source_type TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            author TEXT,
            published_at TIMESTAMP,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            word_count INTEGER DEFAULT 0
        )
    """)
    
    # Chunks table with virtual vec table for embeddings
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            entities TEXT,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)
    
    # Virtual table for vector search using sqlite-vec
    conn.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0(
            chunk_id INTEGER,
            embedding float[{EMBEDDING_DIMENSION}]
        )
    """)
    
    # Entities table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            document_ids TEXT NOT NULL,
            mention_count INTEGER DEFAULT 1,
            UNIQUE(name, type)
        )
    """)
    
    # FTS5 table for keyword search
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(
            title,
            content,
            content='documents',
            content_rowid='id'
        )
    """)
    
    # Triggers to keep FTS index in sync
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
            INSERT INTO document_fts(rowid, title, content)
            VALUES (new.id, new.title, new.content);
        END
    """)
    
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
            INSERT INTO document_fts(document_fts, rowid, title, content)
            VALUES ('delete', old.id, old.title, old.content);
        END
    """)
    
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
            INSERT INTO document_fts(document_fts, rowid, title, content)
            VALUES ('delete', old.id, old.title, old.content);
            INSERT INTO document_fts(rowid, title, content)
            VALUES (new.id, new.title, new.content);
        END
    """)
    
    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_ingested ON documents(ingested_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
    
    conn.commit()
    conn.close()


def insert_document(
    url: str,
    source_type: str,
    title: Optional[str],
    content: str,
    author: Optional[str] = None,
    published_at: Optional[datetime] = None,
    metadata: Optional[Dict] = None
) -> int:
    """Insert a document and return its ID."""
    conn = get_db()
    cursor = conn.execute(
        """
        INSERT INTO documents (url, source_type, title, content, author, published_at, metadata, word_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            title = excluded.title,
            content = excluded.content,
            author = excluded.author,
            published_at = excluded.published_at,
            metadata = excluded.metadata,
            word_count = excluded.word_count,
            ingested_at = CURRENT_TIMESTAMP
        RETURNING id
        """,
        (url, source_type, title, content, author, published_at, 
         json.dumps(metadata) if metadata else None, len(content.split()))
    )
    doc_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return doc_id


def insert_chunk(document_id: int, content: str, chunk_index: int, 
                 embedding: List[float], entities: Optional[List[Dict]] = None) -> int:
    """Insert a chunk with its embedding."""
    conn = get_db()
    
    # Insert chunk
    cursor = conn.execute(
        """
        INSERT INTO chunks (document_id, content, chunk_index, entities)
        VALUES (?, ?, ?, ?)
        RETURNING id
        """,
        (document_id, content, chunk_index, json.dumps(entities) if entities else None)
    )
    chunk_id = cursor.fetchone()[0]
    
    # Insert embedding into vec table
    embedding_json = json.dumps(embedding)
    conn.execute(
        "INSERT INTO chunk_embeddings (chunk_id, embedding) VALUES (?, ?)",
        (chunk_id, embedding_json)
    )
    
    conn.commit()
    conn.close()
    return chunk_id


def update_entities(entities: List[Dict], document_id: int):
    """Update entity mentions across documents."""
    conn = get_db()
    
    for entity in entities:
        name = entity["text"]
        entity_type = entity["label"]
        
        # Check if entity exists
        cursor = conn.execute(
            "SELECT document_ids, mention_count FROM entities WHERE name = ? AND type = ?",
            (name, entity_type)
        )
        row = cursor.fetchone()
        
        if row:
            doc_ids = json.loads(row["document_ids"])
            if document_id not in doc_ids:
                doc_ids.append(document_id)
            conn.execute(
                "UPDATE entities SET document_ids = ?, mention_count = ? WHERE name = ? AND type = ?",
                (json.dumps(doc_ids), row["mention_count"] + 1, name, entity_type)
            )
        else:
            conn.execute(
                "INSERT INTO entities (name, type, document_ids, mention_count) VALUES (?, ?, ?, 1)",
                (name, entity_type, json.dumps([document_id]))
            )
    
    conn.commit()
    conn.close()


def get_document_by_url(url: str) -> Optional[Dict]:
    """Get document by URL."""
    conn = get_db()
    cursor = conn.execute("SELECT * FROM documents WHERE url = ?", (url,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_document_by_id(doc_id: int) -> Optional[Dict]:
    """Get document by ID."""
    conn = get_db()
    cursor = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def search_similar_chunks(embedding: List[float], limit: int = 10) -> List[Dict]:
    """Search for similar chunks using vector similarity."""
    conn = get_db()
    embedding_json = json.dumps(embedding)
    
    cursor = conn.execute(
        f"""
        SELECT 
            c.id,
            c.content,
            c.chunk_index,
            c.document_id,
            d.url,
            d.title,
            d.source_type,
            d.ingested_at,
            d.published_at,
            distance
        FROM chunk_embeddings
        JOIN chunks c ON chunk_embeddings.chunk_id = c.id
        JOIN documents d ON c.document_id = d.id
        WHERE embedding MATCH ? AND k = {limit}
        ORDER BY distance
        """,
        (embedding_json,)
    )
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def search_keyword(query: str, limit: int = 10) -> List[Dict]:
    """Search using FTS5 keyword search."""
    conn = get_db()
    
    cursor = conn.execute(
        """
        SELECT 
            d.id,
            d.url,
            d.title,
            d.content,
            d.source_type,
            d.ingested_at,
            d.published_at,
            rank
        FROM document_fts
        JOIN documents d ON document_fts.rowid = d.id
        WHERE document_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, limit)
    )
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_recent_documents(limit: int = 10) -> List[Dict]:
    """Get recently ingested documents."""
    conn = get_db()
    cursor = conn.execute(
        """
        SELECT * FROM documents
        ORDER BY ingested_at DESC
        LIMIT ?
        """,
        (limit,)
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_documents_by_entity(entity_name: str) -> List[Dict]:
    """Get documents mentioning a specific entity."""
    conn = get_db()
    cursor = conn.execute(
        """
        SELECT d.* FROM documents d
        JOIN chunks c ON c.document_id = d.id
        WHERE c.entities LIKE ?
        GROUP BY d.id
        """,
        (f'%"text": "{entity_name}"%',)
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def delete_document(doc_id: int):
    """Delete a document and all its chunks."""
    conn = get_db()
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()


def get_stats() -> Dict:
    """Get database statistics."""
    conn = get_db()
    
    stats = {}
    
    cursor = conn.execute("SELECT COUNT(*) as count FROM documents")
    stats["total_documents"] = cursor.fetchone()["count"]
    
    cursor = conn.execute("SELECT COUNT(*) as count FROM chunks")
    stats["total_chunks"] = cursor.fetchone()["count"]
    
    cursor = conn.execute("SELECT COUNT(*) as count FROM entities")
    stats["total_entities"] = cursor.fetchone()["count"]
    
    cursor = conn.execute(
        "SELECT source_type, COUNT(*) as count FROM documents GROUP BY source_type"
    )
    stats["by_source"] = {row["source_type"]: row["count"] for row in cursor.fetchall()}
    
    conn.close()
    return stats
