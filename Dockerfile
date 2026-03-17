# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_trf

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies (sqlite-vec needs libsqlite3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Environment variables (override with -e or .env file)
ENV DISCORD_BOT_TOKEN=""
ENV X_BEARER_TOKEN=""
ENV DATABASE_PATH="/app/data/knowledge.db"
ENV EMBEDDING_MODEL="BAAI/bge-large-en-v1.5"
ENV EMBEDDING_DIMENSION="1024"
ENV KB_CHANNEL_ID="1481211293242490900"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/app/data/knowledge.db').close()" || exit 1

# Run bot
CMD ["python", "bot.py"]
