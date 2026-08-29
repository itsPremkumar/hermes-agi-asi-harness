/**
 * Tests for CircuitBreakersDashboard.
 * Verifies: rendering of all four breakers, edit/save/cancel/reset flow,
 * tripped state display, and progress math.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useStudioStore } from '../src/store/studioStore';
import { makeMockApi, resetStore } from './helpers';
import CircuitBreakersDashboard from '../src/components/CircuitBreakersDashboard';

// Mock useStoreContext so we can inject a mock api
const mockApi = makeMockApi();
vi.mock('../src/store/StoreProvider', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/store/StoreProvider')>();
  return {
    ...actual,
    useStoreContext: () => ({ api: mockApi, sse: { connect: vi.fn(), disconnect: vi.fn(), subscribe: vi.fn(() => () => {}), status: 'connected' } }),
  };
});

const renderComponent = () => render(<CircuitBreakersDashboard />);

describe('CircuitBreakersDashboard', () => {
  beforeEach(() => {
    resetStore({
      circuitBreakers: {
        config: { costCapUSD: 0.5, stepBudget: 1000, timeoutSeconds: 30, loopDetectionThreshold: 3 },
        currentCost: 0.1,
        stepsConsumed: 200,
        activeSince: '2026-01-01T00:00:00Z',
        tripped: false,
        trippedBreaker: null,
        trippedReason: undefined,
      },
    });
  });

  it('renders all four breaker cards', () => {
    renderComponent();
    expect(screen.getByTestId('breaker-cost')).toBeInTheDocument();
    expect(screen.getByTestId('breaker-steps')).toBeInTheDocument();
    expect(screen.getByTestId('breaker-timeout')).toBeInTheDocument();
    expect(screen.getByTestId('breaker-loop')).toBeInTheDocument();
  });

  it('shows cost progress as $0.100 against $0.50 cap', () => {
    renderComponent();
    expect(screen.getByText('$0.100')).toBeInTheDocument();
    expect(screen.getByText('/ 0.5')).toBeInTheDocument();
  });

  it('shows step progress as 200 against 1000', () => {
    renderComponent();
    expect(screen.getByText('200')).toBeInTheDocument();
    expect(screen.getByText('/ 1000')).toBeInTheDocument();
  });

  it('does not show tripped badge when not tripped', () => {
    renderComponent();
    expect(screen.queryByTestId('tripped-badge')).not.toBeInTheDocument();
  });

  it('shows tripped badge when a breaker is tripped', () => {
    resetStore({
      circuitBreakers: {
        config: { costCapUSD: 0.5, stepBudget: 1000, timeoutSeconds: 30, loopDetectionThreshold: 3 },
        currentCost: 0.6,
        stepsConsumed: 100,
        activeSince: '2026-01-01T00:00:00Z',
        tripped: true,
        trippedBreaker: 'cost',
        trippedReason: 'Budget exceeded',
      },
    });
    renderComponent();
    const badge = screen.getByTestId('tripped-badge');
    expect(badge).toHaveTextContent('TRIPPED: cost — Budget exceeded');
  });

  it('enters edit mode, updates draft, then saves via API', async () => {
    renderComponent();
    fireEvent.click(screen.getByTestId('edit-button'));

    const costInput = screen.getByTestId('config-cost-cap') as HTMLInputElement;
    fireEvent.change(costInput, { target: { value: '1.0' } });

    fireEvent.click(screen.getByTestId('save-button'));

    await waitFor(() => {
      expect(mockApi.updateCircuitBreakers).toHaveBeenCalledWith({ costCapUSD: 1.0 });
    });
    expect(screen.queryByTestId('save-button')).not.toBeInTheDocument();
  });

  it('cancel exits edit mode without saving', async () => {
    renderComponent();
    fireEvent.click(screen.getByTestId('edit-button'));

    const stepInput = screen.getByTestId('config-step-budget') as HTMLInputElement;
    fireEvent.change(stepInput, { target: { value: '500' } });

    fireEvent.click(screen.getByTestId('cancel-button'));
    expect(screen.queryByTestId('save-button')).not.toBeInTheDocument();
    expect(mockApi.updateCircuitBreakers).not.toHaveBeenCalled();
  });

  it('reset button restores default config values', () => {
    renderComponent();
    fireEvent.click(screen.getByTestId('edit-button'));

    const costInput = screen.getByTestId('config-cost-cap') as HTMLInputElement;
    fireEvent.change(costInput, { target: { value: '5.0' } });
    expect(costInput.value).toBe('5');

    fireEvent.click(screen.getByTestId('reset-button'));
    const costInputAfterReset = screen.getByTestId('config-cost-cap') as HTMLInputElement;
    expect(costInputAfterReset.value).toBe('0.5');
  });
});
