/**
 * Tests for ChatInterface — command parsing, message rendering,
 * quick action buttons, and send flow.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { useStudioStore } from '../src/store/studioStore';
import { makeMockApi, resetStore } from './helpers';
import ChatInterface from '../src/components/ChatInterface';

const mockApi = makeMockApi();
vi.mock('../src/store/StoreProvider', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/store/StoreProvider')>();
  return {
    ...actual,
    useStoreContext: () => ({ api: mockApi, sse: { connect: vi.fn(), disconnect: vi.fn(), subscribe: vi.fn(() => () => {}), status: 'connected' } }),
    useStore: actual.useStore,
  };
});

describe('ChatInterface', () => {
  beforeEach(() => {
    resetStore({ agents: {}, activeAgentId: 'agent-1' });
  });

  it('renders the control channel header with target agent name', () => {
    useStudioStore.getState().setAgents([
      { id: 'agent-1', name: 'Worker-1', status: 'idle', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r1' },
    ]);
    render(<ChatInterface />);
    expect(screen.getByText('Control Channel')).toBeInTheDocument();
    expect(screen.getByText('Target: Worker-1')).toBeInTheDocument();
  });

  it('renders empty state when no messages exist', () => {
    render(<ChatInterface />);
    // Input always present
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
  });

  it('renders messages from the store', () => {
    useStudioStore.getState().appendMessage({
      id: 'm1',
      role: 'user',
      content: 'hello agent',
      timestamp: 'now',
    });
    render(<ChatInterface />);
    expect(screen.getByText('hello agent')).toBeInTheDocument();
  });

  it('send button is present and click submits', () => {
    render(<ChatInterface />);
    const input = screen.getByTestId('chat-input');
    fireEvent.change(input, { target: { value: 'run task' } });
    fireEvent.click(screen.getByTestId('send-button'));
    // User message is appended optimistically
    expect(screen.getByText('run task')).toBeInTheDocument();
  });

  it('quick action buttons render with correct testids', () => {
    render(<ChatInterface />);
    expect(screen.getByTestId('quick-status')).toBeInTheDocument();
    expect(screen.getByTestId('quick-cancel')).toBeInTheDocument();
    expect(screen.getByTestId('quick-escalate')).toBeInTheDocument();
  });

  it('quick action click sends a slash command message', () => {
    render(<ChatInterface />);
    fireEvent.click(screen.getByTestId('quick-status'));
    const msgs = screen.getAllByTestId('message-row');
    expect(msgs.length).toBeGreaterThan(0);
  });

  it('empty input does not submit', () => {
    render(<ChatInterface />);
    fireEvent.click(screen.getByTestId('send-button'));
    // No messages appended
    expect(screen.queryByTestId('message-row')).not.toBeInTheDocument();
  });
});
