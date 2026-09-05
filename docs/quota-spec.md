# Quota Specification — Agent Rate Limiting Platform

**Version**: 1.0
**Status**: Draft

---

## 1. Purpose

This document specifies the **quota system** of the Agent Rate Limiting
Platform: how quotas are defined, tracked, enforced, and observed. A quota is
a **bounded consumption limit** applied over a fixed or rolling time period,
enforced independently of (but in coordination with) the rate-limiting
strategy.

Quotas protect upstream resources (model API budgets, compute quotas,
billing caps) by ensuring no single scope (user / app / model) exceeds a
pre-defined allowance within a billing or operational period.

---

## 2. Quota Model

### 2.1 Definition

A quota is defined as part of a **Policy** (see `docs/api-spec.yaml`, schema
`Policy.limits`). The relevant fields are:

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `daily_quota` | int | requests | Maximum requests allowed in a 24-hour period. |
| `monthly_quota` | int | requests | Maximum requests allowed in a 30-day or calendar-month period. |
| `burst_quota` | int | requests | Maximum requests allowed in a short instantaneous window (e.g. 10 s). Typically governed by the strategy's `burst_capacity`. |
| `requests_per_minute` | int | requests/min | Steady-state rate enforced by the chosen strategy. |

All quota fields are **optional** except `requests_per_minute`. A policy may
define any combination of daily, monthly, and burst quotas.

### 2.2 Composite Key

Each quota counter is keyed by the policy's composite scope:

```
quota:{period}:{policy_id}:{reset_key}
```

Where:
- `{period}` ∈ {`daily`, `monthly`, `burst`}
- `{policy_id}` is the unique policy identifier
- `{reset_key}` is the period-specific reset identifier:
  - `daily`: ISO date `YYYY-MM-DD` (fixed) or rolling epoch day
  - `monthly`: ISO month `YYYY-MM` (calendar) or rolling 30-day epoch
  - `burst`: epoch bucket (e.g. `floor(unix_seconds / 10)`)

### 2.3 Quota Scope Matrix

| Quota Type | Granularity | Example |
|------------|-------------|---------|
| Daily | Per (user, app, model) | User `user_123` calling `gpt-4` from `web_app` gets 10 000 requests/day. |
| Monthly | Per (user, app, model) | Same scope gets 300 000 requests/month. |
| Burst | Per (user, app, model) | Short spike allowance of 20 extra tokens in a 10 s window. |
| RPM | Per (user, app, model) | 60 requests/minute steady-state. |

---

## 3. Period Types & Reset Semantics

### 3.1 Daily Quota

- **Fixed-day** (default): Counter resets at midnight UTC for calendar-day
  boundaries. `reset_key = YYYY-MM-DD`.
- **Rolling-24h** (configurable): Counter covers the trailing 24 hours from
  the last request. `reset_key = floor(unix_seconds / 86400)`.

The period mode is configured at the policy level via
`limits.daily_period` (`fixed` | `rolling`, default `fixed`).

### 3.2 Monthly Quota

- **Calendar month** (default): Resets on the 1st of each month at 00:00 UTC.
  `reset_key = YYYY-MM`.
- **Rolling-30-day** (configurable): Counter covers the trailing 30 days.
  `reset_key = floor(unix_seconds / 2592000)`.

Configured via `limits.monthly_period` (`calendar` | `rolling`,
default `calendar`).

### 3.3 Burst Quota

- Governed by the strategy's `burst_capacity` and refill rate.
- For Token Bucket: burst tokens regenerate over time; no separate counter —
  the bucket's `tokens` field IS the burst state.
- For Sliding Window / Leaky Bucket: a short rolling counter
  (`window_seconds` configurable, default 10 s) is maintained.

### 3.4 Reset Key Computation

The reset key determines which counter bucket a request falls into. When the
key changes, the old bucket expires and a new one begins.

```
# Fixed day example:
reset_key = datetime.utcnow().strftime("%Y-%m-%d")

# Rolling 24h example:
reset_key = str(int(unix_time) // 86400)

# Calendar month example:
reset_key = datetime.utcnow().strftime("%Y-%m")

# Rolling 30-day example:
reset_key = str(int(unix_time) // 2592000)
```

---

## 4. Counter Mechanics

### 4.1 Atomic Increment

All quota counter increments are performed via **atomic Redis operations**
to prevent race conditions under concurrent load:

```lua
-- Lua script for Redis (atomic)
local key = KEYS[1]
local limit = ARGV[1]
local used = redis.call('INCR', key)
if used == 1 then
    -- Set TTL only on first increment in this period
    redis.call('EXPIRE', key, ARGV[2])  -- ARGV[2] = period_seconds
end
if used > limit then
    return 0  -- denied
end
return 1  -- allowed
```

The TTL ensures expired periods are garbage-collected automatically.

### 4.2 Counter Reset

Two reset mechanisms:

1. **TTL-based**: The Redis key expires automatically at the end of the period
   (fixed-day or rolling). New period starts fresh.
2. **Explicit check**: For calendar-month boundaries, the service compares the
   current `reset_key` against the stored one. If different, the counter is
   reset to 0 and the new key is stored.

### 4.3 Counter Replication (HA)

In HA mode, both mechanisms use **Redis with AOF + replication**. For
multi-region, either:
- **Redis Enterprise Active-Active** (CRDT-based multi-region), or
- **Read repair with vector clocks** on a strongly-consistent store.

---

## 5. Enforcement Logic

### 5.1 Decision Sequence

When a `/v1/decide` request arrives, the PDP performs checks in this order:

```
1. Policy lookup  →  resolve policy for (user, app, model)
2. Strategy check →  run strategy (token bucket / sliding window / …)
3. Daily quota    →  INCR + TTL, compare against daily_quota
4. Monthly quota  →  INCR + TTL, compare against monthly_quota
5. Burst check    →  strategy-dependent
6. Enforcement    →  apply mode: hard_limit / soft_limit / graceful_degradation
7. Response       →  return { allowed, retry_after, reason, ... }
```

Each step that **denies** short-circuits subsequent steps and returns the
decision immediately. The `retry_after` value is the **maximum** of all
applicable retry windows.

### 5.2 Enforcement Modes & Quota Exhaustion

| Mode | Action on Quota Exhaustion |
|------|-----------------------------|
| **Hard limit** | Reject with `allowed=false`, `retry_after` = time until next reset. |
| **Soft limit** | Allow request but emit a warning metric `quota_exhausted_warning_total`. Set `allowed=true` with a `warning` field in the response. |
| **Graceful degradation** | Downgrade the request: route to a fallback model, reduce context window, or drop non-essential features. `allowed=true` with `degradation` instructions in the response. |

### 5.3 Retry-After Calculation

| Quota Type | Formula for `retry_after` |
|------------|---------------------------|
| RPM (strategy) | `1 / (tokens / window_seconds)` if bucket empty |
| Daily (fixed) | `seconds_until_next_utc_midnight` |
| Daily (rolling) | `period_seconds - (now - window_start)` |
| Monthly (calendar) | `seconds_until_next_month_1_00:00_UTC` |
| Monthly (rolling) | `2592000 - (now - window_start)` |
| Burst | `strategy_retry_after` (time until next token/bucket refill) |

If multiple quotas are exhausted simultaneously, `retry_after` is the **max**
across all exhausted quotas (the caller should wait until all are available).

---

## 6. Quota Lifecycle

```
┌──────────┐     create/update     ┌──────────┐
│  Draft   │ ────────────────────> │  Active  │
└──────────┘                        └──────────┘
                                         │
                              ┌──────────┴──────────┐
                              ▼                      ▼
                    quota exhaustion          quota refill
                              │                      │
                              ▼                      ▼
                     ┌─────────────┐        ┌─────────────┐
                     │  Exhausted  │ ◄────── │  Recovered  │
                     └─────────────┘        └─────────────┘
                              │                      │
                              ▼                      │
                    enforcement mode decision        │
                              │                      │
                     ┌────────┴────────┐             │
                     ▼                 ▼             │
               ┌──────────┐    ┌───────────┐          │
               │ Rejected │    │ Degraded  │ ─────────┘
               └──────────┘    └───────────┘
                     │                 │
                     ▼                 ▼
               violation record   degradation record
```

### 6.1 States

| State | Meaning |
|-------|---------|
| **Draft** | Policy exists in config but not yet pushed to the enforcement layer. |
| **Active** | Policy is live; quota counters are being tracked and enforced. |
| **Exhausted** | One or more quota periods have been fully consumed for this scope. |
| **Recovered** | The quota period has reset and consumption is below the limit again. |

### 6.2 Transitions

- `Active → Exhausted`: Triggered when `used >= limit` for any period.
- `Exhausted → Recovered`: Triggered at period reset when the new period's
  counter starts (always recovered at reset, since the new counter is 0).

---

## 7. Quota Usage API

### 7.1 Real-time Snapshot

`GET /v1/quotas?user_id=...&app_id=...&model_id=...`

Returns the current `QuotaInfo` for every applicable period:

```jsonc
{
  "scopes": [
    {
      "policy_id": "rl_user_app_model_gpt4",
      "scope": { "user_id": "user_123", "app_id": "web_app", "model_id": "gpt-4" },
      "period": "daily",
      "limit": 10000,
      "used": 8742,
      "remaining": 1258,
      "reset_at": "2026-09-02T00:00:00Z",
      "exhausted": false
    },
    {
      "policy_id": "rl_user_app_model_gpt4",
      "scope": { "user_id": "user_123", "app_id": "web_app", "model_id": "gpt-4" },
      "period": "monthly",
      "limit": 300000,
      "used": 156800,
      "remaining": 143200,
      "reset_at": "2026-10-01T00:00:00Z",
      "exhausted": false
    }
  ]
}
```

### 7.2 Quota Warning Threshold

When `used / limit >= 0.90` (configurable warning threshold), the platform
emits a `quota_warning_threshold_reached_total` metric and (optionally)
sends a notification via the configured alert channel.

---

## 8. Observability

### 8.1 Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `quota_usage_ratio` | Gauge | `used / limit` per quota period, tagged by scope. |
| `quota_exhaustion_events_total` | Counter | Incremented each time a quota is exhausted. |
| `quota_exhausted_warning_total` | Counter | Incremented when warning threshold is crossed. |
| `quota_reset_events_total` | Counter | Incremented at each period reset. |
| `quota_recovery_events_total` | Counter | Incremented when an exhausted quota becomes available again. |

### 8.2 Logs

Structured JSON logs are emitted for:

1. **Quota exhaustion**: `{"event": "quota_exhausted", "policy_id": ..., "period": "daily", "scope": {...}, "used": ..., "limit": ...}`
2. **Period reset**: `{"event": "quota_reset", "policy_id": ..., "period": "monthly", "new_reset_key": ...}`
3. **Warning threshold breach**: `{"event": "quota_warning", "policy_id": ..., "ratio": 0.92, ...}`

### 8.3 Audit Trail

All policy mutations (create, update, delete, enable, disable) are appended
to an immutable audit log stream with:
- Timestamp
- Actor (user/service)
- Action
- Policy diff (before/after)

---

## 9. Configuration

### 9.1 Default Quota Template

A template can be applied to all new policies (or all new users/apps):

```jsonc
{
  "template_id": "default_agent_quota",
  "limits": {
    "requests_per_minute": 60,
    "burst_capacity": 20,
    "daily_quota": 10000,
    "monthly_quota": 300000
  },
  "quota_period": {
    "daily": "fixed",
    "monthly": "calendar"
  },
  "warning_threshold": 0.90
}
```

### 9.2 Per-Scope Overrides

Quotas can be overridden at more specific scopes:

| Scope Level | Override Example |
|-------------|-----------------|
| Global default | 60 RPM / 10 000 daily / 300 000 monthly |
| Per-user | `user_123`: 120 RPM / 20 000 daily |
| Per-app | `mobile_app`: 30 RPM / 5 000 daily |
| Per-model | `gpt-4`: 60 RPM; `claude-3`: 30 RPM |
| Per-user+app+model | Most specific; wins over all others. |

Precedence (highest wins): **user+app+model > model > app > user > global**.

---

## 10. Error Handling

### 10.1 Quota Store Unavailable

If the quota counter store (Redis) is unreachable during a decision:

| Config | Behavior |
|--------|----------|
| `unavailable_behavior: fail_closed` (default) | Deny the request with `allowed=false`, `retry_after=0`, `reason="quota_store_unavailable"`. |
| `unavailable_behavior: fail_open` | Allow the request but emit a `quota_store_unavailable_total` metric for post-hoc reconciliation. |

### 10.2 Inconsistent State

If a counter's TTL has not expired but the `reset_key` has changed (e.g.
clock drift, manual reset), the service detects the mismatch, logs a warning,
and reinitializes the counter for the new key.

---

## 11. Summary

| Aspect | Specification |
|--------|---------------|
| **Periods** | Daily (fixed/rolling), Monthly (calendar/rolling), Burst |
| **Granularity** | Per (user, app, model) composite |
| **Reset mechanism** | TTL-based + explicit reset_key check |
| **Enforcement** | hard_limit / soft_limit / graceful_degradation |
| **Counter store** | Redis (atomic Lua scripts) |
| **HA** | Redis replication / Redis Enterprise |
| **Warning threshold** | 90% (configurable) |
| **Audit** | Immutable append-only log of policy mutations |
