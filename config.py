"""Configuration for Personal Knowledge Base."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
KB_CHANNEL_ID = int(os.getenv("KB_CHANNEL_ID", "1481211293242490900"))

# X API
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "knowledge.db"))

# Embeddings
# BGE-large-en-v1.5: 1024-dim, MTEB top-5 performance, free/open-source
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "128"))

# Search
DEFAULT_SEARCH_LIMIT = int(os.getenv("DEFAULT_SEARCH_LIMIT", "10"))
TIME_DECAY_DAYS = int(os.getenv("TIME_DECAY_DAYS", "30"))

# Source type weights for ranking (higher = more important)
SOURCE_WEIGHTS = {
    "article": 1.0,
    "youtube": 0.9,
    "twitter": 0.8,
    "pdf": 1.0,
}

# Entity types we care about
ENTITY_TYPES = {"PERSON", "ORG", "GPE", "PRODUCT", "WORK_OF_ART", "LAW", "EVENT"}
