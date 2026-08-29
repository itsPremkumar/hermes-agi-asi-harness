# CodeReview Bot Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source
COPY src/ src/
COPY tests/ tests/

# Run as non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["codereview-bot"]
