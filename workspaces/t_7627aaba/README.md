# AVOStudio — Orchestration GUI

Real-time web interface for orchestrating Hermes AVO multi-agent systems.

## Stack
- React 18 + TypeScript + Vite
- Tailwind CSS (AVO theme)
- Zustand (state) + React Router (routing)
- SSE for real-time events via `/stream`
- Vitest + Testing Library for component tests

## Features
1. **Agent Grid View** — Live canvas of all running agents with status,
   tokens, cost, CPU. Click to inspect plan + trace.
2. **Plan Visualization** — Collapsible HTN tree, color-coded by status.
   Click nodes to expand tool calls + observations.
3. **Trace Graph** — Causal edges between events ("WHY" reconstruction).
   Exports to MCP trace server as JSON.
4. **Chat Interface** — Send goals to agents (`/execute`, `/status`,
   `/cancel`, `/escalate`).
5. **Circuit Breakers** — Cost cap, step budget, call timeout, loop detection.
   All configurable via the dashboard.

## Routing
| Route              | Component                  |
|--------------------|----------------------------|
| `/`                | AgentGridView              |
| `/agent/:agentId`  | AgentDetailView            |
| `/traces`          | TraceGraphView             |
| `/breakers`        | CircuitBreakersDashboard   |

## API
REST: `/api/agents`, `/api/plans/:id`, `/api/traces/:id`, `/api/chat`, `/api/circuit-breakers`
SSE: `/stream` — emits `TraceEvent` payloads (agent_step, tool_call_started,
tool_call_completed, checkpoint_created, loop_detected).

## Development
```bash
pnpm install          # or npm install
pnpm dev              # vite dev server on :3999
pnpm test             # vitest run
pnpm build            # tsc + vite build
```

## Trace Event Schema
See `src/types/trace.ts` for the canonical schema, compatible with
AgentWatch's SQLite storage contract and the MCP trace server.
