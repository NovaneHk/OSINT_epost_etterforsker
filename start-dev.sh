#!/bin/bash
# start-dev.sh — One-command local development startup
# Usage: ./start-dev.sh
set -e

# Copy .env.example -> .env if .env does not exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[start-dev] .env created from .env.example — review and set any required API keys."
    else
        echo "[start-dev] WARNING: .env.example not found, starting without .env file."
    fi
fi

# Ensure nginx log directory exists (nginx writes here before Docker creates it)
mkdir -p nginx/logs

echo "[start-dev] Starting stack (HTTP-only dev mode, DEBUG=true)..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build "$@"
