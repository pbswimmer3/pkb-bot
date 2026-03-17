# PKB LLM Integration + Channel Routing Update

## Changes Made

### 1. LLM RAG Layer Added (`kb/llm_rag.py`)
New module that calls OpenClaw gateway for LLM-powered answers:
- `rag_query()` — synthesizes answers from retrieved chunks with citations
- `rewrite_query_for_search()` — optimizes vague queries for better retrieval
- `call_openclaw_llm()` — HTTP client to OpenClaw gateway API

### 2. Bot Updated (`bot.py`)
- `!ask` command now uses LLM RAG instead of raw chunk display
- Shows "Searching..." → "Synthesizing..." status messages
- Returns formatted answer with source citations
- `!search` command still available for raw results

### 3. Configuration Updates

#### `.env.example`
Added:
```
OPENCLAW_GATEWAY_URL=http://openclaw-gateway:18789
# OPENCLAW_API_KEY=your_api_key_here
RAG_MODEL=moonshot/kimi-k2.5
```

#### `docker-compose.yml`
Added external network to reach OpenClaw:
```yaml
networks:
  - openclaw-network

networks:
  openclaw-network:
    external: true
    name: openclaw_default
```

### 4. OpenClaw Config Update Needed

Add this to your OpenClaw config (`openclaw.json`) to disable processing in the PKB channel:

```json5
{
  channels: {
    discord: {
      guilds: {
        "1481206430907240492": {  // Your server ID
          channels: {
            "1481211293242490900": {  // #personal-knowledge-base
              allow: false  // OpenClaw ignores this channel
            }
          }
        }
      }
    }
  }
}
```

Or use the CLI:
```bash
openclaw config set channels.discord.guilds."1481206430907240492".channels."1481211293242490900".allow false --json
```

## Deployment Steps

1. **Update OpenClaw config** (above) to ignore the PKB channel
2. **Rebuild and restart PKB bot**:
   ```bash
   cd /home/node/.openclaw/workspace/pkb
   docker compose down
   docker compose up -d --build
   ```
3. **Test**: Drop a URL, then try `!ask what is this about?`

## Architecture

```
User: !ask what did I save about AI agents?
  ↓
PKB Bot (Discord)
  ├─→ hybrid_search() retrieves top chunks
  ├─→ rag_query() calls OpenClaw gateway /v1/chat/completions
  │     Model: moonshot/kimi-k2.5 (or configured RAG_MODEL)
  │     Prompt: RAG template with chunks as context
  │     ← Returns synthesized answer
  ↓
Discord: Formatted answer with citations [1], [2], etc.
```

## Notes

- Uses existing OpenClaw model routing (Kimi K2.5 default, can escalate to Opus)
- No additional API keys needed — uses your existing gateway
- If gateway is unavailable, bot falls back gracefully
