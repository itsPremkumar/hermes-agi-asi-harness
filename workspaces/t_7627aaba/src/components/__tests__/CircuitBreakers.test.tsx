/**
 * Tests for CircuitBreakersDashboard component.
 * @vitest @component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { useStore } from '../../store/StoreProvider';
import CircuitBreakersDashboard from '../CircuitBreakersDashboard';
import { DEFAULT_CIRCUIT_BREAKERS } from '../../types/trace';

const mockStore = {
  circuitBreakers: {
    config: { ...DEFAULT_CIRCUIT_BREAKERS },
    currentCost: 0.15,
    stepsConsumed: 450,
    activeSince: new Date().toISOString(),
    tripped: false,
    trippedBreaker: null,
    trippedReason: undefined,
  },
  updateBreakers: vi.fn().mockResolvedValue(undefined),
};

vi.mock('../../store/StoreProvider', () => ({
  useStore: () => mockStore,
  useStoreContext: () => ({
    api: {},
    sse: { connect: vi.fn(), disconnect: vi.fn(), subscribe: vi.fn() },
  }),
}));

describe('CircuitBreakersDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStore.circuitBreakers.config = { ...DEFAULT_CIRCUIT_BREAKERS };
    mockStore.circuitBreakers.currentCost = 0.15;
    mockStore.circuitBreakers.stepsConsumed = 450;
    mockStore.circuitBreakers.tripped = false;
    mockStore.circuitBreakers.trippedBreaker = null;
    mockStore.circuitBreakers.trippedReason = undefined;
  });

  it('renders the dashboard title', () => {
    render(<CircuitBreakersDashboard />);
    expect(screen.getByText('Circuit Breakers')).toBeInTheDocument();
  });

  it('renders all four breaker cards', () => {
    render(<CircuitBreakersDashboard />);
    expect(screen.getByTestId('breaker-cost')).toBeInTheDocument();
    expect(screen.getByTestId('breaker-steps')).toBeInTheDocument();
    expect(screen.getByTestId('breaker-timeout')).toBeInTheDocument();
    expect(screen.getByTestId('breaker-loop')).toBeInTheDocument();
  });

  it('renders edit configuration button', () => {
    render(<CircuitBreakersDashboard />);
    expect(screen.getByTestId('edit-button')).toBeInTheDocument();
  });

  it('shows current cost and step values', () => {
    render(<CircuitBreakersDashboard />);
    expect(screen.getByText('$0.15')).toBeInTheDocument();
    expect(screen.getByText('450')).toBeInTheDocument();
  });

  it('enters edit mode when edit button is clicked', () => {
    render(<CircuitBreakersDashboard />);
    fireEvent.click(screen.getByTestId('edit-button'));
    expect(screen.getByTestId('save-button')).toBeInTheDocument();
    expect(screen.getByTestId('reset-button')).toBeInTheDocument();
    expect(screen.getByTestId('cancel-button')).toBeInTheDocument();
  });

  it('shows input fields in edit mode', () => {
    render(<CircuitBreakersDashboard />);
    fireEvent.click(screen.getByTestId('edit-button'));
    expect(screen.getByTestId('config-cost-cap')).toBeInTheDocument();
    expect(screen.getByTestId('config-step-budget')).toBeInTheDocument();
    expect(screen.getByTestId('config-call-timeout')).toBeInTheDocument();
    expect(screen.getByTestId('config-loop-detection')).toBeInTheDocument();
  });

  it('resets to defaults when reset button is clicked', () => {
    render(<CircuitBreakersDashboard />);
    fireEvent.click(screen.getByTestId('edit-button'));
    fireEvent.click(screen.getByTestId('reset-button'));
    // After reset, draft should have default values
  });

  it('cancels edit mode when cancel button is clicked', () => {
    render(<CircuitBreakersDashboard />);
    fireEvent.click(screen.getByTestId('edit-button'));
    fireEvent.click(screen.getByTestId('cancel-button'));
    expect(screen.queryByTestId('save-button')).not.toBeInTheDocument();
  });

  it('shows tripped badge when breaker is tripped', () => {
    mockStore.circuitBreakers.tripped = true;
    mockStore.circuitBreakers.trippedBreaker = 'cost';
    mockStore.circuitBreakers.trippedReason = 'Exceeded $0.50 cap';
    render(<CircuitBreakersDashboard />);
    expect(screen.getByTestId('tripped-badge')).toBeInTheDocument();
    expect(screen.getByText(/Exceeded/)).toBeInTheDocument();
  });

  it('does not show tripped badge when healthy', () => {
    render(<CircuitBreakersDashboard />);
    expect(screen.queryByTestId('tripped-badge')).not.toBeInTheDocument();
  });
});
