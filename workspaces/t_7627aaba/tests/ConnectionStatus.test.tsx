/**
 * Tests for ConnectionStatus — SSE status dot + API-triggered fetch.
 * Verifies the connection indicator reflects SSE status changes.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useStudioStore } from '../src/store/studioStore';
import { makeMockApi, resetStore } from './helpers';
import { ConnectionStatus } from '../src/components/ConnectionStatus';
import { SseClient } from '../src/lib/sse';

vi.mock('../src/store/StoreProvider', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/store/StoreProvider')>();
  return {
    ...actual,
    useStoreContext: () => ({ api: makeMockApi(), sse: { connect: vi.fn(), disconnect: vi.fn(), subscribe: vi.fn(() => () => {}), status: 'connected' } }),
    useStore: actual.useStore,
  };
});

describe('ConnectionStatus', () => {
  beforeEach(() => {
    resetStore({ agents: [] });
  });

  it('renders "Connected" when SSE status is connected', () => {
    useStudioStore.getState().setSseStatus('connected');
    render(<ConnectionStatus />);
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('renders "Connecting..." when SSE status is connecting', () => {
    useStudioStore.getState().setSseStatus('connecting');
    render(<ConnectionStatus />);
    expect(screen.getByText('Connecting...')).toBeInTheDocument();
  });

  it('renders "Disconnected" when SSE status is disconnected', () => {
    useStudioStore.getState().setSseStatus('disconnected');
    render(<ConnectionStatus />);
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('renders error text when an error is set', () => {
    useStudioStore.getState().setSseStatus('connected');
    useStudioStore.getState().setError('Connection timeout');
    render(<ConnectionStatus />);
    expect(screen.getByText(/Connection timeout/)).toBeInTheDocument();
  });

  it('renders the connection status dot with correct class for connected', () => {
    useStudioStore.getState().setSseStatus('connected');
    const { container } = render(<ConnectionStatus />);
    const dot = container.querySelector('.h-2.w-2');
    expect(dot).toHaveClass('bg-green-500');
  });
});
