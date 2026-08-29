# Agent Rate Limiting Platform — Architecture

**Status**: Draft (v1.0)
**Project**: Agent Rate Limiter
**Push target**: `itsPremkumar/agent-rate-limiter`

---

## 1. Overview

The Agent Rate Limiting Platform is a multi-dimensional rate-limiting and
quota-management service that protects agent infrastructure from abuse while
enabling fine-grained control over resource consumption. It enforces limits
**per-user**, **per-app**, and **per-model** using a pluggable strategy
framework (Token Bucket, Sliding Window, Leaky Bucket, Adaptive).

The platform is designed as a **Policy Decision Point (PDP)** that integrates
with an **Enforcement Point (PEP)** — typically an API gateway or an
agent-execution proxy — and a streaming metrics backend for observability.

```
┌─────────────────────────────────────────────────────────────┐
│                     Client / Agent Caller                   │
└──────────────────────┬──────────────────────────────────────┘
                       │  HTTP / gRPC / LangGraph edge call
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Enforcement Point (PEP)  —  API Gateway / Proxy     │
│   ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐  │
│   │ Decision    │  │ Rate Limit  │  │ Forward / Reject / │  │
│   │ Request     │  │ Check Cache │  │ Graceful Degradation│  │
│   └─────────────┘  └─────────────┘  └────────────────────┘  │
└──────────┬──────────────┬─────────────────┬─────────────────┘
           │ gRPC/Redis   │ async events    │ HTTP response
           ▼              ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│               Rate Limiting Service (core PDP)              │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │  Policy      │  │  Strategy    │  │  Counter / State   │ │
│  │  Engine      │  │  Factory     │  │  Store (Redis)     │ │
│  └──────────────┘  └──────────────┘  └────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Quotas & Limits Registry  (config DB / KV store)      │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Observability Pipeline (metrics → Prometheus / OTel)  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Core Concepts

### 2.1 Dimensions (Scopes)

Every rate-limit/quota evaluation is scoped across three first-class
dimensions:

| Dimension | Example | Description |
|-----------|---------|-------------|
| **User** | `user_123` | The authenticated end-user identity. |
| **App**  | `web_app`, `mobile_app`, `cli` | The application or client-type making the call. |
| **Model** | `gpt-4`, `claude-3-opus`, `llama-3-70b` | The underlying LLM/agent model being invoked. |

A limit key is the **composite** of all active dimensions, e.g.:

```
key = "limit:{user_id}:{app_id}:{model_id}"
```

This enables combinations like: *"user A may call gpt-4 at most 60 RPM, but
claude-3 at 30 RPM, while user B has different allowances."*

### 2.2 Strategies

The platform supports four interchangeable rate-limiting strategies. Each is
implemented as a strategy class conforming to the `RateLimitingStrategy`
interface (see API spec).

| Strategy | Mechanism | Use Case | Characteristics |
|----------|-----------|----------|-----------------|
| **Token Bucket** | A bucket with capacity *C*; tokens refill at rate *R* per second; each request consumes one token. | General-purpose bursty traffic; allows short bursts up to *C*. | Simple, efficient, allows bursting. Clock-skew sensitive. |
| **Sliding Window** | Counts requests in a rolling time window (e.g. last 60 s). | Rolling-window limits where "N requests per minute" must be strictly enforced. | Higher memory overhead for sub-windows. Accurate for fixed windows. |
| **Leaky Bucket** | Requests fill a bucket that drains at a constant rate *L*; if bucket overflows, requests are delayed or dropped. | Smoothing output to a fixed rate (e.g. upstream model API quota). | Provides consistent output rate; no bursting. |
| **Adaptive** | Dynamically adjusts the rate limit based on real-time signal (latency, error rate, CPU load). | Protecting degraded backends; throttling under high load. | Feedback control loop; requires metrics integration. |

**Strategy selection** is part of the policy configuration per scope.

### 2.3 Enforcement Modes

| Mode | Behavior |
|------|----------|
| **Hard limit** | Requests exceeding the limit are immediately rejected with HTTP `429 Too Many Requests`. |
| **Soft limit** | Requests are allowed but flagged/queued; warnings are generated. |
| **Graceful degradation** | Under soft-limit conditions, non-critical features are degraded (e.g. fallback to cheaper model, reduced context length) rather than fully rejected. |

---

## 3. Quota System

### 3.1 Quota Granularity

| Level | Period | Description |
|-------|--------|-------------|
| **Daily** | 24 h rolling or fixed-day | e.g. 1 000 model calls per day per user. |
| **Monthly** | Calendar month or 30-day rolling | e.g. 30 000 model calls per month per app. |
| **Burst** | Instantaneous window (e.g. 10 s) | Short-time spikes allowed above steady-state rate. |

### 3.2 Quota Tracking

Each quota is tracked with a **counter** that records consumption against a
reset schedule:

- **Fixed window**: resets at a deterministic calendar boundary.
- **Rolling window**: 30-day sliding window for monthly, 24-hour sliding for
  daily.
- **Burst window**: per-strategy burst counter; refills based on strategy
  parameters.

Counters live in a fast KV store (Redis) with atomic increment operations
(`INCR` + `EXPIRE`) and are replicated asynchronously to the metrics store.

### 3.3 Quota Lifecycle

```
┌────────┐  configure  ┌────────┐  evaluate  ┌──────────┐  exceeded  ┌────────┐
│  Plan  │ ─────────> │  Active │ ─────────> │ Enforcing │ ─────────> │ Blocked  │
└────────┘            └────────┘            └──────────┘            └────────┘
                          │                       │
                          │ reset window          │ grace period
                          ▼                       ▼
                    ┌────────┐            ┌────────────┐
                    │  Plan  │            │  Violation  │
                    │(next)  │            │   record    │
                    └────────┘            └────────────┘
```

When a quota is **exhausted**, the strategy shifts to enforcement-mode
behavior (reject, degrade, or warn). A configurable **grace period** (default
0 s) may let requests through with a warning before hard rejection.

---

## 4. Data Model

### 4.1 Policy Document

```jsonc
{
  "policy_id": "rl_user_app_model_gpt4",
  "scope": {          // composite key dimensions
    "user_id": "user_123",
    "app_id": "web_app",
    "model_id": "gpt-4"
  },
  "strategy": "token_bucket",
  "limits": {
    "requests_per_minute": 60,   // RPM
    "burst_capacity": 20,        // extra burst tokens
    "daily_quota": 10000,        // hard daily cap
    "monthly_quota": 300000
  },
  "enforcement": {
    "mode": "hard_limit",         // hard_limit | soft_limit | graceful_degradation
    "grace_period_seconds": 5,
    "degradation": {              // only if mode == graceful_degradation
      "fallback_model": "gpt-3.5-turbo",
      "reduce_context": true
    }
  },
  "adaptive": {                    // only if strategy == adaptive
    "metrics": ["latency_p95", "error_rate", "cpu_util"],
    "thresholds": {
      "latency_p95_ms": 2000,
      "error_rate_pct": 5.0
    },
    "scale_down_factor": 0.5
  },
  "version": 1,
  "enabled": true,
  "created_at": "2026-09-01T00:00:00Z",
  "updated_at": "2026-09-01T00:00:00Z"
}
```

### 4.2 Counter / State Schema (Redis)

Keys follow the pattern:

```
rate:counter:{policy_id}          # current token count / request count
rate:window:{policy_id}:{epoch}   # per-window counters (sliding window)
rate:bucket:{policy_id}            # last refill timestamp + tokens (token bucket)
quota:daily:{policy_id}:{date_key}  # daily quota counter
quota:monthly:{policy_id}:{month_key} # monthly quota counter
```

### 4.3 Violation Record

```jsonc
{
  "violation_id": "vln_abc123",
  "policy_id": "rl_user_app_model_gpt4",
  "timestamp": "2026-09-01T12:34:56Z",
  "limit_type": "rpm",            // rpm | daily_quota | monthly_quota | burst
  "observed_value": 61,
  "limit_value": 60,
  "enforcement_mode": "hard_limit",
  "action_taken": "rejected"      // rejected | degraded | warned
}
```

---

## 5. Component Architecture

### 5.1 Enforcement Point (PEP)

- **Location**: API gateway (Nginx + Lua / Envoy / Kong) or agent-execution
  proxy layer.
- **Responsibility**: Receive the incoming request, extract identity context
  (user, app, model), call the Rate Limiting Service synchronously, and act on
  the decision.
- **Caching**: Local LRU cache of recent decisions (TTL ~100 ms) to reduce
  round-trips under high QPS. Cache is invalidated by `invalidate` events
  over a message bus.
- **Fallback**: If the Rate Limiting Service is unreachable, the PEP can
  fail-open (allow) or fail-closed (reject) based on a per-policy
  `unavailable_behavior` setting.

### 5.2 Rate Limiting Service (PDP)

- **Language**: Python (>=3.11) or Go; stateless horizontal pod behind a load
  balancer.
- **State store**: Redis (standalone with replication, or Redis Cluster for
  HA) for counter state with sub-millisecond latency.
- **Policy store**: PostgreSQL (or SQLite for single-instance deployments)
  holding policy definitions; changes pushed to Redis via pub/sub for hot
  reload.
- **Strategy engine**: Pluggable strategy dispatch via a factory that maps
  `"strategy"` string → strategy handler. Strategies receive the current
  counter state and return `(allowed: bool, retry_after: float, info: dict)`.
- **Quota engine**: Separate subsystem that wraps strategy decisions with
  hard/soft quota enforcement and graceful-degradation logic.

### 5.3 Observability Pipeline

- **Metrics**: Prometheus metrics exported:
  - `rate_limit_checks_total{result="allowed|denied", strategy="..."}`
  - `rate_limit_decision_latency_seconds`
  - `quota_usage_ratio{period="daily|monthly", ...}`
  - `quota_exhaustion_events_total`
- **Tracing**: OpenTelemetry spans on each decision request.
- **Logging**: Structured JSON logs of every denied request and quota
  exhaustion event.
- **Alerting**: Alertmanager rules for high denial rates, quota exhaustion
  spikes, and service-unavailable fallback triggers.

### 5.4 Management API (Admin)

A separate REST API (see API spec) for creating/updating/deleting policies,
viewing quota usage, and inspecting violation history. Auth-gated behind
admin API keys / OAuth scopes.

---

## 6. Request Flow

```
1. Client -> PEP (API Gateway / Proxy)
2. PEP extracts: user_id, app_id, model_id
3. PEP -> PDP: POST /v1/decide  {scope, model, strategy_hint?}
4. PDP:
   4a. Lookup active policy for (user_id, app_id, model_id)
   4b. Check daily/monthly quota counters (Redis atomic incr/expire)
   4c. Run strategy check (token bucket refill + token consume)
   4d. Apply enforcement mode (hard/soft/degrade)
   4e. If denied: record violation, return {allowed: false, retry_after, reason}
       If allowed: increment counters, return {allowed: true}
5. PEP acts on decision:
   - allowed=true  -> forward request to upstream model/agent
   - allowed=false -> return 429 / degrade / warn
6. PDP emits metrics + (async) writes violation/usage logs
```

---

## 7. Strategy Implementation Details

### 7.1 Token Bucket

```
State: { tokens: float, last_refill: unix_ms }
On each request:
  1. tokens = min(capacity, tokens + (now - last_refill) * refill_rate)
  2. if tokens >= 1:
       tokens -= 1
       last_refill = now
       allowed = true
     else:
       allowed = false
  3. Persist { tokens, last_refill }
```

- `refill_rate = requests_per_minute / 60`
- `capacity = requests_per_minute + burst_capacity`

### 7.2 Sliding Window

Uses a **fixed-window log** or **rolling-sum** approach depending on precision
vs. memory tradeoff:

- **Log-based** (high precision): store timestamps of each request in a sorted
  set; trim entries older than the window; count = length of the set.
- **Counter-based** (lower precision, less memory): keep two counters for the
  current and previous sub-windows and interpolate.

### 7.3 Leaky Bucket

```
State: { water: float, last_drain: unix_ms }
On each request:
  1. water = max(0, water - (now - last_drain) * leak_rate)
  2. if water + request_size <= capacity:
       water += request_size
       allowed = true
     else:
       allowed = false  // or queue for delay
  3. Persist { water, last_drain }
```

### 7.4 Adaptive

A feedback controller that adjusts the effective `requests_per_minute` based
on upstream health signals:

```
if latency_p95 > threshold OR error_rate > threshold:
    effective_rpm = base_rpm * scale_down_factor
else:
    effective_rpm = base_rpm
```

Health signals are pulled from Prometheus or pushed via a metrics feed
(e.g. OpenTelemetry PipelineSignal).

---

## 8. High Availability & Reliability

| Concern | Approach |
|---------|----------|
| **Counter state** | Redis with AOF persistence + replication. For multi-region, use Redis Enterprise or CRDT-based stores. |
| **Policy config** | PostgreSQL with synchronous replicas; hot-reload via Redis pub/sub `policy:update` channel. |
| **PEP failover** | PEP caches last N decisions locally; fail-open or fail-closed configurable. |
| **PDP scaling** | Stateless pods behind load balancer; Redis connection pooling per pod. |
| **Race conditions** | All counter mutations use Redis Lua scripts or `MULTI/EXEC` for atomicity. |

---

## 9. Security Considerations

- **Policy integrity**: All policy mutations require admin auth (OAuth2
  `admin:policies` scope). No anonymous write access.
- **Rate limit on the rate limiter**: Meta-rate-limiting to prevent a flood of
  decide-requests from overwhelming the PDP itself.
- **No secrets in violations**: Violation records contain no PII or API keys.
- **Audit log**: All policy create/update/delete events are written to an
  append-only audit stream.

---

## 10. Deployment

- **Single-instance**: SQLite (policy store) + Redis (state) + in-process PEP
  for simplicity in dev / small deployments.
- **Production**: Kubernetes Deployment for PDP pods, StatefulSet for Redis
  (or managed Redis), PostgreSQL HA cluster, Envoy as PEP.
- **CI/CD**: Pushes to `main` trigger Docker image build + Helm chart deploy.

---

## 11. API Integration Points

The platform exposes two API surfaces:

1. **Decision API** (sync, low-latency) — used by the PEP:
   - `POST /v1/decide`
2. **Management API** (admin, async) — used by operators and dashboards:
   - `GET/POST/PUT/DELETE /v1/policies`
   - `GET /v1/quotas`
   - `GET /v1/metrics`
   - `GET /v1/violations`

Full contract is specified in `docs/api-spec.yaml`.
Quota definitions and lifecycle are specified in `docs/quota-spec.md`.
