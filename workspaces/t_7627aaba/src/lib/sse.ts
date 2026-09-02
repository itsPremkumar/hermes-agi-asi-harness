/**
 * SSE streaming client for real-time agent events.
 * Connects to /stream and emits typed events into the Zustand store.
 *
 * @see hermes-avo/docs/trace-event-schema.md for event schema
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { TraceEvent } from '../types/trace';

export interface SseClientOptions {
  url: string;
  /** Auto-reconnect delay in ms (default 5000). */
  reconnectDelay?: number;
  /** Max reconnect attempts before giving up (default 10). */
  maxReconnects?: number;
  /** Heartbeat interval to detect dead connections (default 30000). */
  heartbeatInterval?: number;
}

export type SseStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface SseClientInterface {
  readonly status: SseStatus;
  connect(): void;
  disconnect(): void;
  subscribe(cb: (event: TraceEvent) => void): () => void;
}

export class SseClient implements SseClientInterface {
  private url: string;
  private reconnectDelay: number;
  private maxReconnects: number;
  private reconnectAttempts = 0;
  private eventSource: EventSource | null = null;
  private subscribers: Set<(event: TraceEvent) => void> = new Set();
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _status: SseStatus = 'disconnected';

  constructor(options: SseClientOptions) {
    this.url = options.url;
    this.reconnectDelay = options.reconnectDelay ?? 5000;
    this.maxReconnects = options.maxReconnects ?? 10;
  }

  get status(): SseStatus {
    return this._status;
  }

  connect(): void {
    if (this._status === 'connected') return;
    this._status = 'connecting';
    this.eventSource = new EventSource(this.url);

    this.eventSource.onopen = () => {
      this._status = 'connected';
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.eventSource.onmessage = (e) => {
      this.handleMessage(e);
    };

    this.eventSource.onerror = () => {
      this._status = 'error';
      this.stopHeartbeat();
      this.cleanup();
      if (this.reconnectAttempts < this.maxReconnects) {
        this.reconnectAttempts++;
        this.reconnectTimer = setTimeout(
          () => this.connect(),
          this.reconnectDelay * this.reconnectAttempts,
        );
      } else {
        this._status = 'disconnected';
      }
    };
  }

  disconnect(): void {
    this._status = 'disconnected';
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  private cleanup(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  private handleMessage(e: MessageEvent): void {
    try {
      const data = JSON.parse(e.data) as TraceEvent;
      this.subscribers.forEach((cb) => cb(data));
    } catch {
      // Malformed JSON — silently drop per spec.
    }
  }

  private startHeartbeat(): void {
    if (this.heartbeatTimer) return;
    this.heartbeatTimer = setInterval(() => {
      if (this.eventSource?.readyState !== EventSource.CONNECTED) {
        this._status = 'error';
        this.stopHeartbeat();
        if (this.reconnectAttempts < this.maxReconnects) {
          this.reconnectAttempts++;
          this.reconnectTimer = setTimeout(
            () => this.connect(),
            this.reconnectDelay * this.reconnectAttempts,
          );
        }
      }
    }, 30000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  subscribe(cb: (event: TraceEvent) => void): () => void {
    this.subscribers.add(cb);
    return () => {
      this.subscribers.delete(cb);
    };
  }
}

/**
 * Factory that creates an SseClientInterface from a URL.
 */
export function createSseClient(url: string): SseClientInterface {
  return new SseClient({ url });
}

// ─── React Hook ─────────────────────────────────────────────────

export interface UseAgentStreamResult {
  /** Stream of trace events received from the SSE endpoint. */
  events: TraceEvent[];
  /** Current connection status. */
  status: SseStatus;
  /** Error message if the stream errored, or null. */
  error: string | null;
  /** Manually reconnect the stream. */
  reconnect: () => void;
}

/**
 * React hook that wraps the SSE client with auto-reconnect.
 *
 * @param url - The SSE endpoint URL (e.g. '/stream').
 * @param options - Optional configuration for reconnect behaviour.
 *
 * @example
 * const { events, status, error, reconnect } = useAgentStream('/stream');
 */
export function useAgentStream(
  url: string,
  options?: {
    reconnectDelay?: number;
    maxReconnects?: number;
  },
): UseAgentStreamResult {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [status, setStatus] = useState<SseStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);

  const clientRef = useRef<SseClient | null>(null);

  // Lazily create the client once
  if (!clientRef.current) {
    clientRef.current = new SseClient({
      url,
      reconnectDelay: options?.reconnectDelay ?? 1000,
      maxReconnects: options?.maxReconnects ?? 10,
    });
  }

  const client = clientRef.current;

  const connect = useCallback(() => {
    setError(null);
    client.connect();
  }, [client]);

  useEffect(() => {
    const unsub = client.subscribe((event) => {
      setEvents((prev) => [...prev, event]);
    });

    // Poll the client status so React re-renders on change
    const interval = setInterval(() => {
      const s = client.status;
      setStatus(s);
      if (s === 'error') {
        setError('SSE connection error — attempting to reconnect...');
      }
    }, 200);

    connect();

    return () => {
      unsub();
      clearInterval(interval);
      client.disconnect();
    };
  }, [client, connect]);

  const reconnect = useCallback(() => {
    client.disconnect();
    connect();
  }, [client, connect]);

  return { events, status, error, reconnect };
}
