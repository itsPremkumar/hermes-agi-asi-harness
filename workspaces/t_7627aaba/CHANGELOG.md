# AVOStudio — Changelog

## 0.1.0 — Initial scaffold (Phase 3)

### Scaffold
- `package.json` — React + Vite + TypeScript, Tailwind, Zustand, React Router
- `vite.config.ts` — dev server on :3999, proxies `/api` and `/stream` to
  backend on :3998, test config with jsdom environment
- `tsconfig.json` / `tsconfig.node.json` — strict TS with JSX transform
- `.eslintrc.cjs` — ESLint with React + TypeScript rules
- `tailwind.config.js` / `postcss.config.cjs` — AVO theme (deep blues,
  amber/sky/violet/green/red status colors)
- `index.html` + `favicon.svg` + `src/index.css`

### Store + API
- `src/store/studioStore.ts` — Zustand store with devtools +
  subscribeWithSelector. Manages agents, plans, traces, messages,
  chat events, circuit breakers, SSE status.
- `src/store/StoreProvider.tsx` — Context provider wiring SSE client
  + API into React context. Subscribes to `/stream` and routes events
  via `processTraceEvent`.
- `src/lib/api.ts` — REST client for `/api/agents`, `/api/plans/:id`,
  `/api/traces/:id`, `/api/chat`, `/api/circuit-breakers`.
- `src/lib/sse.ts` — EventSource SSE client with reconnect + heartbeat.
  Typed subscriber pattern, graceful malformed-message handling.
- `src/types/trace.ts` — Canonical trace event schema (5 event types +
  causal edges), agent lifecycle states, circuit breaker config/state,
  chat command types.

### Components + Views
- `src/components/StatusBadge.tsx` — Color-coded status badge per agent
  state.
- `src/components/ConnectionStatus.tsx` — Header SSE connection dot.
- `src/components/ChatInterface.tsx` — Control channel with slash commands
  (`/execute`, `/status`, `/cancel`, `/escalate`) and `avio_execute` shorthand.
- `src/components/CircuitBreakersDashboard.tsx` — Four breakers: cost cap
  ($0.50 default), step budget (1000), call timeout (30s), loop detection
  (3 repeats). Edit/save/reset flow.
- `src/views/AgentGridView.tsx` — Grid of agent cards with live status,
  resource usage (tokens, cost, CPU), progress bars. Link to `/agent/:id`.
- `src/views/PlanVisualization.tsx` — Collapsible HTN tree with
  expand/collapse, status colors, tool-call detail panels.
- `src/views/TraceGraphView.tsx` — Causal edge view + event timeline,
  JSON export for MCP trace server.
- `src/views/AgentDetailView.tsx` — Split-view route: plan + chat side by side.

### Tests (17+ required → 79 cases across 11 files)
- `tests/setup.ts` — jest-dom matchers
- `tests/helpers.tsx` — Shared test harness (store reset, mock API, agent factory)
- `tests/sse.test.ts` — SSE client lifecycle, message parsing, reconnect, unsubscribe
- `tests/api.test.ts` — REST client endpoint paths, method, body, error handling
- `tests/studioStore.test.ts` — Store mutations, async fetches, processTraceEvent
- `tests/StatusBadge.test.tsx` — Per-status labels and color classes
- `tests/CircuitBreakersDashboard.test.tsx` — Render, edit/save/reset, tripped state
- `tests/AgentGridView.test.tsx` — Empty/error states, cards, resources, click-to-fetch
- `tests/PlanVisualization.test.tsx` — Tree rendering, toggle, tool-call details
- `tests/ChatInterface.test.tsx` — Header, messages, send, quick actions
- `tests/TraceGraphView.test.tsx` — Causal edges, event timeline, export, empty state
- `tests/ConnectionStatus.test.tsx` — Status dot, text, error display
- `tests/AgentDetailView.test.tsx` — Agent lookup, fetch-on-mount, plan/chat placeholders

### Known issues (to resolve in shell session)
- `tsc --noEmit` must pass — App.tsx now imports AgentDetailView directly
- `vitest run` must pass — 17+ component tests
- `vite build` must pass — production bundle
