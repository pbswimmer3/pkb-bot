# Personal Knowledge Base — Docker Setup

## Quick Start

```bash
# 1. Setup environment
make setup

# 2. Edit .env with your Discord bot token
vim .env

# 3. Build and run
make up-build

# 4. Check logs
make logs
```

## Manual Docker Commands

```bash
# Build image
docker build -t pkb-bot .

# Run container
docker run -d \
  --name pkb-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -e DISCORD_BOT_TOKEN="your_token" \
  -e KB_CHANNEL_ID="1481211293242490900" \
  pkb-bot

# Or use docker-compose (recommended)
docker-compose up -d
```

## Data Persistence

The SQLite database is stored in `./data/knowledge.db` on your host machine, mounted into the container. This means:

- Your data survives container restarts
- You can back up the `data/` directory
- You can query the DB directly from host with SQLite tools

## Querying from Container

```bash
# Search
make query ARGS="What are the latest AI developments?"

# Stats
make stats

# Recent docs
make recent
```

Or directly:
```bash
docker-compose exec knowledge-base python query.py "your question"
```

## Updating

```bash
# Pull latest code, rebuild, restart
git pull
make up-build
```

## Troubleshooting

**Container won't start:**
```bash
make logs
# Check if DISCORD_BOT_TOKEN is set in .env
```

**Database issues:**
```bash
# Reset database (WARNING: deletes all data)
rm data/knowledge.db
docker-compose restart
```

**Embedding model download slow:**
The BGE-large model (1.3GB) downloads on first run. This is cached in the container. If you rebuild, it re-downloads. To persist:
```bash
# Add to docker-compose.yml volumes:
- model-cache:/root/.cache/huggingface
```

## Multi-arch Build (for ARM/M1 Macs)

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t pkb-bot .
```
