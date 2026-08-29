/**
 * Zustand store — central state for AVOStudio.
 * Wraps the REST API + SSE client into a single reactive surface.
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import type {
  AVOAgent,
  AgentPlanNode,
  AgentTrace,
  TraceEvent,
  CircuitBreakerState,
  CircuitBreakerConfig,
  ChatMessage,
  ChatEvent,
} from '../types/trace';
import { DEFAULT_CIRCUIT_BREAKERS } from '../types/trace';
import type { AvoStudioApi } from './api';
import type { SseClientInterface } from './sse';

export interface StudioState {
  // Data
  agents: Record<string, AVOAgent>;
  activeAgentId: string | null;
  plans: Record<string, AgentPlanNode>;
  traces: Record<string, AgentTrace>;
  messages: ChatMessage[];
  chatEvents: ChatEvent[];
  circuitBreakers: CircuitBreakerState;

  // UI
  sseStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  isLoadingAgents: boolean;
  error: string | null;

  // Actions
  setAgents: (agents: AVOAgent[]) => void;
  updateAgent: (agent: Partial<AVOAgent> & { id: string }) => void;
  setSseStatus: (status: StudioState['sseStatus']) => void;
  setError: (error: string | null) => void;
  setLoadingAgents: (loading: boolean) => void;
  setActiveAgent: (agentId: string | null) => void;
  setPlan: (agentId: string, plan: AgentPlanNode) => void;
  setTrace: (agentId: string, trace: AgentTrace) => void;
  appendMessage: (message: ChatMessage) => void;
  appendChatEvent: (event: ChatEvent) => void;
  setCircuitBreakers: (state: CircuitBreakerState) => void;
  updateCircuitBreakerConfig: (config: Partial<CircuitBreakerConfig>) => void;

  // Async actions
  fetchAgents: (api: AvoStudioApi, runId?: string) => Promise<void>;
  fetchPlan: (api: AvoStudioApi, agentId: string) => Promise<void>;
  fetchTrace: (api: AvoStudioApi, agentId: string) => Promise<void>;
  sendChat: (api: AvoStudioApi, message: Omit<ChatMessage, 'id'>) => Promise<void>;
  updateBreakers: (
    api: AvoStudioApi,
    config: Partial<CircuitBreakerConfig>,
  ) => Promise<void>;
}

export const useStudioStore = create<StudioState>()(
  subscribeWithSelector(
    devtools((set, get) => ({
      // ── Data ──
      agents: {},
      activeAgentId: null,
      plans: {},
      traces: {},
      messages: [],
      chatEvents: [],
      circuitBreakers: {
        config: DEFAULT_CIRCUIT_BREAKERS,
        currentCost: 0,
        stepsConsumed: 0,
        activeSince: new Date().toISOString(),
        tripped: false,
        trippedBreaker: null,
        trippedReason: undefined,
      },

      // ── UI ──
      sseStatus: 'disconnected',
      isLoadingAgents: false,
      error: null,

      // ── Actions ──
      setAgents: (agents) =>
        set((s) => ({
          agents: Object.fromEntries(agents.map((a) => [a.id, a])),
        })),

      updateAgent: (agent) =>
        set((s) => ({
          agents: {
            ...s.agents,
            [agent.id]: { ...s.agents[agent.id], ...agent },
          },
        })),

      setSseStatus: (status) => set({ sseStatus: status }),
      setError: (error) => set({ error }),
      setLoadingAgents: (loading) => set({ isLoadingAgents: loading }),

      setActiveAgent: (agentId) => set({ activeAgentId: agentId }),

      setPlan: (agentId, plan) =>
        set((s) => ({ plans: { ...s.plans, [agentId]: plan } })),

      setTrace: (agentId, trace) =>
        set((s) => ({ traces: { ...s.traces, [agentId]: trace } })),

      appendMessage: (message) =>
        set((s) => ({ messages: [...s.messages, message] })),

      appendChatEvent: (event) =>
        set((s) => ({ chatEvents: [...s.chatEvents, event] })),

      setCircuitBreakers: (state) => set({ circuitBreakers: state }),

      updateCircuitBreakerConfig: (config) =>
        set((s) => ({
          circuitBreakers: {
            ...s.circuitBreakers,
            config: { ...s.circuitBreakers.config, ...config },
          },
        })),

      // ── Async actions ──
      fetchAgents: async (api, runId) => {
        set({ isLoadingAgents: true, error: null });
        try {
          const agents = await api.fetchAgents(runId);
          set((s) => ({
            agents: Object.fromEntries(agents.map((a) => [a.id, a])),
            isLoadingAgents: false,
          }));
        } catch (e) {
          set({ error: (e as Error).message, isLoadingAgents: false });
        }
      },

      fetchPlan: async (api, agentId) => {
        set({ error: null });
        try {
          const plan = await api.fetchPlan(agentId);
          set((s) => ({
            plans: { ...s.plans, [agentId]: plan },
          }));
        } catch (e) {
          set({ error: (e as Error).message });
        }
      },

      fetchTrace: async (api, agentId) => {
        set({ error: null });
        try {
          const trace = await api.fetchTrace(agentId);
          set((s) => ({
            traces: { ...s.traces, [agentId]: trace },
          }));
        } catch (e) {
          set({ error: (e as Error).message });
        }
      },

      sendChat: async (api, message) => {
        const fullMessage: ChatMessage = {
          ...message,
          id: crypto.randomUUID(),
        };
        get().appendMessage(fullMessage);
        try {
          const resp = await api.sendChatMessage(fullMessage);
          if (resp.reply) {
            get().appendMessage({
              id: crypto.randomUUID(),
              role: 'assistant',
              content: resp.reply,
              timestamp: new Date().toISOString(),
            });
          }
        } catch (e) {
          get().appendMessage({
            id: crypto.randomUUID(),
            role: 'system',
            content: `Error: ${(e as Error).message}`,
            timestamp: new Date().toISOString(),
          });
        }
      },

      updateBreakers: async (api, config) => {
        try {
          const updated = await api.updateCircuitBreakers(config);
          set((s) => ({
            circuitBreakers: {
              ...s.circuitBreakers,
              config: updated,
            },
          }));
        } catch (e) {
          set({ error: (e as Error).message });
        }
      },
    })),
  ),
);

/**
 * Process a trace event from the SSE stream and update the store.
 */
export function processTraceEvent(state: typeof useStudioStore, event: TraceEvent) {
  const { agentId } = event;

  // Update agent status for step events
  if (event.type === 'agent_step') {
    state.getState().updateAgent({
      id: agentId,
      status: event.status,
    });
  }

  // Track tool call state
  if (event.type === 'tool_call_started') {
    state.getState().updateAgent({
      id: agentId,
      status: 'executing',
    });
  }

  if (event.type === 'loop_detected') {
    state.getState().updateAgent({
      id: agentId,
      status: 'failed',
    });
  }

  // Update traces
  const existing = state.getState().traces[agentId];
  if (existing) {
    state.getState().setTrace(agentId, {
      ...existing,
      events: [...existing.events, event],
    });
  }
}
