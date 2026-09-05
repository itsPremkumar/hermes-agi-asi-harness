# Hermes AGI/ASI Harness — Test Plan (t_d62fcc6f)

≥40 tests across control plane, safety, and Hermes integration. All must pass.

## harness_control_plane.py — 15 tests

| # | Test | Assertion |
|---|------|-----------|
| CP.1 | Initial state | State is INITIALIZING |
| CP.2 | Initialize sets READY | After init, state = READY |
| CP.3 | Submit task queued | Task added to queue |
| CP.4 | Submit when not ready rejected | RuntimeError if not READY/RUNNING |
| CP.5 | Execute task no plugin | Returns error "No plugin found" |
| CP.6 | Register plugin | Plugin registered with metadata |
| CP.7 | Register duplicate rejected | ValueError on duplicate |
| CP.8 | Unregister plugin | Plugin removed |
| CP.9 | Get plugin by name | Returns correct plugin |
| CP.10 | Get by capability | Returns matching plugins |
| CP.11 | Plugin registry checksum | Checksum computed |
| CP.12 | Safety guard evaluate | SafetyReport returned |
| CP.13 | CRITICAL task rejected | Violations include human approval |
| CP.14 | Shutdown sets state | State = SHUTTING_DOWN then INITIALIZING |
| CP.15 | Result stored | Result retrievable after execution |

## safety_plugin.py — 13 tests

| # | Test | Assertion |
|---|------|-----------|
| SP.1 | Initialize | Plugin initialized |
| SP.2 | Health check | Returns True when initialized |
| SP.3 | Shutdown | Plugin shut down |
| SP.4 | Precheck clean | No violations |
| SP.5 | CRITICAL without human flag rejected | Violation reported |
| SP.6 | Invalid timeout rejected | Violation reported |
| SP.7 | Rate limit per-minute | Violations after limit |
| SP.8 | Rate limit per-hour | Violations after limit |
| SP.9 | Rate limit concurrent | Violations after limit |
| SP.10 | Quota enforcement | Violations after quota |
| SP.11 | Custom rule violation | Custom rule blocks task |
| SP.12 | Anomaly detection | Z-score > threshold detected |
| SP.13 | Anomaly recording | Anomalies retrievable |

## hermes_integration.py — 12 tests

| # | Test | Assertion |
|---|------|-----------|
| HI.1 | Initialize | Plugin initialized |
| HI.2 | Detect profiles | Profiles detected from filesystem |
| HI.3 | List profiles | Returns profile list |
| HI.4 | Get profile | Returns correct profile |
| HI.5 | Read memory (empty) | Returns empty list |
| HI.6 | Write memory | Memory entry created |
| HI.7 | Read memory (after write) | Returns written entry |
| HI.8 | Register skill hook | Hook registered |
| HI.9 | Hook skill task | Returns hooked skill name |
| HI.10 | Gateway status | Returns status dict |
| HI.11 | Shutdown | Plugin shut down |
| HI.12 | Health check | Returns True when initialized |

## Total: 40 tests (15 + 13 + 12)

All tests runnable via `pytest`. Each module independently testable.

Author: @cto
