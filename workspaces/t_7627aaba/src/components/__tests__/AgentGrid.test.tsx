/**
 * Tests for AgentGridView component.
 * @vitest @component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useStore } from '../../store/StoreProvider';
import AgentGridView from '../AgentGridView';

// Mock the store context
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

const renderWithRouter = (component: React.ReactNode) =>
  render(<MemoryRouter>{component}</MemoryRouter>);

describe('AgentGridView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStore.agents = {};
    mockStore.isLoadingAgents = false;
    mockStore.error = null;
  });

  it('renders "Running Agents" heading', () => {
    renderWithRouter(<AgentGridView />);
    expect(screen.getByText('Running Agents')).toBeInTheDocument();
  });

  it('shows loading state when isLoadingAgents is true', () => {
    mockStore.agents = {};
    mockStore.isLoadingAgents = true;
    renderWithRouter(<AgentGridView />);
    expect(screen.getByText('Loading agents...')).toBeInTheDocument();
  });

  it('shows empty state when no agents', () => {
    renderWithRouter(<AgentGridView />);
    expect(
      screen.getByText('No agents running. Start an AVO session to see agents here.'),
    ).toBeInTheDocument();
  });

  it('renders agent cards for each agent', () => {
    mockStore.agents = {
      agent-1: {
        id: 'agent-1',
        name: 'PlannerAgent',
        status: 'planning',
        resources: { tokens: 1500, cost: 0.15, cpuMs: 200 },
        lastSeen: '',
        runId: 'run-1',
      },
      agent-2: {
        id: 'agent-2',
        name: 'ExecutorAgent',
        status: 'executing',
        resources: { tokens: 3200, cost: 0.32, cpuMs: 500 },
        lastSeen: '',
        runId: 'run-1',
      },
    };
    renderWithRouter(<AgentGridView />);
    expect(screen.getAllByTestId('agent-card')).toHaveLength(2);
    expect(screen.getByText('PlannerAgent')).toBeInTheDocument();
    expect(screen.getByText('ExecutorAgent')).toBeInTheDocument();
  });

  it('displays resource usage on agent cards', () => {
    mockStore.agents = {
      'agent-1': {
        id: 'agent-1',
        name: 'TestAgent',
        status: 'done',
        resources: { tokens: 1500, cost: 0.15, cpuMs: 200 },
        lastSeen: '',
        runId: 'run-1',
      },
    };
    renderWithRouter(<AgentGridView />);
    expect(screen.getByText('1,500')).toBeInTheDocument();
    expect(screen.getByText('$0.150')).toBeInTheDocument();
    expect(screen.getByText('200ms')).toBeInTheDocument();
  });

  it('renders status badge for each agent', () => {
    mockStore.agents = {
      'agent-1': {
        id: 'agent-1',
        name: 'TestAgent',
        status: 'executing',
        resources: { tokens: 0, cost: 0, cpuMs: 0 },
        lastSeen: '',
        runId: 'run-1',
      },
    };
    renderWithRouter(<AgentGridView />);
    expect(screen.getByTestId('status-badge')).toHaveAttribute('data-status', 'executing');
  });

  it('calls setActiveAgent and fetch functions on card click', () => {
    mockStore.agents = {
      'agent-1': {
        id: 'agent-1',
        name: 'TestAgent',
        status: 'done',
        resources: { tokens: 0, cost: 0, cpuMs: 0 },
        lastSeen: '',
        runId: 'run-1',
      },
    };
    renderWithRouter(<AgentGridView />);
    const card = screen.getByTestId('agent-card');
    card.click();
    expect(mockStore.setActiveAgent).toHaveBeenCalledWith('agent-1');
  });
});
