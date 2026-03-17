# TODO.md — PKB Paywall Bypass & Auto-Summarization

## Objective
Enhance PKB Discord bot with:
1. **Paywall bypass** — Use archive.org (Wayback Machine) to get full article text
2. **Auto-summarization** — Post 3-5 bullet summary immediately after ingestion

## Active Tasks

### Phase 1: Discovery & Planning
- [x] Review current ingestion flow in `kb/ingest/web.py`
- [x] Identify where URL is processed before scraping
- [x] Plan archive.org integration approach
- [x] Plan summary generation trigger point

### Phase 2: Archive-First Ingestion
- [x] Create `kb/ingest/archive.py` — Wayback Machine API wrapper
- [x] Function: `get_archive_url(url)` → returns archive URL or None
- [x] Modify `kb/ingest/web.py` to try archive first, fallback to direct
- [x] Log when fallback is used

### Phase 3: Auto-Summarization
- [x] Create `kb/summarize.py` — article summarization module
- [x] Use OpenClaw LLM for summarization (Kimi or Sonnet)
- [x] Function: `summarize_article(content)` → 3-5 bullet points
- [x] Modify `bot.py` to post summary after successful ingestion

### Phase 4: Integration & Testing
- [x] Wire archive logic into ingestion pipeline
- [x] Wire summary generation into Discord message flow
- [ ] Test with paywalled URL (e.g., NYT, WaPo)
- [ ] Test summary appears in Discord channel

### Phase 5: Documentation & Deploy
- [x] Update README with new features
- [x] Rebuild Docker image
- [ ] Push to GitHub

## Completed ✅
All core features implemented. Container restarted and running.

## Completed
*None yet*

## Blocked
*None*

## Notes
- Archive.org has rate limits — implement basic retry/backoff
- Summary should be concise (Executive Summary style)
- Must not break existing ingestion for non-paywalled sites
