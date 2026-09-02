"""Dockerfile for MCPHub backend."""
FROM python:3.11-slim as base

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application
COPY backend/src/mcphub ./mcphub
COPY cli/mcphub_cli ./mcphub_cli

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"

# Run
CMD ["uvicorn", "mcphub.main:app", "--host", "0.0.0.0", "--port", "8000"]
