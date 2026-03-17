#!/bin/bash
# Quick rebuild script for PKB bot

cd /home/node/.openclaw/workspace/pkb

echo "Stopping PKB bot..."
docker compose down

echo "Rebuilding..."
docker compose up -d --build

echo "Waiting for startup..."
sleep 3

echo "Recent logs:"
docker logs pkb-bot --tail 30
