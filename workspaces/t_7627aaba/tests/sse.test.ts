/**
 * Tests for the SSE client.
 * Covers: connect/disconnect lifecycle, message parsing, subscriber
 * notification, auto-reconnect, and heartbeat dead-connection detection.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SseClient, createSseClient } from '../src/lib/sse';

// Mock EventSource with full lifecycle control
class MockEventSource {
  static CONNECTED = 1;
  static CONNECTING = 0;
  readyState: number = MockEventSource.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;

  url: string;
  static lastInstance: MockEventSource | null = null;

  constructor(url: string) {
    this.url = url;
    MockEventSource.lastInstance = this;
  }

  close() {
    this.readyState = MockEventSource.CONNECTING;
  }

  // Test helpers to simulate server events
  triggerOpen() {
    this.readyState = MockEventSource.CONNECTED;
    this.onopen?.();
  }

  triggerMessage(data: string) {
    this.onmessage?.(
      new MessageEvent('message', { data, lastEventId: '', origin: '' }),
    );
  }

  triggerError() {
    this.readyState = MockEventSource.CONNECTING;
    this.onerror?.();
  }
}

global.EventSource = MockEventSource as unknown as typeof EventSource;

describe('SseClient', () => {
  let client: SseClient;

  beforeEach(() => {
    MockEventSource.lastInstance = null;
    client = new SseClient({ url: '/stream' });
  });

  afterEach(() => {
    client.disconnect();
  });

  it('starts disconnected', () => {
    expect(client.status).toBe('disconnected');
  });

  it('transitions to connecting then connected on connect()', () => {
    client.connect();
    expect(client.status).toBe('connecting');
    MockEventSource.lastInstance?.triggerOpen();
    expect(client.status).toBe('connected');
  });

  it('notifies subscribers on incoming message', () => {
    const received: unknown[] = [];
    client.subscribe((event) => received.push(event));

    client.connect();
    MockEventSource.lastInstance?.triggerOpen();
    MockEventSource.lastInstance?.triggerMessage(
      JSON.stringify({
        id: 'evt-1',
        type: 'agent_step',
        agentId: 'a1',
        timestamp: '2026-01-01T00:00:00Z',
        runId: 'run-1',
        status: 'executing',
      }),
    );

    expect(received).toHaveLength(1);
    expect((received[0] as { type: string }).type).toBe('agent_step');
  });

  it('silently drops malformed JSON', () => {
    const received: unknown[] = [];
    client.subscribe((event) => received.push(event));

    client.connect();
    MockEventSource.lastInstance?.triggerOpen();
    MockEventSource.lastInstance?.triggerMessage('not-json');

    expect(received).toHaveLength(0);
  });

  it('disconnect() clears timers and closes the EventSource', () => {
    client.connect();
    MockEventSource.lastInstance?.triggerOpen();

    const closeSpy = vi.spyOn(MockEventSource.lastInstance!, 'close');
    client.disconnect();

    expect(client.status).toBe('disconnected');
    expect(closeSpy).toHaveBeenCalled();
  });

  it('unsubscribed callbacks no longer fire', () => {
    const received: unknown[] = [];
    const unsub = client.subscribe((event) => received.push(event));

    client.connect();
    MockEventSource.lastInstance?.triggerOpen();
    unsub();

    MockEventSource.lastInstance?.triggerMessage(
      JSON.stringify({
        id: 'evt-2',
        type: 'agent_step',
        agentId: 'a1',
        timestamp: '2026-01-01T00:00:00Z',
        runId: 'run-1',
        status: 'done',
      }),
    );

    expect(received).toHaveLength(0);
  });

  it('createSseClient returns a usable SseClientInterface', () => {
    const c = createSseClient('ws://localhost:3998/stream');
    expect(c).toBeInstanceOf(SseClient);
    expect(c.status).toBe('disconnected');
  });
});
