/**
 * Tests for the Zustand studio store + processTraceEvent.
 * @vitest @unit
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useStudioStore, processTraceEvent } from '../src/store/studioStore';
import type { TraceEvent, AVOAgent } from '../src/types/trace';

describe('Studio Store', () => {
  beforeEach(() => {
    useStudioStore.setState({
      agents: {},
      activeAgentId: null,
      plans: {},
      traces: {},
      messages: [],
      chatEvents: [],
      circuitBreakers: {
        config: { costCapUSD: 0.5, stepBudget: 1000, timeoutSeconds: 30, loopDetectionThreshold: 3 },
        currentCost: 0,
        stepsConsumed: 0,
        activeSince: new Date().toISOString(),
        tripped: false,
        trippedBreaker: null,
        trippedReason: undefined,
      },
      sseStatus: 'disconnected',
      isLoadingAgents: false,
      error: null,
    });
  });

  it('starts with empty state', () => {
    const state = useStudioStore.getState();
    expect(Object.keys(state.agents)).toHaveLength(0);
    expect(state.error).toBeNull();
    expect(state.sseStatus).toBe('disconnected');
  });

  it('setAgents replaces the agents map', () => {
    const agents: AVOAgent[] = [
      { id: 'a1', name: 'Bot', status: 'done', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r1' },
    ];
    useStudioStore.getState().setAgents(agents);
    expect(Object.keys(useStudioStore.getState().agents)).toHaveLength(1);
    expect(useStudioStore.getState().agents.a1.name).toBe('Bot');
  });

  it('updateAgent merges partial data', () => {
    useStudioStore.getState().setAgents([
      { id: 'a1', name: 'Bot', status: 'done', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r1' },
    ]);
    useStudioStore.getState().updateAgent({ id: 'a1', status: 'executing' });
    expect(useStudioStore.getState().agents.a1.status).toBe('executing');
  });

  it('setActiveAgent sets active agent', () => {
    useStudioStore.getState().setActiveAgent('a1');
    expect(useStudioStore.getState().activeAgentId).toBe('a1');
  });

  it('appendMessage adds a message', () => {
    useStudioStore.getState().appendMessage({
      id: 'm1',
      role: 'user',
      content: 'hello',
      timestamp: new Date().toISOString(),
    });
    expect(useStudioStore.getState().messages).toHaveLength(1);
  });

  it('updateCircuitBreakerConfig merges config', () => {
    useStudioStore.getState().updateCircuitBreakerConfig({ costCapUSD: 1.0 });
    expect(useStudioStore.getState().circuitBreakers.config.costCapUSD).toBe(1.0);
    expect(useStudioStore.getState().circuitBreakers.config.stepBudget).toBe(1000);
  });

  it('processTraceEvent updates agent status on agent_step', () => {
    const event: TraceEvent = {
      id: 'e1',
      type: 'agent_step',
      agentId: 'a1',
      timestamp: new Date().toISOString(),
      runId: 'r1',
      status: 'observing',
      thought: 'Done planning',
    } as any;
    processTraceEvent(useStudioStore, event);
    expect(useStudioStore.getState().agents.a1?.status).toBe('observing');
  });

  it('processTraceEvent adds event to trace', () => {
    useStudioStore.getState().setTrace('a1', {
      agentId: 'a1',
      plan: { id: 'p', name: 'p', type: 'goal', status: 'pending', children: [], toolCalls: [] },
      events: [],
      causalEdges: [],
    });
    const event: TraceEvent = {
      id: 'e1',
      type: 'checkpoint_created',
      agentId: 'a1',
      timestamp: new Date().toISOString(),
      runId: 'r1',
      checkpointId: 'cp-1',
      stateSummary: 'at checkpoint',
    };
    processTraceEvent(useStudioStore, event);
    expect(useStudioStore.getState().traces.a1.events).toHaveLength(1);
  });

  it('processTraceEvent marks agent failed on loop_detected', () => {
    useStudioStore.getState().setAgents([
      { id: 'a1', name: 'Bot', status: 'planning', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r1' },
    ]);
    const event: TraceEvent = {
      id: 'e1',
      type: 'loop_detected',
      agentId: 'a1',
      timestamp: new Date().toISOString(),
      runId: 'r1',
      repeatCount: 3,
      toolName: 'read_file',
      argsHash: 'abc',
    };
    processTraceEvent(useStudioStore, event);
    expect(useStudioStore.getState().agents.a1?.status).toBe('failed');
  });

  it('processTraceEvent sets executing on tool_call_started', () => {
    useStudioStore.getState().setAgents([
      { id: 'a1', name: 'Bot', status: 'planning', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r1' },
    ]);
    const event: TraceEvent = {
      id: 'e1',
      type: 'tool_call_started',
      agentId: 'a1',
      timestamp: new Date().toISOString(),
      runId: 'r1',
      toolCallId: 'tc-1',
      toolName: 'grep',
      args: { pattern: 'test' },
    };
    processTraceEvent(useStudioStore, event);
    expect(useStudioStore.getState().agents.a1?.status).toBe('executing');
  });
});
