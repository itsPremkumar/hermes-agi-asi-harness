/**
 * Tests for PlanVisualization component.
 * @vitest @component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { useStore } from '../../store/StoreProvider';
import PlanVisualization from '../PlanVisualization';
import type { AgentPlanNode } from '../../types/trace';

const mockStore = {
  agents: {},
  activeAgentId: null,
  setActiveAgent: vi.fn(),
  isLoadingAgents: false,
  error: null,
  fetchAgents: vi.fn(),
  fetchPlan: vi.fn(),
  fetchTrace: vi.fn(),
  plans: {},
  traces: {},
  messages: [],
  chatEvents: [],
  circuitBreakers: {
    config: { costCapUSD: 0.5, stepBudget: 1000, timeoutSeconds: 30, loopDetectionThreshold: 3 },
    currentCost: 0,
    stepsConsumed: 0,
    activeSince: '',
    tripped: false,
    trippedBreaker: null,
    trippedReason: undefined,
  },
  updateBreakers: vi.fn(),
  updateCircuitBreakerConfig: vi.fn(),
  setCircuitBreakers: vi.fn(),
  setAgents: vi.fn(),
  setSseStatus: vi.fn(),
  setError: vi.fn(),
  setPlan: vi.fn(),
  setTrace: vi.fn(),
  appendMessage: vi.fn(),
  appendChatEvent: vi.fn(),
  sseStatus: 'connected',
};

vi.mock('../../store/StoreProvider', () => ({
  useStore: () => mockStore,
  useStoreContext: () => ({ api: {}, sse: { connect: vi.fn(), disconnect: vi.fn(), subscribe: vi.fn() } }),
}));

const samplePlan: AgentPlanNode = {
  id: 'plan-root',
  name: 'Analyze codebase',
  type: 'goal',
  status: 'pending',
  children: [
    {
      id: 'plan-1',
      name: 'Read source files',
      type: 'task',
      status: 'complete',
      children: [],
      toolCalls: [
        {
          id: 'call-1',
          name: 'read_file',
          args: { path: '/src/index.ts' },
          result: 'file content here',
          startedAt: new Date().toISOString(),
          completedAt: new Date().toISOString(),
          status: 'complete',
        },
      ],
    },
    {
      id: 'plan-2',
      name: 'Summarize findings',
      type: 'task',
      status: 'running',
      children: [],
      toolCalls: [],
    },
  ],
};

describe('PlanVisualization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStore.plans = {};
    mockStore.activeAgentId = null;
  });

  it('renders empty state when no active agent', () => {
    render(<PlanVisualization />);
    expect(screen.getByText(/Select an agent to view its plan/i)).toBeInTheDocument();
  });

  it('renders plan tree when plan exists', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.plans = { 'agent-1': samplePlan };
    render(<PlanVisualization />);
    expect(screen.getByText('Plan')).toBeInTheDocument();
    expect(screen.getByText('Analyze codebase')).toBeInTheDocument();
    expect(screen.getByText('(goal)')).toBeInTheDocument();
  });

  it('renders child nodes in the tree', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.plans = { 'agent-1': samplePlan };
    render(<PlanVisualization />);
    expect(screen.getByText('Read source files')).toBeInTheDocument();
    expect(screen.getByText('Summarize findings')).toBeInTheDocument();
  });

  it('shows tool calls when details are toggled', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.plans = { 'agent-1': samplePlan };
    render(<PlanVisualization />);
    const detailsButton = screen.getByTestId('details-plan-1');
    fireEvent.click(detailsButton);
    expect(screen.getByTestId('tool-call-details')).toBeInTheDocument();
    expect(screen.getByText('read_file')).toBeInTheDocument();
  });

  it('renders status badges for each node', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.plans = { 'agent-1': samplePlan };
    render(<PlanVisualization />);
    const statusElements = screen.getAllByTestId('node-status');
    expect(statusElements.length).toBeGreaterThanOrEqual(1);
  });

  it('toggles tree expansion on click', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.plans = { 'agent-1': samplePlan };
    render(<PlanVisualization />);
    const toggle = screen.getByTestId('toggle-plan-root');
    fireEvent.click(toggle);
    // After collapsing, children should not be visible
    const cards = screen.queryAllByText('Read source files');
    expect(cards.length).toBe(0);
  });
});
