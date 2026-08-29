/**
 * Tests for the Zustand studio store.
 * Covers: state mutations, async fetch flows (plan/trace/agents),
 * trace-event processing, circuit breaker config updates, and chat flow.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useStudioStore, processTraceEvent } from '../src/store/studioStore';
import type { TraceEvent } from '../src/types/trace';

import { AvoStudioApi } from '../src/lib/api';

// A minimal mock API — the real AvoStudioApi is tested separately.
const makeApi = () =>
  ({
    fetchAgents: vi.fn(),
    fetchPlan: vi.fn(),
    fetchTrace: vi.fn(),
    sendChatMessage: vi.fn(),
    updateCircuitBreakers: vi.fn(),
    fetchCircuitBreakers: vi.fn(),
  } as unknown as AvoStudioApi);

// getState/setState via the hook's static API
const get = () => useStudioStore.getState();
const set = (patch: Partial<ReturnType<typeof get>>) =>
  useStudioStore.setState(patch, false);

describe('studioStore', () => {
  beforeEach(() => {
    useStudioStore.setState(
      {
        agents: {},
        activeAgentId: null,
        plans: {},
        traces: {},
        messages: [],
        chatEvents: [],
        sseStatus: 'disconnected',
        isLoadingAgents: false,
        error: null,
        circuitBreakers: {
          config: { costCapUSD: 0.5, stepBudget: 1000, timeoutSeconds: 30, loopDetectionThreshold: 3 },
          currentCost: 0,
          stepsConsumed: 0,
          activeSince: '2026-01-01T00:00:00Z',
          tripped: false,
          trippedBreaker: null,
          trippedReason: undefined,
        },
      },
      true,
    );
  });

  it('setAgents indexes agents by id', () => {
    set({ agents: {} });
    get().setAgents([
      { id: 'a1', name: 'Alpha', status: 'idle', resources: { tokens: 10, cost: 0.01, cpuMs: 5 }, lastSeen: '', runId: 'r1' },
      { id: 'a2', name: 'Beta', status: 'idle', resources: { tokens: 20, cost: 0.02, cpuMs: 8 }, lastSeen: '', runId: 'r1' },
    ]);
    const ids = Object.keys(get().agents);
    expect(ids).toEqual(['a1', 'a2']);
    expect(get().agents['a1']?.name).toBe('Alpha');
  });

  it('updateAgent merges partial props', () => {
    set({ agents: { a1: { id: 'a1', name: 'A', status: 'idle', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r' } } });
    get().updateAgent({ id: 'a1', status: 'executing' });
    expect(get().agents['a1']!.status).toBe('executing');
    expect(get().agents['a1']!.name).toBe('A'); // unchanged
  });

  it('updateCircuitBreakerConfig merges without clobbering other keys', () => {
    get().updateCircuitBreakerConfig({ costCapUSD: 1.0 });
    expect(get().circuitBreakers.config.costCapUSD).toBe(1.0);
    expect(get().circuitBreakers.config.stepBudget).toBe(1000); // preserved
  });

  it('setActiveAgent updates activeAgentId', () => {
    get().setActiveAgent('a1');
    expect(get().activeAgentId).toBe('a1');
    get().setActiveAgent(null);
    expect(get().activeAgentId).toBeNull();
  });

  it('appendMessage and appendChatEvent grow arrays', () => {
    get().appendMessage({ id: 'm1', role: 'user', content: 'hi', timestamp: '' });
    expect(get().messages).toHaveLength(1);
    get().appendChatEvent({ type: 'agent-response', message: 'ack', timestamp: '' });
    expect(get().chatEvents).toHaveLength(1);
  });

  it('fetchAgents sets loading then populates agents', async () => {
    const api = makeApi();
    api.fetchAgents = vi.fn().mockResolvedValue([
      { id: 'a1', name: 'Alpha', status: 'idle', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r' },
    ]);

    await get().fetchAgents(api, 'run-1');
    expect(api.fetchAgents).toHaveBeenCalledWith('run-1');
    expect(get().agents['a1']?.name).toBe('Alpha');
    expect(get().isLoadingAgents).toBe(false);
  });

  it('fetchAgents sets error on failure', async () => {
    const api = makeApi();
    api.fetchAgents = vi.fn().mockRejectedValue(new Error('network down'));

    await get().fetchAgents(api);
    expect(get().error).toBe('network down');
  });

  it('fetchPlan populates plans map', async () => {
    const api = makeApi();
    const plan = { id: 'root', name: 'Goal', type: 'goal' as const, children: [], status: 'pending' as const, toolCalls: [] };
    api.fetchPlan = vi.fn().mockResolvedValue(plan);

    await get().fetchPlan(api, 'a1');
    expect(get().plans['a1']).toEqual(plan);
  });

  it('fetchTrace populates traces map', async () => {
    const api = makeApi();
    const trace = {
      agentId: 'a1',
      plan: { id: 'root', name: 'G', type: 'goal' as const, children: [], status: 'pending' as const, toolCalls: [] },
      events: [],
      causalEdges: [],
    };
    api.fetchTrace = vi.fn().mockResolvedValue(trace);

    await get().fetchTrace(api, 'a1');
    expect(get().traces['a1']?.agentId).toBe('a1');
  });

  it('sendChat appends user message then assistant reply', async () => {
    const api = makeApi();
    api.sendChatMessage = vi.fn().mockResolvedValue({ ok: true, reply: 'got it' });

    await get().sendChat(api, { role: 'user', content: 'run', timestamp: 'now' });
    expect(get().messages).toHaveLength(2);
    expect(get().messages[0]!.role).toBe('user');
    expect(get().messages[1]!.role).toBe('assistant');
    expect(get().messages[1]!.content).toBe('got it');
  });

  it('sendChat appends error message on failure', async () => {
    const api = makeApi();
    api.sendChatMessage = vi.fn().mockRejectedValue(new Error('timeout'));

    await get().sendChat(api, { role: 'user', content: 'run', timestamp: 'now' });
    const system = get().messages.find((m) => m.role === 'system');
    expect(system?.content).toContain('Error: timeout');
  });
});

describe('processTraceEvent', () => {
  beforeEach(() => {
    useStudioStore.setState(
      {
        agents: { a1: { id: 'a1', name: 'A', status: 'idle', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r' } },
        traces: { a1: { agentId: 'a1', plan: { id: 'root', name: 'G', type: 'goal' as const, children: [], status: 'pending' as const, toolCalls: [] }, events: [], causalEdges: [] } },
        activeAgentId: 'a1',
        plans: {},
        messages: [],
        chatEvents: [],
        sseStatus: 'disconnected', isLoadingAgents: false, error: null,
        circuitBreakers: { config: { costCapUSD: 0.5, stepBudget: 1000, timeoutSeconds: 30, loopDetectionThreshold: 3 }, currentCost: 0, stepsConsumed: 0, activeSince: '', tripped: false, trippedBreaker: null, trippedReason: undefined },
      },
      true,
    );
  });

  it('agent_step updates agent status', () => {
    const evt: TraceEvent = { id: 'e1', type: 'agent_step', agentId: 'a1', timestamp: '', runId: 'r', status: 'planning' };
    processTraceEvent(useStudioStore, evt);
    expect(get().agents['a1']!.status).toBe('planning');
  });

  it('tool_call_started sets agent to executing', () => {
    const evt: TraceEvent = { id: 'e2', type: 'tool_call_started', agentId: 'a1', timestamp: '', runId: 'r', toolCallId: 'tc1', toolName: 'search', args: {} };
    processTraceEvent(useStudioStore, evt);
    expect(get().agents['a1']!.status).toBe('executing');
  });

  it('loop_detected marks agent as failed', () => {
    const evt: TraceEvent = { id: 'e3', type: 'loop_detected', agentId: 'a1', timestamp: '', runId: 'r', repeatCount: 3, toolName: 'search', argsHash: 'abc' };
    processTraceEvent(useStudioStore, evt);
    expect(get().agents['a1']!.status).toBe('failed');
  });

  it('appends events to the trace timeline', () => {
    const evt: TraceEvent = { id: 'e4', type: 'agent_step', agentId: 'a1', timestamp: '', runId: 'r', status: 'done' };
    processTraceEvent(useStudioStore, evt);
    expect(get().traces['a1']!.events).toHaveLength(1);
    expect(get().traces['a1']!.events[0]!.id).toBe('e4');
  });

  it('does nothing when trace does not exist for agent', () => {
    const evt: TraceEvent = { id: 'e5', type: 'agent_step', agentId: 'a2', timestamp: '', runId: 'r', status: 'done' };
    processTraceEvent(useStudioStore, evt);
    // should not throw and should not create a trace entry
    expect(get().traces['a2']).toBeUndefined();
  });
});
