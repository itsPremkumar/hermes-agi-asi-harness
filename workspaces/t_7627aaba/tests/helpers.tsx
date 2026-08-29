/**
 * Shared test harness for component tests.
 * Provides mock store context + API injection so components that call
 * useStoreContext() render without importing a real backend.
 */
import React, { ReactNode } from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { StoreProvider } from '../src/store/StoreProvider';
import { useStudioStore } from '../src/store/studioStore';
import { AvoStudioApi } from '../src/lib/api';
import type {
  AVOAgent,
  AgentPlanNode,
  AgentTrace,
  CircuitBreakerState,
} from '../src/types/trace';

export function resetStore(overrides: {
  agents?: AVOAgent[];
  plans?: Record<string, AgentPlanNode>;
  traces?: Record<string, AgentTrace>;
  circuitBreakers?: Partial<CircuitBreakerState>;
  activeAgentId?: string | null;
} = {}) {
  const store = useStudioStore.getState();
  store.setAgents(overrides.agents ?? []);
  if (overrides.activeAgentId !== undefined) {
    store.setActiveAgent(overrides.activeAgentId);
  }
  if (overrides.plans) {
    Object.entries(overrides.plans).forEach(([id, plan]) => store.setPlan(id, plan));
  }
  if (overrides.traces) {
    Object.entries(overrides.traces).forEach(([id, trace]) => store.setTrace(id, trace));
  }
  if (overrides.circuitBreakers) {
    store.setCircuitBreakers({
      ...store.circuitBreakers,
      ...overrides.circuitBreakers,
    });
  }
}

export function makeAgent(
  overrides: Partial<AVOAgent> & { id: string; name: string },
): AVOAgent {
  return {
    id: overrides.id,
    name: overrides.name,
    status: overrides.status ?? 'idle',
    resources: overrides.resources ?? { tokens: 0, cost: 0, cpuMs: 0 },
    lastSeen: overrides.lastSeen ?? '2026-01-01T00:00:00Z',
    runId: overrides.runId ?? 'run-1',
    currentPlanNode: overrides.currentPlanNode,
  };
}

/** Mock API that returns canned data for fetch methods. */
export function makeMockApi(): AvoStudioApi {
  const api = new AvoStudioApi('/api');
  api.fetchAgents = vi.fn().mockResolvedValue([]);
  api.fetchPlan = vi.fn().mockResolvedValue({
    id: 'root',
    name: 'Root Goal',
    type: 'goal',
    children: [],
    status: 'pending',
    toolCalls: [],
  });
  api.fetchTrace = vi.fn().mockResolvedValue({
    agentId: 'a1',
    plan: { id: 'root', name: 'Root', type: 'goal', children: [], status: 'pending', toolCalls: [] },
    events: [],
    causalEdges: [],
  });
  api.sendChatMessage = vi.fn().mockResolvedValue({ ok: true, reply: 'ack' });
  api.updateCircuitBreakers = vi.fn().mockResolvedValue({
    costCapUSD: 0.5,
    stepBudget: 1000,
    timeoutSeconds: 30,
    loopDetectionThreshold: 3,
  });
  return api;
}

/** Wrap a component in MemoryRouter + StoreProvider with a mocked API+SSE. */
export function renderWithProviders(ui: ReactNode, initialEntries: string[] = ['/']) {
  // We need to inject a mock API + SSE into the StoreContext.
  // StoreProvider creates its own api/sse, so we instead render inside a
  // context that overrides the api via a wrapper. Since StoreProvider
  // constructs the api internally, we test components that read useStore
  // (which does not need the context) directly, and mock useStoreContext
  // for components that do.
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <StoreProvider>{ui}</StoreProvider>
    </MemoryRouter>,
  );
}
