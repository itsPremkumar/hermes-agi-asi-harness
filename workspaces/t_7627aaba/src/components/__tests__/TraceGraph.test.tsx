/**
 * Tests for TraceGraphView component.
 * @vitest @component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { useStore } from '../../store/StoreProvider';
import TraceGraphView from '../TraceGraphView';
import type { AgentTrace, TraceEvent } from '../../types/trace';

const mockStore = {
  traces: {},
  activeAgentId: null,
  agents: {},
  circuitBreakers: {
    config: { costCapUSD: 0.5, stepBudget: 1000, timeoutSeconds: 30, loopDetectionThreshold: 3 },
    currentCost: 0, stepsConsumed: 0, activeSince: '', tripped: false,
    trippedBreaker: null, trippedReason: undefined,
  },
  sseStatus: 'connected',
  isLoadingAgents: false,
  error: null,
  messages: [],
  chatEvents: [],
  plans: {},
  setActiveAgent: vi.fn(),
  fetchAgents: vi.fn(),
  fetchPlan: vi.fn(),
  fetchTrace: vi.fn(),
  sendChat: vi.fn(),
  setSseStatus: vi.fn(),
  setError: vi.fn(),
  setLoadingAgents: vi.fn(),
  setAgents: vi.fn(),
  updateAgent: vi.fn(),
  setPlan: vi.fn(),
  setTrace: vi.fn(),
  appendMessage: vi.fn(),
  appendChatEvent: vi.fn(),
  setCircuitBreakers: vi.fn(),
  updateCircuitBreakerConfig: vi.fn(),
  updateBreakers: vi.fn(),
};

vi.mock('../../store/StoreProvider', () => ({
  useStore: () => mockStore,
  useStoreContext: () => ({ api: {}, sse: { connect: vi.fn(), disconnect: vi.fn(), subscribe: vi.fn() } }),
}));

const sampleEvents: TraceEvent[] = [
  {
    id: 'evt-1',
    type: 'agent_step',
    agentId: 'agent-1',
    timestamp: new Date().toISOString(),
    runId: 'run-1',
    status: 'planning',
    thought: 'Starting analysis',
  } as any,
  {
    id: 'evt-2',
    type: 'tool_call_started',
    agentId: 'agent-1',
    timestamp: new Date().toISOString(),
    runId: 'run-1',
    toolCallId: 'call-1',
    toolName: 'read_file',
    args: { path: '/test.ts' },
  },
  {
    id: 'evt-3',
    type: 'tool_call_completed',
    agentId: 'agent-1',
    timestamp: new Date().toISOString(),
    runId: 'run-1',
    toolCallId: 'call-1',
    toolName: 'read_file',
    result: 'file content',
    status: 'success',
  },
];

const sampleTrace: AgentTrace = {
  agentId: 'agent-1',
  plan: {
    id: 'root', name: 'Test plan', type: 'goal', status: 'complete',
    children: [], toolCalls: [],
  },
  events: sampleEvents,
  causalEdges: [
    { causeEventId: 'evt-1', effectEventId: 'evt-2', relation: 'triggered-by' },
  ],
};

describe('TraceGraphView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStore.traces = {};
    mockStore.activeAgentId = null;
  });

  it('renders empty state when no active agent', () => {
    render(<TraceGraphView />);
    expect(screen.getByText(/Select an agent to view its causal trace/i)).toBeInTheDocument();
  });

  it('renders trace header when trace exists', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.traces = { 'agent-1': sampleTrace };
    render(<TraceGraphView />);
    expect(screen.getByText('Trace Graph — agent-1')).toBeInTheDocument();
  });

  it('renders causal edges', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.traces = { 'agent-1': sampleTrace };
    render(<TraceGraphView />);
    const edges = screen.getAllByTestId('causal-edge');
    expect(edges).toHaveLength(1);
    expect(screen.getByText('triggered-by')).toBeInTheDocument();
  });

  it('renders event timeline with all events', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.traces = { 'agent-1': sampleTrace };
    render(<TraceGraphView />);
    expect(screen.getByTestId('event-timeline')).toBeInTheDocument();
    const rows = screen.getAllByTestId('event-row');
    expect(rows).toHaveLength(3);
  });

  it('renders export button', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.traces = { 'agent-1': sampleTrace };
    render(<TraceGraphView />);
    expect(screen.getByTestId('export-trace')).toBeInTheDocument();
  });

  it('formats agent_step events in timeline', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.traces = { 'agent-1': sampleTrace };
    render(<TraceGraphView />);
    expect(screen.getByText('agent_step')).toBeInTheDocument();
  });

  it('formats tool_call events in timeline', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.traces = { 'agent-1': sampleTrace };
    render(<TraceGraphView />);
    const toolRows = screen.getAllByText('tool_call_started');
    expect(toolRows.length).toBe(1);
  });

  it('shows empty message when no events', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.traces = {
      'agent-1': { ...sampleTrace, events: [] },
    };
    render(<TraceGraphView />);
    expect(screen.getByText('No trace events recorded.')).toBeInTheDocument();
  });
});
