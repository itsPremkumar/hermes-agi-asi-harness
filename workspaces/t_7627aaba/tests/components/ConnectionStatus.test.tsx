/**
 * Tests for ConnectionStatus component.
 * @vitest @component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useStore } from '../../src/store/StoreProvider';
import { ConnectionStatus } from '../../src/components/ConnectionStatus';

const mockStore = {
  sseStatus: 'connected' as const,
  error: null as string | null,
  fetchAgents: vi.fn(),
};

vi.mock('../../src/store/StoreProvider', () => ({
  useStore: () => mockStore,
  useStoreContext: () => ({ api: {}, sse: { connect: vi.fn(), disconnect: vi.fn(), subscribe: vi.fn() } }),
}));

describe('ConnectionStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStore.sseStatus = 'connected';
    mockStore.error = null;
  });

  it('renders "Connected" when sseStatus is connected', () => {
    render(<ConnectionStatus />);
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('renders "Connecting..." when sseStatus is connecting', () => {
    mockStore.sseStatus = 'connecting';
    render(<ConnectionStatus />);
    expect(screen.getByText('Connecting...')).toBeInTheDocument();
  });

  it('renders "Disconnected" when sseStatus is disconnected', () => {
    mockStore.sseStatus = 'disconnected';
    render(<ConnectionStatus />);
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('renders "Error" state when sseStatus is error', () => {
    mockStore.sseStatus = 'error';
    render(<ConnectionStatus />);
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('shows error message when error is set', () => {
    mockStore.error = 'Connection refused on port 3998';
    render(<ConnectionStatus />);
    expect(screen.getByText(/Error/)).toBeInTheDocument();
  });

  it('calls fetchAgents on mount', () => {
    render(<ConnectionStatus />);
    expect(mockStore.fetchAgents).toHaveBeenCalled();
  });

  it('does not show error message when error is null', () => {
    mockStore.error = null;
    render(<ConnectionStatus />);
    expect(screen.queryByText(/Error/)).not.toBeInTheDocument();
  });
});
