/**
 * REST API client — talks to the AVOStudio backend.
 * Endpoints:
 *   GET  /api/agents       → AgentsResponse
 *   GET  /api/plans/:id     → PlansResponse
 *   GET  /api/traces/:id    → TracesResponse
 *   POST /api/chat          → { ok: boolean, reply: string }
 *
 * @see hermes-avo/docs/api-spec.md
 */

import type {
  AgentsResponse,
  PlansResponse,
  TracesResponse,
  CircuitBreakerConfig,
  ChatMessage,
  AVOAgent,
  AgentPlanNode,
  AgentTrace,
} from '../types/trace';

export interface AvoStudioApiBase {
  baseUrl: string;
}

export class AvoStudioApi {
  readonly baseUrl: string;

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl;
  }

  // ── Agents ──────────────────────────────────────────────────────

  async fetchAgents(runId?: string): Promise<AVOAgent[]> {
    const url = new URL(`${this.baseUrl}/agents`, window.location.origin);
    if (runId) url.searchParams.set('runId', runId);
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`Failed to fetch agents: ${res.status}`);
    const data: AgentsResponse = await res.json();
    return data.agents;
  }

  async fetchAgent(agentId: string): Promise<AVOAgent | null> {
    const agents = await this.fetchAgents();
    return agents.find((a) => a.id === agentId) ?? null;
  }

  // ── Plans ───────────────────────────────────────────────────────

  async fetchPlan(agentId: string): Promise<AgentPlanNode> {
    const res = await fetch(
      `${this.baseUrl}/plans/${encodeURIComponent(agentId)}`,
    );
    if (!res.ok) throw new Error(`Failed to fetch plan: ${res.status}`);
    const data: PlansResponse = await res.json();
    return data.plan;
  }

  // ── Traces ──────────────────────────────────────────────────────

  async fetchTrace(agentId: string): Promise<AgentTrace> {
    const res = await fetch(
      `${this.baseUrl}/traces/${encodeURIComponent(agentId)}`,
    );
    if (!res.ok) throw new Error(`Failed to fetch trace: ${res.status}`);
    const data: TracesResponse = await res.json();
    return data.trace;
  }

  // ── Chat ────────────────────────────────────────────────────────

  async sendChatMessage(
    message: ChatMessage,
  ): Promise<{ ok: boolean; reply?: string; error?: string }> {
    const res = await fetch(`${this.baseUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(message),
    });
    if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
    return await res.json();
  }

  // ── Circuit Breakers ────────────────────────────────────────────

  async fetchCircuitBreakers(): Promise<CircuitBreakerConfig> {
    const res = await fetch(`${this.baseUrl}/circuit-breakers`);
    if (!res.ok) throw new Error(`Failed to fetch breakers: ${res.status}`);
    return await res.json();
  }

  async updateCircuitBreakers(
    config: Partial<CircuitBreakerConfig>,
  ): Promise<CircuitBreakerConfig> {
    const res = await fetch(`${this.baseUrl}/circuit-breakers`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error(`Failed to update breakers: ${res.status}`);
    return await res.json();
  }
}

export default AvoStudioApi;
