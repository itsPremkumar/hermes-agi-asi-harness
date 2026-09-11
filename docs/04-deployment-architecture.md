# 4. Deployment Architecture

This document describes how the AGI/ASI Harness is deployed, scaled, and operated in production environments.

---

## 4.1 Deployment Models

### Model 1: Single-Node Development

For local development and testing.

```
┌─────────────────────────────────────────┐
│              Single Node                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ API GW  │  │Scheduler│  │ Safety  │ │
│  └─────────┘  └─────────┘  └─────────┘ │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ EventBus│  │Plugins  │  │ Storage │ │
│  └─────────┘  └─────────┘  └─────────┘ │
└─────────────────────────────────────────┘
```

**Requirements**: 8GB RAM, 4 CPU cores, 50GB storage.

**Use Case**: Individual developers, CI/CD testing, demos.

### Model 2: High-Availability Cluster

For production workloads requiring fault tolerance.

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
└─────────────────────────────────────────────────────────┘
         │                    │                    │
┌────────┴────────┐ ┌────────┴────────┐ ┌────────┴────────┐
│   Control Plane  │ │   Control Plane  │ │   Control Plane  │
│   (Active)       │ │   (Standby)      │ │   (Standby)      │
│   ┌───────────┐  │ │   ┌───────────┐  │ │   ┌───────────┐  │
│   │ API GW    │  │ │   │ API GW    │  │ │   │ API GW    │  │
│   │ Scheduler │  │ │   │ Scheduler │  │ │   │ Scheduler │  │
│   │ Safety    │  │ │   │ Safety    │  │ │   │ Safety    │  │
│   └───────────┘  │ │   └───────────┘  │ │   └───────────┘  │
│   ┌───────────┐  │ │   ┌───────────┐  │ │   ┌───────────┐  │
│   │ Event Bus │  │ │   │ Event Bus │  │ │   │ Event Bus │  │
│   │ (Raft)    │  │ │   │ (Raft)    │  │ │   │ (Raft)    │  │
│   └───────────┘  │ │   └───────────┘  │ │   └───────────┘  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
         │                    │                    │
┌────────┴────────────────────┴────────────────────┴────────┐
│                    Shared Storage (PostgreSQL)              │
└────────────────────────────────────────────────────────────┘
```

**Requirements**: 3+ control plane nodes, shared storage, load balancer.

**Use Case**: Production deployments, multi-tenant setups.

### Model 3: Kubernetes-Native

For cloud-native deployments with auto-scaling.

```
┌─────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Namespace: harness-system                            │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │    │
│  │  │ API Gateway │  │ API Gateway │  │ API Gateway │ │    │
│  │  │ (Deployment)│  │ (Deployment)│  │ (Deployment)│ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │    │
│  │  ┌─────────────┐  ┌─────────────┐                  │    │
│  │  │ Control     │  │ Control     │  (StatefulSet)   │    │
│  │  │ Plane 1     │  │ Plane 2     │                  │    │
│  │  └─────────────┘  └─────────────┘                  │    │
│  │  ┌─────────────────────────────────────┐           │    │
│  │  │ Event Bus (NATS Cluster)            │           │    │
│  │  └─────────────────────────────────────┘           │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Namespace: harness-agents                            │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │    │
│  │  │ Agent Pool  │  │ Agent Pool  │  │ Agent Pool  │ │    │
│  │  │ (DMAR)      │  │ (v9)        │  │ (AVO)       │ │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Requirements**: Kubernetes 1.28+, Helm 3, cert-manager, ingress controller.

**Use Case**: Cloud deployments, auto-scaling, multi-region.

---

## 4.2 Kubernetes Deployment

### Namespace Structure

```
harness-system       # Core control plane components
harness-agents       # Agent runtime pools
harness-plugins      # Plugin sandboxes
harness-monitoring   # Observability stack
harness-secrets      # Sealed secrets, vault
```

### Core Components

#### API Gateway

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: harness-api-gateway
  namespace: harness-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: harness-api-gateway
  template:
    metadata:
      labels:
        app: harness-api-gateway
    spec:
      containers:
        - name: api-gateway
          image: harness/api-gateway:latest
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi
          env:
            - name: EVENT_BUS_URL
              valueFrom:
                configMapKeyRef:
                  name: harness-config
                  key: event_bus_url
            - name: SAFETY_GATE_ENDPOINT
              value: "http://harness-safety:8080"
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
```

#### Control Plane (StatefulSet for Raft)

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: harness-control-plane
  namespace: harness-system
spec:
  serviceName: harness-control-plane
  replicas: 3
  selector:
    matchLabels:
      app: harness-control-plane
  template:
    metadata:
      labels:
        app: harness-control-plane
    spec:
      containers:
        - name: control-plane
          image: harness/control-plane:latest
          ports:
            - containerPort: 8080
            - containerPort: 9090  # Raft
          resources:
            requests:
              cpu: 1000m
              memory: 2Gi
            limits:
              cpu: 4000m
              memory: 8Gi
          volumeMounts:
            - name: raft-data
              mountPath: /data/raft
  volumeClaimTemplates:
    - metadata:
        name: raft-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

#### Event Bus (NATS Cluster)

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: harness-event-bus
  namespace: harness-system
spec:
  serviceName: harness-event-bus
  replicas: 3
  selector:
    matchLabels:
      app: harness-event-bus
  template:
    metadata:
      labels:
        app: harness-event-bus
    spec:
      containers:
        - name: nats
          image: nats:2.10-alpine
          ports:
            - containerPort: 4222  # Client
            - containerPort: 8222  # HTTP
            - containerPort: 6222  # Cluster
          command:
            - "--cluster"
            - "nats://0.0.0.0:6222"
            - "--store_dir"
            - "/data/nats"
          volumeMounts:
            - name: nats-data
              mountPath: /data/nats
  volumeClaimTemplates:
    - metadata:
        name: nats-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi
```

### Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: harness-ingress
  namespace: harness-system
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
    - hosts:
        - harness.example.com
      secretName: harness-tls
  rules:
    - host: harness.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: harness-api-gateway
                port:
                  number: 8080
```

---

## 4.3 Configuration Management

### ConfigMap Structure

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: harness-config
  namespace: harness-system
data:
  event_bus_url: "nats://harness-event-bus:4222"
  storage_url: "postgresql://harness:5432/harness"
  log_level: "info"
  scheduler_algorithm: "edf"
  max_concurrent_tasks: "100"
  safety_default_policy: "deny"
  plugin_auto_load: "true"
  plugin_sandbox_enabled: "true"
```

### Secret Management

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: harness-secrets
  namespace: harness-system
type: Opaque
stringData:
  llm_api_key: "${LLM_API_KEY}"
  hermes_api_token: "${HERMES_API_TOKEN}"
  db_password: "${DB_PASSWORD}"
```

**Rotation**: Secrets are rotated via external-secrets operator syncing from HashiCorp Vault.

---

## 4.4 Scaling Strategies

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: harness-api-gateway-hpa
  namespace: harness-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: harness-api-gateway
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"
```

### Agent Pool Scaling

Agent pools scale based on queue depth:

```
Queue Depth > 100  --> Scale up (+2 agents)
Queue Depth < 10   --> Scale down (-1 agent)
Max agents per pool: 50
```

### Event Bus Scaling

NATS cluster scales based on connection count:

```
Connections > 1000  --> Add node
Connections < 100   --> Remove node (graceful)
```

---

## 4.5 Storage Architecture

### PostgreSQL (Primary Store)

```
┌─────────────────────────────────────────┐
│            PostgreSQL Cluster            │
│  ┌─────────────┐  ┌─────────────┐      │
│  │   Primary   │──│  Standby    │      │
│  │  (Read/Write)│  │  (Read)     │      │
│  └─────────────┘  └─────────────┘      │
│         │                               │
│  ┌──────┴──────┐                        │
│  │ WAL Archive │                        │
│  │  (S3/GCS)   │                        │
│  └─────────────┘                        │
└─────────────────────────────────────────┘
```

**Tables**:
- `tasks` — Task records
- `events` — Event store (append-only)
- `agents` — Agent registry
- `safety_decisions` — Audit trail
- `resource_allocations` — Budget tracking

### NATS JetStream (Event Store)

- Retention: 7 days for raw events
- Replication: 3x across cluster
- Storage: SSD-backed volumes

### Object Storage (Checkpoints)

- S3/GCS for checkpoint archives
- Lifecycle: 30 days, then archive to cold storage
- Encryption: AES-256 server-side

---

## 4.6 Network Architecture

### Service Mesh (Optional)

For complex deployments, Istio provides:
- mTLS between all services
- Traffic management (canary, blue-green)
- Observability (metrics, access logs)

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: harness-control-plane-policy
  namespace: harness-system
spec:
  podSelector:
    matchLabels:
      app: harness-control-plane
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: harness-api-gateway
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: harness-event-bus
      ports:
        - protocol: TCP
          port: 4222
```

---

## 4.7 Disaster Recovery

### Backup Strategy

| Data | Frequency | Retention | Method |
|------|-----------|-----------|--------|
| PostgreSQL | Continuous (WAL) + Daily full | 30 days | pg_basebackup + WAL-G |
| NATS streams | Hourly snapshot | 7 days | NATS built-in |
| Checkpoints | On-demand | 30 days | S3 versioning |
| ConfigMaps | On change | Forever | GitOps (Flux) |

### Recovery Objectives

| Scenario | RPO | RTO |
|----------|-----|-----|
| Single pod failure | 0 | < 30s |
| Node failure | 0 | < 2 min |
| AZ failure | < 1 min | < 5 min |
| Region failure | < 5 min | < 30 min |

### Multi-Region Deployment

```
Region A (Active)                Region B (Standby)
┌──────────────────┐             ┌──────────────────┐
│ Control Plane    │────────────│ Control Plane    │
│ (Primary)        │  Async Repl│ (Standby)        │
│ Event Bus        │────────────│ Event Bus        │
│ Storage          │────────────│ Storage          │
└──────────────────┘             └──────────────────┘
```

---

## 4.8 Security Hardening

### Pod Security Standards

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: harness-system
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### Container Security

- Non-root user (UID 1000)
- Read-only root filesystem
- Dropped all capabilities
- Seccomp profile: runtime/default
- No privilege escalation

### Image Security

- Images scanned for vulnerabilities (Trivy)
- Only signed images accepted (Cosign)
- Base images distroless or slim

---

## 4.9 Cost Optimization

### Resource Right-Sizing

- Start with requests = limits for predictable workloads
- Use VPA for recommendation, then tune manually
- Burstable QoS for non-critical components

### Spot/Preemptible Instances

- Agent pools can run on spot instances
- Checkpoint before preemption (SIGTERM handler)
- Fallback to on-demand if spot unavailable

### Storage Tiering

- Hot: SSD for active data (< 7 days)
- Warm: Standard disk (7-30 days)
- Cold: Archive storage (> 30 days)

---

## 4.10 Migration and Upgrade

### Rolling Updates

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

### Blue-Green Deployment

For major versions:
1. Deploy new version alongside old
2. Switch traffic via load balancer
3. Monitor for 24 hours
4. Decommission old version

### Database Migrations

- Run as Kubernetes Job before rolling update
- Backward-compatible changes only (expand-contract pattern)
- Rollback plan documented for each migration

---

*End of Architecture & System Spec*
