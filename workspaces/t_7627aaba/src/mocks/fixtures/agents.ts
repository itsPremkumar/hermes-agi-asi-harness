import type { AVOAgent } from '../../types/trace';

// Realistic sample agents for MSW mock server
export const agentsFixture: AVOAgent[] = [
  {
    id: 'agent-001',
    name: 'PlannerAgent',
    status: 'planning',
    resources: { tokens: 1250, cost: 0.18, cpuMs: 340 },
    lastSeen: '2026-08-25T14:30:00Z',
    runId: 'run-2026-08-25-001',
    currentPlanNode: 'node-1',
  },
  {
    id: 'agent-002',
    name: 'ExecutorAgent',
    status: 'executing',
    resources: { tokens: 8900, cost: 0.42, cpuMs: 1200 },
    lastSeen: '2026-08-25T14:31:00Z',
    runId: 'run-2026-08-25-001',
    currentPlanNode: 'node-3',
  },
  {
    id: 'agent-003',
    name: 'ObserverAgent',
    status: 'observing',
    resources: { tokens: 3400, cost: 0.28, cpuMs: 560 },
    lastSeen: '2026-08-25T14:29:00Z',
    runId: 'run-2026-08-25-001',
    currentPlanNode: 'node-7',
  },
  {
    id: 'agent-004',
    name: 'CodeReviewAgent',
    status: 'done',
    resources: { tokens: 15000, cost: 0.85, cpuMs: 2300 },
    lastSeen: '2026-08-25T14:20:00Z',
    runId: 'run-2026-08-25-001',
    currentPlanNode: undefined,
  },
  {
    id: 'agent-005',
    name: 'DebugAgent',
    status: 'failed',
    resources: { tokens: 5400, cost: 0.31, cpuMs: 890 },
    lastSeen: '2026-08-25T14:28:00Z',
    runId: 'run-2026-08-25-001',
    currentPlanNode: 'node-failed',
  },
];
