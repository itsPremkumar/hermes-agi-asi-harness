/**
 * Tests for AvoStudioApi REST client.
 * @vitest @unit
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AvoStudioApi } from '../src/lib/api';
import { DEFAULT_CIRCUIT_BREAKERS } from '../src/types/trace';

const API_BASE = 'http://localhost:3998/api';

describe('AvoStudioApi', () => {
  let api: AvoStudioApi;
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockFetch = vi.fn();
    global.fetch = mockFetch as any;
    api = new AvoStudioApi();
  });

  it('constructs with default /api base URL', () => {
    const a = new AvoStudioApi();
    expect(a.baseUrl).toBe('/api');
  });

  it('constructs with custom base URL', () => {
    const a = new AvoStudioApi('http://example.com/api');
    expect(a.baseUrl).toBe('http://example.com/api');
  });

  it('fetchAgents returns agent list on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        agents: [
          { id: 'agent-1', name: 'Bot', status: 'done', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r1' },
        ],
      }),
    });
    const agents = await api.fetchAgents();
    expect(agents).toHaveLength(1);
    expect(agents[0].id).toBe('agent-1');
  });

  it('fetchAgents throws on HTTP error', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
    await expect(api.fetchAgents()).rejects.toThrow('Failed to fetch agents');
  });

  it('fetchAgent returns matching agent', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        agents: [
          { id: 'a1', name: 'Bot1', status: 'done', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r1' },
          { id: 'a2', name: 'Bot2', status: 'done', resources: { tokens: 0, cost: 0, cpuMs: 0 }, lastSeen: '', runId: 'r1' },
        ],
      }),
    });
    const agent = await api.fetchAgent('a2');
    expect(agent?.name).toBe('Bot2');
  });

  it('fetchAgent returns null when not found', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ agents: [] }),
    });
    const agent = await api.fetchAgent('nonexistent');
    expect(agent).toBeNull();
  });

  it('fetchPlan fetches plan by agent ID', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        plan: { id: 'p1', name: 'Test plan', type: 'goal', status: 'pending', children: [], toolCalls: [] },
      }),
    });
    const plan = await api.fetchPlan('agent-1');
    expect(plan.id).toBe('p1');
    expect(plan.name).toBe('Test plan');
  });

  it('fetchTrace fetches trace by agent ID', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        trace: {
          agentId: 'agent-1',
          plan: { id: 'p', name: 'p', type: 'goal', status: 'pending', children: [], toolCalls: [] },
          events: [],
          causalEdges: [],
        },
      }),
    });
    const trace = await api.fetchTrace('agent-1');
    expect(trace.agentId).toBe('agent-1');
  });

  it('sendChatMessage sends POST with message body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, reply: 'Acknowledged' }),
    });
    const resp = await api.sendChatMessage({
      id: 'msg-1',
      role: 'user',
      content: '/execute hello',
      timestamp: new Date().toISOString(),
      command: 'execute',
      args: 'hello',
    });
    expect(resp.ok).toBe(true);
    expect(resp.reply).toBe('Acknowledged');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/chat'),
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('fetchCircuitBreakers returns config', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => DEFAULT_CIRCUIT_BREAKERS,
    });
    const config = await api.fetchCircuitBreakers();
    expect(config.costCapUSD).toBe(0.5);
    expect(config.stepBudget).toBe(1000);
    expect(config.timeoutSeconds).toBe(30);
    expect(config.loopDetectionThreshold).toBe(3);
  });

  it('updateCircuitBreakers sends PUT with partial config', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ...DEFAULT_CIRCUIT_BREAKERS, costCapUSD: 1.0 },
    });
    const config = await api.updateCircuitBreakers({ costCapUSD: 1.0 });
    expect(config.costCapUSD).toBe(1.0);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/circuit-breakers'),
      expect.objectContaining({ method: 'PUT' }),
    );
  });
});
