# 3. Integration Patterns

This document describes the integration patterns used within the harness and for connecting to external systems. It covers API contracts, event-driven communication, data flow, and error handling.

---

## 3.1 Internal Component Integration

### Pattern 1: Event-Driven Messaging

All internal components communicate via the Event Bus. This decouples producers from consumers and enables replay, audit, and monitoring.

```
Component A --publish--> Event Bus --deliver--> Component B
                                      --deliver--> Component C
                                      --deliver--> Audit Log
```

**Contract**: Components must declare the event types they publish and subscribe to. Events are schema-validated on publish.

**Guarantees**:
- At-least-once delivery (idempotent consumers required)
- Ordering per task ID across partitions
- Durable persistence before acknowledgment

### Pattern 2: Request-Response via Agent Bridge

For synchronous operations (safety checks, status queries), the Agent Bridge provides a request-response pattern over the event bus.

```
Scheduler --request--> Agent Bridge --check--> Safety Governor
                                      <--result-- Safety Governor
```

**Timeout**: 5 seconds default, configurable per operation type.

**Fallback**: On timeout, the operation is retried once with exponential backoff. If still failing, the task is marked for retry or escalation.

### Pattern 3: Streaming for Real-Time Output

Agent output streams use Server-Sent Events (SSE) for real-time delivery to dashboards and monitoring.

```
Agent Runtime --SSE--> Event Bus --SSE--> Dashboard
                                  --SSE--> WebSocket Gateway
```

**Backpressure**: Consumers signal readiness via flow control messages. Producers pause when consumers fall behind.

---

## 3.2 External System Integration

### Pattern 4: Adapter Pattern for External APIs

External systems (LLM providers, web search, GitHub) are accessed via adapters that implement a common interface.

```python
class ExternalAdapter(ABC):
    @abstractmethod
    async def connect(self) -> ConnectionHandle:
        """Establish connection to external system."""

    @abstractmethod
    async def execute(self, request: AdapterRequest) -> AdapterResponse:
        """Execute an operation on the external system."""

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check if the external system is reachable."""

    @abstractmethod
    async def disconnect(self):
        """Gracefully close the connection."""
```

**Adapter Registry**: All adapters are registered in the Plugin Registry and discovered at startup.

**Circuit Breaker**: Each adapter has a circuit breaker that opens after 5 consecutive failures, preventing cascade failures.

### Pattern 5: Webhook Integration

External systems can push events to the harness via webhooks.

```
External System --HTTP POST--> Webhook Gateway --> Event Bus
```

**Security**: Webhook payloads are verified using HMAC-SHA2556 signatures.

**Idempotency**: Webhook events include idempotency keys to prevent duplicate processing.

### Pattern 6: Polling for Status

For external systems that don't support webhooks, the harness uses adaptive polling.

```
Poll Scheduler --request--> Adapter --> External System
                     <--response-- Adapter
```

**Adaptive Interval**: Polling interval increases exponentially when no changes are detected (1s → 5s → 30s → 60s). Resets to 1s on change detection.

---

## 3.3 API Design Patterns

### Pattern 7: RESTful Resource API

The primary external API follows REST conventions.

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/tasks | Submit a new task |
| GET | /v1/tasks/{id} | Get task status |
| DELETE | /v1/tasks/{id} | Cancel a task |
| GET | /v1/agents | List registered agents |
| POST | /v1/safety/estop | Trigger emergency stop |
| GET | /v1/health | Health check |

**Versioning**: API version is in the URL path (v1, v2). Breaking changes require a new version.

**Pagination**: List endpoints use cursor-based pagination for consistency under concurrent modifications.

### Pattern 8: GraphQL for Complex Queries

For dashboard and monitoring queries, a GraphQL endpoint provides flexible data fetching.

```graphql
query {
  tasks(status: RUNNING, limit: 10) {
    id
    type
    agent { name status }
    progress
    safetyEvents { gate decision timestamp }
  }
}
```

**Authorization**: GraphQL resolvers enforce field-level authorization based on the caller's role.

### Pattern 9: gRPC for Internal Services

High-performance internal communication uses gRPC with Protocol Buffers.

```protobuf
service SchedulerService {
  rpc SubmitTask(SubmitTaskRequest) returns (TaskHandle);
  rpc CancelTask(CancelTaskRequest) returns (CancelResponse);
  rpc StreamEvents(StreamRequest) returns (stream HarnessEvent);
}
```

**Benefits**: Strong typing, binary efficiency, bidirectional streaming, deadline propagation.

---

## 3.4 Data Flow Patterns

### Pattern 10: CQRS (Command Query Responsibility Segregation)

Commands (state changes) and queries (reads) use separate models.

```
Command --> Command Handler --> Event Bus --> Projection --> Read Model
Query   --> Query Handler   --> Read Model
```

**Event Sourcing**: The event bus is the source of truth. Read models are projections that can be rebuilt from events.

### Pattern 11: Saga Pattern for Distributed Transactions

Long-running operations that span multiple components use the saga pattern for consistency.

```
Saga Orchestrator
  Step 1: Reserve resources     --> Resource Manager
  Step 2: Dispatch task         --> Scheduler
  Step 3: Monitor execution     --> Agent Bridge
  Compensate (if failure):
    Step 2: Release resources   --> Resource Manager
    Step 1: Mark task failed    --> Event Bus
```

**Compensation**: Each step has a compensating action that undoes its effects. Compensations are applied in reverse order.

### Pattern 12: Outbox Pattern for Reliable Publishing

Components that must both update state and publish events use the outbox pattern.

```
1. Begin transaction
2. Update component state
3. Insert event into outbox table
4. Commit transaction
5. Outbox publisher reads from outbox
6. Publish event to Event Bus
7. Mark event as published
```

**Guarantees**: Events are never lost, even if the component crashes after the commit.

---

## 3.5 Error Handling Patterns

### Pattern 13: Retry with Exponential Backoff

Transient failures are handled with bounded retries.

```
Attempt 1 --> Fail --> Wait 1s
Attempt 2 --> Fail --> Wait 2s
Attempt 3 --> Fail --> Wait 4s
Attempt 4 --> Fail --> Escalate
```

**Jitter**: Random jitter (±25%) is added to prevent thundering herd.

**Max Retries**: 3 attempts by default, configurable per operation type.

### Pattern 14: Fallback Chain

When primary integration fails, fallbacks are tried in sequence.

```
Primary LLM (GPT-4) --> Fail
Fallback 1 (Claude) --> Fail
Fallback 2 (Local Model) --> Fail
Escalate to operator
```

**Health-Based Routing**: Unhealthy endpoints are automatically removed from the fallback chain.

### Pattern 15: Dead Letter Queue

Events that cannot be processed after max retries are sent to a dead letter queue.

```
Event --> Process --> Fail (x3)
       --> Dead Letter Queue
       --> Alert Operator
       --> Manual inspection/replay
```

**Retention**: Dead letter events are retained for 30 days with full context for debugging.

---

## 3.6 Security Integration Patterns

### Pattern 16: mTLS for Internal Communication

All internal service-to-service communication uses mutual TLS.

```
Service A --mTLS--> Service B
   ↓                  ↓
Certificate        Certificate
(rotated every 24h) (rotated every 24h)
```

**Certificate Management**: Automated rotation via cert-manager in Kubernetes.

### Pattern 17: OAuth 2.0 / OIDC for External APIs

External API access uses OAuth 2.0 with PKCE for public clients.

```
Client --> Authorization Server --> Access Token
         --> API Request (with token) --> Resource Server
```

**Token Lifespan**: Access tokens expire in 15 minutes. Refresh tokens expire in 24 hours.

### Pattern 18: Secret Management

Secrets are never stored in code or configuration files.

```
Secret Reference: ${secrets.llm_api_key}
         ↓
Secret Manager (HashiCorp Vault / K8s Secrets)
         ↓
Injected at runtime via sidecar
```

**Rotation**: Secrets are rotated automatically every 30 days. Applications reload secrets without restart.

---

## 3.7 Observability Integration

### Pattern 19: OpenTelemetry for Distributed Traces

All components export traces via OpenTelemetry.

```
Component A --> Trace Span --> OpenTelemetry Collector --> Jaeger/Tempo
Component B --> Trace Span --> OpenTelemetry Collector --> Jaeger/Tempo
```

**Sampling**: 100% for errors, 10% for successful operations (adaptive sampling).

### Pattern 20: Structured Logging

All logs are emitted as JSON with correlation fields.

```json
{
  "timestamp": "2026-08-31T12:00:00Z",
  "level": "info",
  "component": "scheduler",
  "trace_id": "abc123",
  "task_id": "task-456",
  "message": "Task dispatched to agent",
  "data": { "agent_id": "agent-789" }
}
```

**Log Levels**: DEBUG, INFO, WARN, ERROR, CRITICAL. Default is INFO in production.

---

*Next: [Deployment Architecture](04-deployment-architecture.md)*
