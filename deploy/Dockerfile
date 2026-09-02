# Hermes AGI/ASI Harness — Production Docker Image
FROM python:3.11-slim

# Security: non-root user
RUN groupadd -r hermes && useradd -r -g hermes -d /app -s /sbin/nologin hermes

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    redis-tools \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY src/ ./src/
COPY config/ ./config/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Resource limits (enforced by Docker/K8s)
# CPU: 2 cores
# Memory: 4GB
# Storage: 10GB

USER hermes

EXPOSE 8000

CMD ["python", "-m", "src.hermes", "--host", "0.0.0.0", "--port", "8000"]
