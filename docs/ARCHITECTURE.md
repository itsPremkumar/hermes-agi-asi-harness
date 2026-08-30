# Architecture

The Hermes AGI/ASI Harness is built on a three-plane architecture with a shared blackboard for coordination.

## Three-Plane Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HERMES INTELLIGENCE OS v11                    │
├─────────────────────────────────────────────────────────────────┤
│  COGNITION PLANE  │  SHARED BLACKBOARD  │  RSI PLANE           │
│                   │                      │                      │
│  World Model      │  State               │  Bottleneck          │
│  Memory           │  Events              │  Hypothesis           │
│  Beliefs          │  Goals               │  Candidates           │
│  Research         │  Plans               │  Benchmarks           │
│  Reasoning        │  Results             │  Holdout              │
│  Planning         │                      │  Promotion            │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### Cognition Plane
Handles perception, reasoning, and planning. Uses LangGraph for stateful agent workflows.

### Shared Blackboard
Central coordination layer. All planes read/write state, events, goals, and results.

### RSI Plane (Recursive Self-Improvement)
Manages benchmarking, hypothesis generation, and capability promotion.

## Plugin System

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Plugin A    │    │  Plugin B    │    │  Plugin C    │
│  (safety)    │    │  (reasoning) │    │  (perception)│
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼───────┐
                    │   Harness    │
                    │   Registry   │
                    └──────────────┘
```

## High Availability

- **Circuit Breaker**: Fails fast when dependencies are unhealthy
- **Failover**: Automatic fallback to backup services
- **Graceful Degradation**: Reduced functionality instead of total failure

## Dynamic Configuration

Configuration reloads in <5s without restart. Uses file watchers and atomic swaps.

## Hermes Agent Integration

- **Profiles**: Load different agent configurations
- **Kanban**: Task board integration
- **Cron**: Scheduled task execution
- **MCP**: Model Context Protocol endpoints

## Data Flow

```
Input → Perception → Blackboard → Reasoning → Planning → Action → Output
                         ↑                                      │
                         └──────────────────────────────────────┘
```
