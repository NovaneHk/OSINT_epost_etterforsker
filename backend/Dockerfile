# Backend Dockerfile for OSINT E-post Etterforsker
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    curl \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY backend/requirements.txt ./backend-requirements.txt
COPY requirements_core.txt ./requirements_core.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements_core.txt && \
    pip install --no-cache-dir -r backend-requirements.txt

# Copy application code
COPY backend ./backend
COPY core ./core
COPY configs ./configs
COPY scraping ./scraping
COPY extract ./extract
COPY validate ./validate
COPY scoring ./scoring
COPY export ./export
COPY enrich ./enrich
COPY report ./report
COPY monitoring ./monitoring
COPY integrations ./integrations
COPY automation ./automation
COPY ai ./ai
COPY logging.conf ./logging.conf

# Create necessary directories
RUN mkdir -p /app/logs /app/exports /app/cache /app/backups /app/data && \
    chown -R appuser:appuser /app

# Copy alembic configuration
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
