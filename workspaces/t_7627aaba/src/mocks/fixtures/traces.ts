import type { AgentTrace, TraceEvent } from '../../types/trace';

// Sample trace events for MSW SSE stream and trace fixture
export const eventsFixture: TraceEvent[] = [
  {
    id: 'evt-001',
    type: 'agent_step',
    agentId: 'agent-001',
    timestamp: '2026-08-25T14:30:00Z',
    runId: 'run-2026-08-25-001',
    status: 'planning',
    thought: 'I need to understand the codebase before making changes.',
    action: 'Read source files for context',
  },
  {
    id: 'evt-002',
    type: 'tool_call_started',
    agentId: 'agent-001',
    timestamp: '2026-08-25T14:30:01Z',
    runId: 'run-2026-08-25-001',
    toolCallId: 'tc-001',
    toolName: 'read_file',
    args: { path: '/src/types/trace.ts' },
  },
  {
    id: 'evt-003',
    type: 'tool_call_completed',
    agentId: 'agent-001',
    timestamp: '2026-08-25T14:30:02Z',
    runId: 'run-2026-08-25-001',
    toolCallId: 'tc-001',
    toolName: 'read_file',
    result: 'File contents loaded successfully',
    status: 'success',
  },
  {
    id: 'evt-004',
    type: 'checkpoint_created',
    agentId: 'agent-001',
    timestamp: '2026-08-25T14:30:03Z',
    runId: 'run-2026-08-25-001',
    checkpointId: 'ckpt-001',
    stateSummary: 'Agent has read trace type definitions and parsed the schema.',
  },
  {
    id: 'evt-005',
    type: 'agent_step',
    agentId: 'agent-001',
    timestamp: '2026-08-25T14:30:04Z',
    runId: 'run-2026-08-25-001',
    status: 'executing',
    thought: 'Now I will implement the useAgentStream hook with auto-reconnect.',
    action: 'Write SSE hook module',
  },
  {
    id: 'evt-006',
    type: 'loop_detected',
    agentId: 'agent-002',
    timestamp: '2026-08-25T14:31:00Z',
    runId: 'run-2026-08-25-001',
    repeatCount: 3,
    toolName: 'shell_exec',
    argsHash: 'a1b2c3d4',
  },
];

// Full trace fixture with causal edges
export const traceFixture: AgentTrace = {
  agentId: 'agent-001',
  plan: {
    id: 'node-root',
    name: 'Build AVOStudio orchestration dashboard',
    type: 'goal',
    status: 'running',
    children: [],
    toolCalls: [],
  },
  events: eventsFixture,
  causalEdges: [
    {
      causeEventId: 'evt-001',
      effectEventId: 'evt-002',
      relation: 'triggered-by',
    },
    {
      causeEventId: 'evt-003',
      effectEventId: 'evt-004',
      relation: 'informed-by',
    },
    {
      causeEventId: 'evt-004',
      effectEventId: 'evt-005',
      relation: 'consequence-of',
    },
  ],
};
