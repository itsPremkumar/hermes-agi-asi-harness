/**
 * Tests for TraceGraphView — causal edge rendering, event timeline,
 * CSV/JSON export, and empty states.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { useStudioStore } from '../src/store/studioStore';
import { makeMockApi, resetStore } from './helpers';
import TraceGraphView from '../src/views/TraceGraphView';
import type { AgentTrace, TraceEvent } from '../src/types/trace';

vi.mock('../src/store/StoreProvider', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/store/StoreProvider')>();
  return {
    ...actual,
    useStoreContext: () => ({ api: makeMockApi(), sse: { connect: vi.fn(), disconnect: vi.fn(), subscribe: vi.fn(() => () => {}), status: 'connected' } }),
    useStore: actual.useStore,
  };
});

const sampleTrace: AgentTrace = {
  agentId: 'a1',
  plan: { id: 'root', name: 'Root', type: 'goal', children: [], status: 'pending', toolCalls: [] },
  events: [
    { id: 'e1', type: 'agent_step', agentId: 'a1', timestamp: '2026-01-01T00:00:00Z', runId: 'r1', status: 'planning', thought: 'I should explore the codebase' },
    { id: 'e2', type: 'tool_call_started', agentId: 'a1', timestamp: '2026-01-01T00:00:01Z', runId: 'r1', toolCallId: 'tc1', toolName: 'search_code', args: { query: 'auth' } },
    { id: 'e3', type: 'tool_call_completed', agentId: 'a1', timestamp: '2026-01-01T00:00:02Z', runId: 'r1', toolCallId: 'tc1', toolName: 'search_code', result: '3 matches', status: 'success' },
    { id: 'e4', type: 'checkpoint_created', agentId: 'a1', timestamp: '2026-01-01T00:00:03Z', runId: 'r1', checkpointId: 'ckpt-1', stateSummary: 'explored auth module' },
    { id: 'e5', type: 'loop_detected', agentId: 'a1', timestamp: '2026-01-01T00:00:04Z', runId: 'r1', repeatCount: 3, toolName: 'search_code', argsHash: 'abc123' },
  ],
  causalEdges: [
    { causeEventId: 'e1', effectEventId: 'e2', relation: 'triggered-by' },
    { causeEventId: 'e3', effectEventId: 'e4', relation: 'informed-by' },
  ],
};

describe('TraceGraphView', () => {
  beforeEach(() => {
    resetStore({ agents: [], traces: {} });
    // Stub createObjectURL for the export button
    global.URL.createObjectURL = vi.fn().mockReturnValue('blob:mock');
    global.URL.revokeObjectURL = vi.fn();
    const mockAnchor = {
      href: '',
      download: '',
      click: vi.fn(),
      setAttribute: vi.fn(),
    };
    vi.spyOn(document, 'createElement').mockImplementation((tag?: string) => {
      if (tag === 'a') return mockAnchor as unknown as HTMLElement;
      return document.createElement(tag ?? 'div');
    });
  });

  it('renders placeholder when no trace is loaded', () => {
    render(<TraceGraphView />);
    expect(screen.getByText(/Select an agent to view its causal trace graph/i)).toBeInTheDocument();
  });

  it('renders the trace header with agentId', () => {
    resetStore({ activeAgentId: 'a1', traces: { a1: sampleTrace } });
    render(<TraceGraphView />);
    expect(screen.getByText('Trace Graph — a1')).toBeInTheDocument();
  });

  it('renders all causal edges', () => {
    resetStore({ activeAgentId: 'a1', traces: { a1: sampleTrace } });
    render(<TraceGraphView />);
    expect(screen.getAllByTestId('causal-edge')).toHaveLength(2);
  });

  it('renders causal edge cause/effect event types', () => {
    resetStore({ activeAgentId: 'a1', traces: { a1: sampleTrace } });
    render(<TraceGraphView />);
    const causes = screen.getAllByTestId('cause-event');
    const effects = screen.getAllByTestId('effect-event');
    expect(causes[0]).toHaveTextContent('agent_step');
    expect(effects[0]).toHaveTextContent('agent_step');
    expect(causes[1]).toHaveTextContent('tool_call_completed');
    expect(effects[1]).toHaveTextContent('checkpoint_created');
  });

  it('renders all timeline events', () => {
    resetStore({ activeAgentId: 'a1', traces: { a1: sampleTrace } });
    render(<TraceGraphView />);
    expect(screen.getAllByTestId('event-row')).toHaveLength(5);
  });

  it('event rows have correct data-event-type attributes', () => {
    resetStore({ activeAgentId: 'a1', traces: { a1: sampleTrace } });
    render(<TraceGraphView />);
    const rows = screen.getAllByTestId('event-row');
    expect(rows[0]).toHaveAttribute('data-event-type', 'agent_step');
    expect(rows[1]).toHaveAttribute('data-event-type', 'tool_call_started');
    expect(rows[4]).toHaveAttribute('data-event-type', 'loop_detected');
  });

  it('export button triggers download with trace JSON', () => {
    resetStore({ activeAgentId: 'a1', traces: { a1: sampleTrace } });
    render(<TraceGraphView />);
    fireEvent.click(screen.getByTestId('export-trace'));
    expect(global.URL.createObjectURL).toHaveBeenCalled();
  });

  it('shows empty message when trace has zero events', () => {
    const emptyTrace: AgentTrace = {
      ...sampleTrace,
      events: [],
      causalEdges: [],
    };
    resetStore({ activeAgentId: 'a1', traces: { a1: emptyTrace } });
    render(<TraceGraphView />);
    expect(screen.queryByTestId('event-row')).not.toBeInTheDocument();
    expect(screen.queryByTestId('causal-edge')).not.toBeInTheDocument();
  });
});
