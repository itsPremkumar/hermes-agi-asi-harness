/**
 * Tests for SSE streaming client.
 * @vitest @unit
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SseClient, createSseClient, type SseClientInterface } from '../src/lib/sse';
import type { TraceEvent } from '../src/types/trace';

// Mock EventSource
class MockEventSource {
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  readyState: number = MockEventSource.CONNECTING;

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  static instances: MockEventSource[] = [];

  close() {
    this.readyState = MockEventSource.CLOSED;
  }

  emitOpen() {
    this.readyState = MockEventSource.OPEN;
    this.onopen?.();
  }

  emitMessage(data: string) {
    this.onmessage?.({ data } as MessageEvent);
  }

  emitError() {
    this.onerror?.();
  }
}

global.EventSource = MockEventSource as any;
global.MessageEvent = class {
  data: string;
  constructor(data: string) {
    this.data = data;
  }
} as any;

describe('SseClient', () => {
  let client: SseClient;
  let mockEvents: MockEventSource[];

  beforeEach(() => {
    MockEventSource.instances = [];
    client = new SseClient({ url: '/stream' });
  });

  afterEach(() => {
    client.disconnect();
  });

  it('starts in disconnected state', () => {
    expect(client.status).toBe('disconnected');
  });

  it('transitions to connecting on connect()', () => {
    client.connect();
    expect(client.status).toBe('connecting');
  });

  it('transitions to connected on open event', () => {
    client.connect();
    MockEventSource.instances[0]?.emitOpen();
    expect(client.status).toBe('connected');
  });

  it('subscribes and receives events', () => {
    const received: TraceEvent[] = [];
    const unsub = client.subscribe((e) => received.push(e));

    client.connect();
    MockEventSource.instances[0]?.emitOpen();

    const event: TraceEvent = {
      id: 'evt-1',
      type: 'agent_step',
      agentId: 'agent-1',
      timestamp: new Date().toISOString(),
      runId: 'run-1',
      status: 'planning',
    };

    MockEventSource.instances[0]?.emitMessage(JSON.stringify(event));
    expect(received).toHaveLength(1);
    expect(received[0].agentId).toBe('agent-1');

    unsub();
  });

  it('handles malformed JSON gracefully', () => {
    const handler = vi.fn();
    client.subscribe(handler);
    client.connect();
    MockEventSource.instances[0]?.emitOpen();
    MockEventSource.instances[0]?.emitMessage('not json');
    expect(handler).not.toHaveBeenCalled();
  });

  it('disconnects and closes EventSource', () => {
    client.connect();
    MockEventSource.instances[0]?.emitOpen();
    client.disconnect();
    expect(client.status).toBe('disconnected');
  });

  it('createSseClient factory returns a client', () => {
    const c = createSseClient('/stream');
    expect(c).toBeDefined();
    expect(typeof c.connect).toBe('function');
    expect(typeof c.subscribe).toBe('function');
  });

  it('reconnects on error up to maxReconnects', () => {
    const c = new SseClient({
      url: '/stream',
      reconnectDelay: 100,
      maxReconnects: 3,
    });
    c.connect();
    MockEventSource.instances[0]?.emitOpen();

    // Simulate error
    MockEventSource.instances[0]?.emitError();
    expect(c.status).toBe('error');
  });
});
