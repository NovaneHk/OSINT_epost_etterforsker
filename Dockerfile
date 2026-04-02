FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install Playwright dependencies (if needed, but maybe skip for now to save time/space if not strictly used in API)
# RUN playwright install-deps

# Copy requirements
COPY requirements.txt .
COPY requirements_core.txt .
# Create backend directory for requirements if it doesn't exist in context yet (it will be copied later, but we need the file now)
COPY backend/requirements.txt ./backend/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements_core.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install uvicorn fastapi psycopg2-binary redis

# Copy source code
COPY . .

# Set python path
ENV PYTHONPATH=/app

# Create runtime directories and grant ownership
RUN mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run the canonical backend entry point
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
