# Multi-stage Dockerfile for OSINT B2B Email System Production Deployment
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

# Install Python dependencies
COPY requirements_core.txt requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements_core.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/exports /app/cache /app/backups && \
    chown -R appuser:appuser /app

# Production stage
FROM base as production

# Copy production configuration
COPY deploy/production.yml /app/config/production.yml

# Health check script
COPY deploy/health_check.py /app/health_check.py

# Startup script
COPY deploy/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python health_check.py || exit 1

# Start application
CMD ["/app/start.sh"]

# Development stage
FROM base as development

# Install development dependencies
COPY requirements_dev.txt ./
RUN pip install --no-cache-dir -r requirements_dev.txt

# Switch to non-root user
USER appuser

# Expose port for development
EXPOSE 8000

# Start in development mode
CMD ["python", "main.py", "--dev"]