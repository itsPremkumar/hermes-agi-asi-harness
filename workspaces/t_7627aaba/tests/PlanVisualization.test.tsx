/**
 * Tests for PlanVisualization — the collapsible HTN tree.
 * Verifies: empty state, tree node rendering, expand/collapse toggle,
 * tool-call detail toggle, and status color mapping.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { useStudioStore } from '../src/store/studioStore';
import { makeMockApi, resetStore } from './helpers';
import PlanVisualization from '../src/views/PlanVisualization';
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

const sampleTree = {
  id: 'root',
  name: 'Main Goal',
  type: 'goal' as const,
  status: 'complete' as const,
  children: [
    {
      id: 'child-1',
      name: 'Subtask A',
      type: 'task' as const,
      status: 'running' as const,
      children: [],
      toolCalls: [
        {
          id: 'tc1',
          name: 'search_code',
          args: { query: 'auth' },
          result: 'found 3 matches',
          startedAt: '2026-01-01T00:00:00Z',
          status: 'complete' as const,
        },
      ],
    },
  ],
};

describe('PlanVisualization', () => {
  beforeEach(() => {
    resetStore({ agents: [], plans: {} });
  });

  it('renders placeholder when no plan is loaded', () => {
    render(<MemoryRouter><PlanVisualization /></MemoryRouter>);
    expect(screen.getByText(/Select an agent to view its plan/i)).toBeInTheDocument();
  });

  it('renders the root plan node + children after plan is loaded', () => {
    useStudioStore.getState().setActiveAgent('a1');
    useStudioStore.getState().setPlan('a1', sampleTree);
    render(<MemoryRouter><PlanVisualization /></MemoryRouter>);

    expect(screen.getByText('Main Goal')).toBeInTheDocument();
    expect(screen.getByText('Subtask A')).toBeInTheDocument();
    expect(screen.getAllByTestId('tree-node')).toHaveLength(2);
  });

  it('node status labels are rendered', () => {
    useStudioStore.getState().setActiveAgent('a1');
    useStudioStore.getState().setPlan('a1', sampleTree);
    render(<MemoryRouter><PlanVisualization /></MemoryRouter>);

    expect(screen.getByText('Complete')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('toggle button collapses/expand children', () => {
    useStudioStore.getState().setActiveAgent('a1');
    useStudioStore.getState().setPlan('a1', sampleTree);
    render(<MemoryRouter><PlanVisualization /></MemoryRouter>);

    // Initially expanded
    expect(screen.getByText('Subtask A')).toBeInTheDocument();

    // Collapse — the child should disappear
    fireEvent.click(screen.getByTestId('toggle-root'));
    expect(screen.queryByText('Subtask A')).not.toBeInTheDocument();

    // Expand again
    fireEvent.click(screen.getByTestId('toggle-root'));
    expect(screen.getByText('Subtask A')).toBeInTheDocument();
  });

  it('clicking a node with tool calls shows the details panel', () => {
    useStudioStore.getState().setActiveAgent('a1');
    useStudioStore.getState().setPlan('a1', sampleTree);
    render(<MemoryRouter><PlanVisualization /></MemoryRouter>);

    fireEvent.click(screen.getByTestId('details-child-1'));
    expect(screen.getByTestId('tool-call-details')).toBeInTheDocument();
  });

  it('node with no children has no toggle button', () => {
    useStudioStore.getState().setActiveAgent('a1');
    useStudioStore.getState().setPlan('a1', sampleTree);
    render(<MemoryRouter><PlanVisualization /></MemoryRouter>);

    // child-1 has no children, so no toggle button for it
    expect(screen.queryByTestId('toggle-child-1')).not.toBeInTheDocument();
  });
});
