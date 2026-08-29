/**
 * Tests for ChatInterface component.
 * @vitest @component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useStore } from '../../store/StoreProvider';
import ChatInterface from '../ChatInterface';

const mockStore = {
  messages: [] as any[],
  chatEvents: [] as any[],
  activeAgentId: null,
  agents: {} as Record<string, any>,
  circuitBreakers: {
    config: { costCapUSD: 0.5, stepBudget: 1000, timeoutSeconds: 30, loopDetectionThreshold: 3 },
    currentCost: 0, stepsConsumed: 0, activeSince: '', tripped: false,
    trippedBreaker: null, trippedReason: undefined,
  },
  sseStatus: 'connected',
  isLoadingAgents: false,
  error: null,
  plans: {},
  traces: {},
  setActiveAgent: vi.fn(),
  fetchAgents: vi.fn(),
  fetchPlan: vi.fn(),
  fetchTrace: vi.fn(),
  sendChat: vi.fn().mockResolvedValue(undefined),
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

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStore.messages = [];
    mockStore.chatEvents = [];
    mockStore.activeAgentId = null;
    mockStore.agents = {};
  });

  it('renders the control channel header', () => {
    render(<ChatInterface />);
    expect(screen.getByText('Control Channel')).toBeInTheDocument();
  });

  it('renders the chat input', () => {
    render(<ChatInterface />);
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
  });

  it('renders the send button', () => {
    render(<ChatInterface />);
    expect(screen.getByTestId('send-button')).toBeInTheDocument();
  });

  it('renders quick action buttons', () => {
    render(<ChatInterface />);
    expect(screen.getByTestId('quick-status')).toBeInTheDocument();
    expect(screen.getByTestId('quick-cancel')).toBeInTheDocument();
    expect(screen.getByTestId('quick-escalate')).toBeInTheDocument();
  });

  it('renders empty chat messages area initially', () => {
    render(<ChatInterface />);
    const messagesArea = screen.getByTestId('chat-messages');
    expect(messagesArea.querySelectorAll('[data-testid="message-row"]')).toHaveLength(0);
  });

  it('renders existing messages from store', () => {
    mockStore.messages = [
      {
        id: 'msg-1',
        role: 'user',
        content: 'Hello agent',
        timestamp: new Date().toISOString(),
      },
    ];
    render(<ChatInterface />);
    expect(screen.getByTestId('message-row')).toBeInTheDocument();
    expect(screen.getByText('Hello agent')).toBeInTheDocument();
  });

  it('shows "all agents" as default target when no active agent', () => {
    render(<ChatInterface />);
    expect(screen.getByText('Target: all agents')).toBeInTheDocument();
  });

  it('shows agent name as target when active agent is set', () => {
    mockStore.activeAgentId = 'agent-1';
    mockStore.agents = {
      'agent-1': { id: 'agent-1', name: 'PlannerBot' },
    };
    render(<ChatInterface />);
    expect(screen.getByText('Target: PlannerBot')).toBeInTheDocument();
  });

  it('calls sendChat when form is submitted with text', async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);
    const input = screen.getByTestId('chat-input');
    await user.type(input, 'Analyze the codebase');
    fireEvent.submit(screen.getByRole('form'));
    await waitFor(() => {
      expect(mockStore.sendChat).toHaveBeenCalled();
    });
  });

  it('does not send when input is empty', async () => {
    render(<ChatInterface />);
    fireEvent.submit(screen.getByRole('form'));
    expect(mockStore.sendChat).not.toHaveBeenCalled();
  });

  it('parses slash commands correctly', async () => {
    const user = userEvent.setup();
    render(<ChatInterface />);
    const input = screen.getByTestId('chat-input');
    await user.type(input, '/status');
    fireEvent.submit(screen.getByRole('form'));
    await waitFor(() => {
      expect(mockStore.sendChat).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({ command: 'status' }),
      );
    });
  });
});
