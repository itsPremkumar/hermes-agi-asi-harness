/**
 * Tests for AgentDetailView — the /agent/:agentId route.
 * Verifies: agent lookup by param, plan/trace fetch on mount,
 * placeholder rendering when plan is loaded, and not-found state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { useStudioStore } from '../src/store/studioStore';
import { makeMockApi, makeAgent, resetStore } from './helpers';
import AgentDetailView from '../src/views/AgentDetailView';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const mockApi = makeMockApi();
vi.mock('../src/store/StoreProvider', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/store/StoreProvider')>();
  return {
    ...actual,
    useStoreContext: () => ({ api: mockApi, sse: { connect: vi.fn(), disconnect: vi.fn(), subscribe: vi.fn(() => () => {}), status: 'connected' } }),
    useStore: actual.useStore,
  };
});

const renderWithRoute = (agentId: string) =>
  render(
    <MemoryRouter initialEntries={[`/agent/${agentId}`]}>
      <Routes>
        <Route path="/agent/:agentId" element={<AgentDetailView />} />
      </Routes>
    </MemoryRouter>,
  );

describe('AgentDetailView', () => {
  beforeEach(() => {
    resetStore({ agents: [], plans: {} });
  });

  it('fetches plan + trace for the agent on mount', async () => {
    useStudioStore.getState().setAgents([
      makeAgent({ id: 'a1', name: 'Worker', status: 'executing' }),
    ]);
    renderWithRoute('a1');

    await waitFor(() => {
      expect(mockApi.fetchPlan).toHaveBeenCalledWith('a1');
      expect(mockApi.fetchTrace).toHaveBeenCalledWith('a1');
    });
  });

  it('renders agent name + status badge when agent exists', () => {
    useStudioStore.getState().setAgents([
      makeAgent({ id: 'a1', name: 'Worker', status: 'done' }),
    ]);
    renderWithRoute('a1');

    expect(screen.getByText('Worker')).toBeInTheDocument();
    expect(screen.getByTestId('status-badge')).toHaveAttribute('data-status', 'done');
  });

  it('shows resource summary (tokens, cost, CPU)', () => {
    useStudioStore.getState().setAgents([
      makeAgent({
        id: 'a1',
        name: 'Worker',
        status: 'executing',
        resources: { tokens: 2048, cost: 0.35, cpuMs: 1200 },
      }),
    ]);
    renderWithRoute('a1');
    expect(screen.getByText('Tokens: 2,048')).toBeInTheDocument();
    expect(screen.getByText('Cost: $0.350')).toBeInTheDocument();
    expect(screen.getByText('CPU: 1200ms')).toBeInTheDocument();
  });

  it('renders plan placeholder when plan not yet loaded', () => {
    useStudioStore.getState().setAgents([
      makeAgent({ id: 'a1', name: 'Worker' }),
    ]);
    renderWithRoute('a1');
    expect(screen.getByTestId('plan-placeholder')).toBeInTheDocument();
  });

  it('renders plan summary when plan is loaded', () => {
    useStudioStore.getState().setAgents([
      makeAgent({ id: 'a1', name: 'Worker' }),
    ]);
    useStudioStore.getState().setPlan('a1', {
      id: 'root',
      name: 'Deploy Application',
      type: 'goal',
      children: [],
      status: 'complete',
      toolCalls: [],
    });
    renderWithRoute('a1');
    expect(screen.getByTestId('plan-summary')).toBeInTheDocument();
    expect(screen.getByText('Root Goal: Deploy Application')).toBeInTheDocument();
  });

  it('renders not-found message for unknown agent', () => {
    renderWithRoute('unknown-123');
    expect(screen.getByText(/Agent unknown-123 not found/i)).toBeInTheDocument();
  });

  it('renders chat placeholder with "no messages" state', () => {
    useStudioStore.getState().setAgents([
      makeAgent({ id: 'a1', name: 'Worker' }),
    ]);
    renderWithRoute('a1');
    expect(screen.getByTestId('chat-placeholder')).toBeInTheDocument();
    expect(screen.getByText(/No messages yet/i)).toBeInTheDocument();
  });

  it('renders chat placeholder with messages when store has them', () => {
    useStudioStore.getState().setAgents([
      makeAgent({ id: 'a1', name: 'Worker' }),
    ]);
    useStudioStore.getState().appendMessage({
      id: 'm1',
      role: 'user',
      content: 'analyze codebase',
      timestamp: 'now',
    });
    renderWithRoute('a1');
    expect(screen.getByTestId('detail-message')).toBeInTheDocument();
  });
});
