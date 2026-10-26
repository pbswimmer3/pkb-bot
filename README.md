# Personal Knowledge Base with RAG

> **Status: disabled (2026-10-25).** This bot ran as a Docker container on a self-hosted Hyper-V VM. The VM was shut down on 2026-05-11 and retired on 2026-10-25 during a security cleanup: the Discord bot was removed from every server, and the OpenClaw gateway it used for answers is retired. The code stays here for reference; running it again needs a new Discord bot token and a new model backend. The knowledge base (`data/knowledge.db`) is preserved in an offline backup.

A Discord-native personal knowledge base with semantic search, supporting articles, YouTube videos, X/Twitter threads, and PDFs.

## Features

- **Multi-source ingestion**: URLs, YouTube videos, X/Twitter threads, PDFs
- **Paywall bypass**: Automatically uses Wayback Machine for archive copies
- **Auto-summarization**: Posts 3-5 bullet executive summary after ingestion
- **Smart entity extraction**: People, companies, concepts using transformer-based NER
- **SQLite + Vector storage**: Local-first with sqlite-vec for embeddings
- **Hybrid search**: Semantic + BM25 keyword search
- **Time-aware ranking**: Recent sources rank higher
- **Source-weighted ranking**: Prioritize certain content types
- **Discord-native**: Drop URLs in channel for auto-ingestion

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Discord Bot    │────▶│  Ingestion       │────▶│  SQLite + Vec   │
│  (URL Listener) │     │  Pipeline        │     │  (Embeddings)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Entity Extraction│
                        │  (spaCy trf)     │
                        └──────────────────┘

┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Query (NL)     │────▶│  Search Engine   │────▶│  Ranked Results │
│                 │     │  (Hybrid + Time) │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Setup

### Option 1: Docker (Recommended)

```bash
# Setup environment
cp .env.example .env
# Edit .env with your DISCORD_BOT_TOKEN

# Build and run
make up-build

# View logs
make logs
```

### Option 2: Manual

```bash
# Install dependencies
pip install -r requirements.txt

# Download spaCy transformer model
python -m spacy download en_core_web_trf

# Set environment variables
export DISCORD_BOT_TOKEN="your_token"
export X_BEARER_TOKEN="your_x_api_token"  # Optional, for X threads

# Initialize database
python -c "from kb.database import init_db; init_db()"

# Run bot
python bot.py
```

## Usage

### Ingest Content
- Drop any URL in the configured Discord channel
- For PDFs: Upload directly to the channel

### Query
```
!ask What are the latest developments in AI RAG?
!search hybrid search sqlite
!recent 5
```

## Project Structure

```
pkb/
├── bot.py              # Discord bot entry point
├── config.py           # Configuration
├── requirements.txt    # Dependencies
├── kb/
│   ├── __init__.py
│   ├── database.py     # SQLite + vector operations
│   ├── embeddings.py   # Embedding generation
│   ├── entities.py     # NER entity extraction
│   ├── search.py       # Hybrid search engine
│   └── ingest/
│       ├── __init__.py
│       ├── web.py      # Article extraction
│       ├── youtube.py  # YouTube transcripts
│       ├── twitter.py  # X/Twitter threads
│       └── pdf.py      # PDF processing
└── data/
    └── knowledge.db    # SQLite database
```

## Data Model

### Documents Table
- `id`: Primary key
- `url`: Source URL
- `source_type`: article|youtube|twitter|pdf
- `title`: Document title
- `content`: Full text content
- `author`: Content author (if available)
- `published_at`: Publication date
- `ingested_at`: Ingestion timestamp
- `metadata`: JSON blob

### Chunks Table
- `id`: Primary key
- `document_id`: Foreign key
- `content`: Chunk text
- `embedding`: Vector (sqlite-vec)
- `chunk_index`: Position in document
- `entities`: Extracted entities JSON

### Entities Table
- `id`: Primary key
- `name`: Entity name
- `type`: PERSON|ORG|GPE|PRODUCT|CONCEPT
- `document_ids`: JSON array of doc IDs
- `mention_count`: Total mentions

## License

MIT
