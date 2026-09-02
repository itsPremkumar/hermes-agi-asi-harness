import type { AgentPlanNode, ToolCall } from '../../types/trace';

// Sample tool calls for the plan fixture
const toolCalls: ToolCall[] = [
  {
    id: 'call-1',
    name: 'read_file',
    args: { path: '/src/App.tsx' },
    result: 'File contents loaded successfully',
    startedAt: '2026-08-25T14:28:01Z',
    completedAt: '2026-08-25T14:28:02Z',
    status: 'complete',
  },
  {
    id: 'call-2',
    name: 'search_code',
    args: { pattern: 'useAgentStream' },
    result: 'Found 3 matches in 2 files',
    startedAt: '2026-08-25T14:28:03Z',
    completedAt: '2026-08-25T14:28:04Z',
    status: 'complete',
  },
  {
    id: 'call-3',
    name: 'shell_exec',
    args: { command: 'npm test' },
    startedAt: '2026-08-25T14:28:05Z',
    status: 'running',
  },
];

// A nested plan tree fixture for PlanVisualization
export const planFixture: AgentPlanNode = {
  id: 'node-root',
  name: 'Build AVOStudio orchestration dashboard',
  type: 'goal',
  status: 'running',
  startedAt: '2026-08-25T14:25:00Z',
  children: [
    {
      id: 'node-1',
      name: 'Scaffold project structure',
      type: 'task',
      status: 'complete',
      startedAt: '2026-08-25T14:25:00Z',
      completedAt: '2026-08-25T14:26:00Z',
      toolCalls: [toolCalls[0], toolCalls[1]],
      children: [],
    },
    {
      id: 'node-2',
      name: 'Define domain types',
      type: 'task',
      status: 'complete',
      startedAt: '2026-08-25T14:26:00Z',
      completedAt: '2026-08-25T14:27:00Z',
      toolCalls: [toolCalls[0]],
      children: [],
    },
    {
      id: 'node-3',
      name: 'Implement REST + SSE clients',
      type: 'task',
      status: 'running',
      startedAt: '2026-08-25T14:27:00Z',
      toolCalls: [toolCalls[2]],
      children: [
        {
          id: 'node-3a',
          name: 'Build typed REST client',
          type: 'method',
          status: 'complete',
          startedAt: '2026-08-25T14:27:00Z',
          completedAt: '2026-08-25T14:27:30Z',
          toolCalls: [],
          children: [],
        },
        {
          id: 'node-3b',
          name: 'Add SSE auto-reconnect hook',
          type: 'method',
          status: 'running',
          startedAt: '2026-08-25T14:27:30Z',
          toolCalls: [],
          children: [],
        },
      ],
    },
    {
      id: 'node-4',
      name: 'Set up MSW mock server',
      type: 'task',
      status: 'pending',
      toolCalls: [],
      children: [],
    },
  ],
};
