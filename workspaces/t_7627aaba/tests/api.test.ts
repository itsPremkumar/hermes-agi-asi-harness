/**
 * Tests for the AvoStudioApi REST client.
 * Uses a mocked fetch to verify endpoint paths, method, body serialization,
 * and response parsing.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AvoStudioApi } from '../src/lib/api';

const BASE = 'http://localhost:3998/api';

function mockFetch(response: ResponseInit & { body?: unknown }) {
  const { body, ...init } = response;
  return vi.fn().mockResolvedValue({
    ok: init.status ? init.status < 400 : true,
    status: init.status ?? 200,
    json: () => Promise.resolve(body),
  });
}

describe('AvoStudioApi', () => {
  let api: AvoStudioApi;
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    api = new AvoStudioApi(BASE);
    fetchSpy = vi.fn();
    // @ts-expect-error — patch global fetch
    global.fetch = fetchSpy;
    // Make window.location.origin available for the agents-list URL builder
    Object.defineProperty(window, 'location', {
      value: { origin: 'http://localhost:3000', href: 'http://localhost:3000/' },
      writable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetchAgents GETs /api/agents with optional runId param', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ agents: [{ id: 'a1', name: 'A1' }] }),
    });

    const agents = await api.fetchAgents('run-123');

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const calledUrl = fetchSpy.mock.calls[0]![0] as string;
    expect(calledUrl).toContain('/api/agents');
    expect(calledUrl).toContain('runId=run-123');
    expect(agents).toHaveLength(1);
    expect(agents[0]!.id).toBe('a1');
  });

  it('fetchAgent returns null when agent not found', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ agents: [{ id: 'a1', name: 'A1' }] }),
    });

    const agent = await api.fetchAgent('missing');
    expect(agent).toBeNull();
  });

  it('fetchPlan GETs /api/plans/:agentId', async () => {
    const plan = { id: 'root', name: 'Goal', type: 'goal', children: [], status: 'pending', toolCalls: [] };
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ plan }),
    });

    const result = await api.fetchPlan('agent-1');
    expect(fetchSpy.mock.calls[0]![0]).toBe(`${BASE}/plans/agent-1`);
    expect(result.id).toBe('root');
  });

  it('fetchPlan throws on non-ok response', async () => {
    fetchSpy.mockResolvedValue({ ok: false, status: 404, json: () => Promise.resolve({}) });
    await expect(api.fetchPlan('x')).rejects.toThrow('Failed to fetch plan');
  });

  it('sendChatMessage POSTs to /api/chat with JSON body', async () => {
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ ok: true, reply: 'ack' }),
    });

    const resp = await api.sendChatMessage({
      id: 'm1',
      role: 'user',
      content: 'hello',
      timestamp: '2026-01-01T00:00:00Z',
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy.mock.calls[0]![0]).toBe(`${BASE}/chat`);
    expect(fetchSpy.mock.calls[0]![1].method).toBe('POST');
    expect(fetchSpy.mock.calls[0]![1].headers['Content-Type']).toBe('application/json');
    expect(resp.reply).toBe('ack');
  });

  it('updateCircuitBreakers PUTs to /api/circuit-breakers', async () => {
    const updated = { costCapUSD: 1.0, stepBudget: 500, timeoutSeconds: 60, loopDetectionThreshold: 5 };
    fetchSpy.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(updated),
    });

    const result = await api.updateCircuitBreakers({ costCapUSD: 1.0 });
    expect(fetchSpy.mock.calls[0]![0]).toBe(`${BASE}/circuit-breakers`);
    expect(fetchSpy.mock.calls[0]![1].method).toBe('PUT');
    expect(result.costCapUSD).toBe(1.0);
  });
});
