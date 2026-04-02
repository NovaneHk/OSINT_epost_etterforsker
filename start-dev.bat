@echo off
REM start-dev.bat — One-command local development startup (Windows)
REM Usage: start-dev.bat

REM Copy .env.example -> .env if .env does not exist
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo [start-dev] .env created from .env.example — review and set any required API keys.
    ) else (
        echo [start-dev] WARNING: .env.example not found, starting without .env file.
    )
)

REM Ensure nginx log directory exists
if not exist nginx\logs mkdir nginx\logs

echo [start-dev] Starting stack (HTTP-only dev mode, DEBUG=true)...
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build %*
