/**
 * Shared type definitions for AVOStudio
 * Mirrors the AgentWatch trace event schema (SQLite storage contract)
 * and the MCP trace server interface.
 *
 * @see hermes-avo/docs/trace-event-schema.md (single source of truth)
 */

// ─── Agent Lifecycle ───────────────────────────────────────────────

/**
 * AVO agent lifecycle states — mirrors AVOExecutionState in the engine.
 */
export type AgentStatus =
  | 'idle'
  | 'planning'
  | 'executing'
  | 'observing'
  | 'done'
  | 'failed';

/**
 * Uppercase enum-style status for the canonical AgentRecord type
 * (as used by the task spec).
 */
export type AgentRecordStatus =
  | 'PLANNING'
  | 'EXECUTING'
  | 'OBSERVING'
  | 'DONE'
  | 'FAILED';

/**
 * Color mapping for each agent status. Used by status badges and tree nodes.
 */
export const AGENT_STATUS_COLOR: Record<AgentStatus, string> = {
  idle: 'node-pending',
  planning: 'status-planning',
  executing: 'status-executing',
  observing: 'status-observing',
  done: 'status-done',
  failed: 'status-failed',
};

export interface AgentResourceUsage {
  /** Total input + output tokens consumed. */
  tokens: number;
  /** Estimated USD cost (cached per-token rate). */
  cost: number;
  /** Wall-clock CPU time in milliseconds. */
  cpuMs: number;
}

/**
 * Canonical agent record as specified in the task spec.
 * Uses uppercase status and camelCase resource fields.
 */
export interface AgentRecord {
  id: string;
  name: string;
  status: AgentRecordStatus;
  tokensUsed: number;
  costUsd: number;
  cpuMs: number;
}

/**
 * AVOAgent — internal representation used by the app's REST client.
 * Extends AgentRecord with runtime fields the UI tracks.
 */
export interface AVOAgent extends AgentRecord {
  status: AgentStatus;
  resources: AgentResourceUsage;
  currentPlanNode?: string;
  /** ISO timestamp of last activity. */
  lastSeen: string;
  /** Run ID this agent belongs to. */
  runId: string;
}

export interface AgentPlanNode {
  id: string;
  /** Human-readable goal description. */
  name: string;
  /** HTN sub-type: task / method / primitive. */
  type: 'task' | 'method' | 'primitive' | 'goal';
  /** Tree expansion — children are subtasks. */
  children: AgentPlanNode[];
  /** Current execution status. */
  status: 'pending' | 'running' | 'complete' | 'failed';
  /** When this node started executing (ISO). */
  startedAt?: string;
  /** When this node completed (ISO). */
  completedAt?: string;
  /** Tool calls made while executing this node. */
  toolCalls: ToolCall[];
}

/**
 * Canonical PlanNode type as specified in the task spec.
 * Uses lowercase statuses and includes parentId + observations.
 */
export interface PlanNode {
  id: string;
  parentId?: string | null;
  goal: string;
  status: 'pending' | 'executing' | 'done' | 'failed';
  toolCalls: ToolCall[];
  observations: string[];
}

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  /** Observation returned by the tool. */
  result?: string;
  startedAt: string;
  completedAt?: string;
  status: 'running' | 'complete' | 'error';
  error?: string;
}

export interface AgentTrace {
  agentId: string;
  /** Root plan tree for this agent. */
  plan: AgentPlanNode;
  /** Flat list of events for quick lookup. */
  events: TraceEvent[];
  /** Causal edges between events. */
  causalEdges: CausalEdge[];
}

/**
 * Trace event schema — compatible with AgentWatch's SQLite storage contract.
 * @see docs/trace-event-schema.md
 */
export type TraceEventType =
  | 'agent_step'
  | 'tool_call_started'
  | 'tool_call_completed'
  | 'checkpoint_created'
  | 'loop_detected';

export interface BaseTraceEvent {
  id: string;
  type: TraceEventType;
  agentId: string;
  timestamp: string;
  runId: string;
}

export interface AgentStepEvent extends BaseTraceEvent {
  type: 'agent_step';
  /** The agent's current status at this step. */
  status: AgentStatus;
  /** What the agent is thinking — its reasoning. */
  thought?: string;
  /** The action the agent decided to take. */
  action?: string;
}

export interface ToolCallStartedEvent extends BaseTraceEvent {
  type: 'tool_call_started';
  toolCallId: string;
  toolName: string;
  args: Record<string, unknown>;
  /** Parent node in the HTN plan. */
  parentNodeId?: string;
}

export interface ToolCallCompletedEvent extends BaseTraceEvent {
  type: 'tool_call_completed';
  toolCallId: string;
  toolName: string;
  result: string;
  status: 'success' | 'error';
  error?: string;
}

export interface CheckpointCreatedEvent extends BaseTraceEvent {
  type: 'checkpoint_created';
  checkpointId: string;
  /** Snapshot of the agent state at this checkpoint. */
  stateSummary: string;
}

export interface LoopDetectedEvent extends BaseTraceEvent {
  type: 'loop_detected';
  /** Number of repeated calls that triggered detection. */
  repeatCount: number;
  /** The repeated tool call signature. */
  toolName: string;
  argsHash: string;
}

export type TraceEvent =
  | AgentStepEvent
  | ToolCallStartedEvent
  | ToolCallCompletedEvent
  | CheckpointCreatedEvent
  | LoopDetectedEvent;

export interface CausalEdge {
  /** ID of the cause event. */
  causeEventId: string;
  /** ID of the effect event. */
  effectEventId: string;
  /** WHY relationship — e.g. "informed-by", "triggered-by", "consequence-of". */
  relation: string;
}

/**
 * Canonical TraceEvent with cause/decision/inputs/outputs fields
 * as specified in the task spec. This is a superset used for
 * detailed trace analysis.
 */
export interface TraceEventFull {
  id: string;
  timestamp: string;
  agentId: string;
  cause?: string;
  decision?: string;
  inputs?: Record<string, unknown>;
  outputs?: unknown;
}

// ─── Circuit Breakers ────────────────────────────────────────────────

export interface CircuitBreakerConfig {
  costCapUSD: number;
  stepBudget: number;
  timeoutSeconds: number;
  loopDetectionThreshold: number;
}

export const DEFAULT_CIRCUIT_BREAKERS: CircuitBreakerConfig = {
  costCapUSD: 0.5,
  stepBudget: 1000,
  timeoutSeconds: 30,
  loopDetectionThreshold: 3,
};

export interface CircuitBreakerState {
  config: CircuitBreakerConfig;
  currentCost: number;
  stepsConsumed: number;
  activeSince: string;
  /** true when any breaker has tripped. */
  tripped: boolean;
  trippedBreaker?: 'cost' | 'steps' | 'timeout' | 'loop' | null;
  trippedReason?: string;
}

/**
 * Canonical BreakerState type as specified in the task spec.
 */
export interface BreakerState {
  costCapUsd: number;
  stepBudget: number;
  callTimeoutSec: number;
  loopThreshold: number;
  tripped: boolean;
}

export const DEFAULT_BREAKER_STATE: BreakerState = {
  costCapUsd: 0.5,
  stepBudget: 1000,
  callTimeoutSec: 30,
  loopThreshold: 3,
  tripped: false,
};

// ─── Chat / Control ─────────────────────────────────────────────────

export type ChatCommand =
  | 'execute'
  | 'status'
  | 'cancel'
  | 'escalate';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  /** Parsed command if the message was a slash command. */
  command?: ChatCommand;
  /** The agent this command targets. */
  targetAgentId?: string;
  /** Raw argument string after the command. */
  args?: string;
}

/**
 * Canonical ChatMessage type as specified in the task spec.
 */
export interface ChatMessageRecord {
  role: 'user' | 'assistant' | 'system';
  agentId?: string;
  text: string;
  critique?: string;
  escalatedTo?: string;
}

export interface ChatEvent {
  type: 'message' | 'agent-response' | 'agent-stuck' | 'escalated';
  agentId?: string;
  message: string;
  timestamp: string;
}

// ─── API Response Shapes ────────────────────────────────────────────

export interface AgentsResponse {
  agents: AVOAgent[];
}

export interface PlansResponse {
  plan: AgentPlanNode;
}

export interface TracesResponse {
  trace: AgentTrace;
}

// ─── Index re-exports ─────────────────────────────────────────────────

export {
  AgentRecord as AgentRecordType,
  PlanNode as PlanNodeType,
  TraceEventFull as TraceEventTypeFull,
  BreakerState as BreakerStateType,
  ChatMessageRecord as ChatMessageRecordType,
};
