"""Production Deployment Stack - Docker, Kubernetes, monitoring configuration."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

DOCKER_COMPOSE_YAML = """
version: '3.8'

services:
  hermes-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://hermes:hermes@postgres:5432/hermes
      - LLM_PROVIDER=ollama
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - postgres
      - redis
      - ollama
    restart: unless-stopped

  hermes-worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["python", "-m", "hermes_worker"]
    environment:
      - DATABASE_URL=postgresql://hermes:hermes@postgres:5432/hermes
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  hermes-dashboard:
    build:
      context: .
      dockerfile: Dockerfile
    command: ["python", "-m", "core.dashboard", "--host", "0.0.0.0", "--port", "8080"]
    ports:
      - "8080:8080"
    depends_on:
      - hermes-api
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: hermes
      POSTGRES_PASSWORD: hermes
      POSTGRES_DB: hermes
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: hermes
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  postgres_data:
  ollama_data:
  grafana_data:
"""

DOCKERFILE = """
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8080

CMD ["python", "-m", "core.api"]
"""

K8S_DEPLOYMENT = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hermes-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: hermes-api
  template:
    metadata:
      labels:
        app: hermes-api
    spec:
      containers:
      - name: hermes-api
        image: hermes-agi:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: hermes-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: hermes-api
spec:
  selector:
    app: hermes-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
"""

PROMETHEUS_YAML = """
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'hermes-api'
    static_configs:
      - targets: ['hermes-api:8000']
"""


class DeploymentGenerator:
    """Generate deployment configurations."""
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
    
    def generate_docker_compose(self):
        """Generate docker-compose.yml."""
        path = self.output_dir / "docker-compose.yml"
        path.write_text(DOCKER_COMPOSE_YAML.strip())
        return path
    
    def generate_dockerfile(self):
        """Generate Dockerfile."""
        path = self.output_dir / "Dockerfile"
        path.write_text(DOCKERFILE.strip())
        return path
    
    def generate_k8s(self):
        """Generate Kubernetes manifests."""
        k8s_dir = self.output_dir / "k8s"
        k8s_dir.mkdir(exist_ok=True)
        
        deployment_path = k8s_dir / "deployment.yaml"
        deployment_path.write_text(K8S_DEPLOYMENT.strip())
        
        return k8s_dir
    
    def generate_monitoring(self):
        """Generate monitoring configuration."""
        monitoring_dir = self.output_dir / "monitoring"
        monitoring_dir.mkdir(exist_ok=True)
        
        prometheus_path = monitoring_dir / "prometheus.yml"
        prometheus_path.write_text(PROMETHEUS_YAML.strip())
        
        return monitoring_dir
    
    def generate_all(self):
        """Generate all deployment files."""
        self.generate_docker_compose()
        self.generate_dockerfile()
        self.generate_k8s()
        self.generate_monitoring()
