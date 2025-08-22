#!/bin/bash
# Production startup script for OSINT B2B Email System

set -e

echo "Starting OSINT B2B Email System..."

# Environment validation
if [ -z "$SECRET_KEY" ]; then
    echo "ERROR: SECRET_KEY environment variable is required"
    exit 1
fi

if [ -z "$DB_HOST" ]; then
    echo "ERROR: DB_HOST environment variable is required"
    exit 1
fi

# Set default values for optional environment variables
export PYTHONPATH=${PYTHONPATH:-/app}
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export WORKERS=${WORKERS:-4}
export PORT=${PORT:-8000}

# Create necessary directories
mkdir -p /app/logs /app/exports /app/cache /app/backups

# Wait for database to be ready
echo "Waiting for database connection..."
python -c "
import time
import sys
import os
sys.path.insert(0, '/app')
from core.database import DatabaseManager

max_attempts = 30
for attempt in range(max_attempts):
    try:
        db = DatabaseManager()
        db.get_contact_stats()
        print('Database connection successful')
        break
    except Exception as e:
        if attempt == max_attempts - 1:
            print(f'Database connection failed after {max_attempts} attempts: {e}')
            sys.exit(1)
        print(f'Database connection attempt {attempt + 1} failed, retrying in 2 seconds...')
        time.sleep(2)
"

# Initialize database schema if needed
echo "Initializing database schema..."
python -c "
import sys
sys.path.insert(0, '/app')
from core.database import DatabaseManager
db = DatabaseManager()
db.init_db()
print('Database schema initialized')
"

# Validate configuration
echo "Validating configuration..."
python -c "
import sys
sys.path.insert(0, '/app')
from core.config import ConfigManager
config_manager = ConfigManager()
config = config_manager.get_current_config()
if not config:
    print('ERROR: Configuration validation failed')
    sys.exit(1)
print('Configuration validation successful')
"

# Start the application
echo "Starting application on port $PORT with $WORKERS workers..."

# Check if we're in development mode
if [ "$1" = "--dev" ]; then
    echo "Starting in development mode..."
    export FLASK_ENV=development
    export DEBUG=true
    python main.py --dev
else
    echo "Starting in production mode..."
    # Use gunicorn for production
    if command -v gunicorn >/dev/null 2>&1; then
        exec gunicorn \
            --bind 0.0.0.0:$PORT \
            --workers $WORKERS \
            --worker-class aiohttp.GunicornWebWorker \
            --timeout 300 \
            --keepalive 2 \
            --max-requests 1000 \
            --max-requests-jitter 100 \
            --preload \
            --access-logfile /app/logs/access.log \
            --error-logfile /app/logs/error.log \
            --log-level $LOG_LEVEL \
            main:app
    else
        # Fallback to direct python execution
        echo "Gunicorn not found, starting with Python directly..."
        python main.py --production
    fi
fi