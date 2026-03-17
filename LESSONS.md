# LESSONS.md — PKB Enhancement Session

## Format: `[DATE] - [Category] - [Lesson]`

## Active Lessons

### 2026-03-17 - Architecture - Archive-first ingestion pattern
**Lesson:** Wayback Machine API is simple and effective for paywall bypass. The availability endpoint returns the closest snapshot.
**Implementation:** `https://archive.org/wayback/available?url={encoded_url}`

### 2026-03-17 - Implementation - Docker API vs CLI
**Lesson:** The agent container doesn't have `docker` CLI, but can use the Docker HTTP API via `/var/run/docker.sock` with curl.
**Pattern:** `curl -s --unix-socket /var/run/docker.sock http://localhost/containers/{name}/json`

### 2026-03-17 - Integration - Summary generation timing
**Lesson:** Generate summary AFTER successful ingestion, not before. This ensures we have clean content and don't waste LLM calls on failed ingests.

## Categories
- `Architecture` — Design decisions
- `Implementation` — Coding bugs/solutions
- `API` — External service issues (archive.org, etc.)
- `Integration` — Wiring components together

## Archive
*None yet*
