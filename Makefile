# Build and run the Personal Knowledge Base bot with Docker

.PHONY: build run stop logs shell clean setup

# Detect docker compose command (newer versions use 'docker compose', older use 'docker-compose')
DOCKER_COMPOSE := $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; else echo "docker-compose"; fi)

# Default target
all: build

# Build the Docker image
build:
	docker build -t pkb-bot:latest .

# Run with docker compose (recommended)
up:
	$(DOCKER_COMPOSE) up -d

# Run with docker compose and build
up-build:
	$(DOCKER_COMPOSE) up -d --build

# Stop the bot
stop:
	$(DOCKER_COMPOSE) down

# View logs
logs:
	$(DOCKER_COMPOSE) logs -f

# Open shell in container
shell:
	$(DOCKER_COMPOSE) exec knowledge-base bash

# Query the knowledge base from container
query:
	$(DOCKER_COMPOSE) exec knowledge-base python query.py "$(ARGS)"

# Show stats
stats:
	$(DOCKER_COMPOSE) exec knowledge-base python query.py --stats

# Recent documents
recent:
	$(DOCKER_COMPOSE) exec knowledge-base python query.py --recent 10

# Clean up
clean:
	$(DOCKER_COMPOSE) down -v
	docker rmi pkb-bot:latest 2>/dev/null || true

# First-time setup
setup:
	@echo "Creating .env file..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env — edit it to add your DISCORD_BOT_TOKEN"; \
	else \
		echo "✅ .env already exists"; \
	fi
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env and add your DISCORD_BOT_TOKEN"
	@echo "  2. Run: make up-build"
	@echo "  3. Check logs: make logs"

# Help
help:
	@echo "Personal Knowledge Base — Docker Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup:"
	@echo "  make setup       — Create .env from template"
	@echo ""
	@echo "Build & Run:"
	@echo "  make build       — Build Docker image"
	@echo "  make up          — Start bot with docker compose"
	@echo "  make up-build    — Build and start"
	@echo "  make stop        — Stop bot"
	@echo ""
	@echo "Query (container must be running):"
	@echo "  make query ARGS=\"your question\""
	@echo "  make stats       — Show KB stats"
	@echo "  make recent      — Show recent docs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make logs        — View logs"
	@echo "  make shell       — Open container shell"
	@echo "  make clean       — Remove containers and images"
