# Deployment

## Environments

| Environment | URL | Branch |
|-------------|-----|--------|
| Staging | https://staging.hermes-harness.ai | `develop` |
| Production | https://hermes-harness.ai | `main` (tags) |

## Docker Deployment

```bash
# Build
docker build -t hermes-agi-asi-harness:latest .

# Run
docker run -d \
  --name hermes-harness \
  -p 8080:8080 \
  -e HERMES_ENV=production \
  hermes-agi-asi-harness:latest
```

## Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hermes-harness
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hermes-harness
  template:
    metadata:
      labels:
        app: hermes-harness
    spec:
      containers:
      - name: harness
        image: ghcr.io/itsPremkumar/hermes-agi-asi-harness:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Helm Chart

```bash
helm install hermes-harness ./helm/hermes-harness \
  --set image.tag=latest \
  --set replicaCount=3
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HERMES_ENV` | `development` | Environment name |
| `HERMES_HOME` | `~/.hermes` | Hermes home directory |
| `LOG_LEVEL` | `INFO` | Logging level |
| `PORT` | `8080` | HTTP port |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `DATABASE_URL` | `sqlite:///hermes.db` | Database connection URL |

## Health Checks

```
GET /health
→ {"status": "healthy", "version": "1.0.0", "checks": {...}}

GET /ready
→ {"ready": true}
```

## Monitoring

```bash
# Start monitoring stack
docker-compose --profile monitoring up -d

# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
```

## Rollback

```bash
# Kubernetes
kubectl rollout undo deployment/hermes-harness

# Docker
docker stop hermes-harness
docker run -d hermes-agi-asi-harness:<previous-tag>
```
