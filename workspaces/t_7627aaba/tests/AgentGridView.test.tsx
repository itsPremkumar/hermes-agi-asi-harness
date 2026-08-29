/**
 * Tests for AgentGridView.
 * Verifies: empty state, error state, agent card rendering with resources,
 * status badges, and that selecting a card fetches plan + trace.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { useStudioStore } from '../src/store/studioStore';
import { makeMockApi, makeAgent, resetStore } from './helpers';
import AgentGridView from '../src/views/AgentGridView';
import { MemoryRouter } from 'react-router-dom';

const mockApi = makeMockApi();
vi.mock('../src/store/StoreProvider', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/store/StoreProvider')>();
  return {
    ...actual,
    useStoreContext: () => ({ api: mockApi, sse: { connect: vi.fn(), disconnect: vi.fn(), subscribe: vi.fn(() => () => {}), status: 'connected' } }),
    useStore: actual.useStore,
  };
});

const renderWithRouter = () =>
  render(
    <MemoryRouter initialEntries={['/']}>
      <AgentGridView />
    </MemoryRouter>,
  );

describe('AgentGridView', () => {
  beforeEach(() => {
    resetStore({ agents: [] });
  });

  it('renders "No agents running" when the list is empty', () => {
    renderWithRouter();
    expect(screen.getByText(/No agents running/i)).toBeInTheDocument();
  });

  it('renders a card per agent with name, status badge, and resources', () => {
    useStudioStore.getState().setAgents([
      makeAgent({ id: 'a1', name: 'Planner', status: 'executing', resources: { tokens: 1500, cost: 0.12, cpuMs: 420 } }),
      makeAgent({ id: 'a2', name: 'Executor', status: 'done', resources: { tokens: 800, cost: 0.05, cpuMs: 310 } }),
    ]);
    renderWithRouter();

    const cards = screen.getAllByTestId('agent-card');
    expect(cards).toHaveLength(2);
    expect(screen.getByText('Planner')).toBeInTheDocument();
    expect(screen.getByText('Executor')).toBeInTheDocument();

    const badges = screen.getAllByTestId('status-badge');
    expect(badges[0]).toHaveAttribute('data-status', 'executing');
    expect(badges[1]).toHaveAttribute('data-status', 'done');
  });

  it('shows resource rows with tokens, cost, and CPU', () => {
    useStudioStore.getState().setAgents([
      makeAgent({
        id: 'a1',
        name: 'Worker',
        resources: { tokens: 1234, cost: 0.256, cpuMs: 789 },
      }),
    ]);
    renderWithRouter();
    expect(screen.getByText('1,234')).toBeInTheDocument();
    expect(screen.getByText('$0.256')).toBeInTheDocument();
    expect(screen.getByText('789ms')).toBeInTheDocument();
  });

  it('fetches plan + trace when a card is clicked', async () => {
    useStudioStore.getState().setAgents([
      makeAgent({ id: 'a1', name: 'Worker', status: 'idle' }),
    ]);
    renderWithRouter();
    fireEvent.click(screen.getByTestId('agent-card'));

    await waitFor(() => {
      expect(mockApi.fetchPlan).toHaveBeenCalledWith('a1');
      expect(mockApi.fetchTrace).toHaveBeenCalledWith('a1');
    });
  });

  it('shows error message when fetch fails and no agents loaded', () => {
    useStudioStore.getState().setLoadingAgents(false);
    useStudioStore.getState().setError('network error');
    renderWithRouter();
    expect(screen.getByText('Error: network error')).toBeInTheDocument();
  });
});
