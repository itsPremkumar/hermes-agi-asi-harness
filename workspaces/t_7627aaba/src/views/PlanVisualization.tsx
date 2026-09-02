import { useState, useEffect } from 'react';
import { useStore, useStoreContext } from '../store/StoreProvider';
import { clsx } from 'clsx';
import type { AgentPlanNode, ToolCall } from '../types/trace';
import { AGENT_STATUS_COLOR } from '../types/trace';

/**
 * Plan Visualization — Collapsible HTN tree explorer.
 * Color-coded by status (pending/executing/done/failed).
 * Click any node → show tool calls + observations.
 */
export default function PlanVisualization() {
  const { plans, activeAgentId } = useStore();
  const { api } = useStoreContext();

  const plan = activeAgentId ? plans[activeAgentId] : undefined;

  useEffect(() => {
    if (activeAgentId && !plan) {
      useStore.getState().fetchPlan(api, activeAgentId);
    }
  }, [activeAgentId, plan, api]);

  if (!plan) {
    return (
      <div className="card m-4">
        <p className="text-avo-text-muted">
          Select an agent to view its plan.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-avo-text">Plan</h2>
        <p className="text-sm text-avo-text-muted">
          Root: {plan.name} · HTN tree decomposition
        </p>
      </div>

      <TreeNode node={plan} level={0} />
    </div>
  );
}

interface TreeNodeProps {
  node: AgentPlanNode;
  level: number;
}

function TreeNode({ node, level }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(true);
  const [showDetails, setShowDetails] = useState(false);
  const hasChildren = node.children.length > 0;
  const statusColor = AGENT_STATUS_COLOR[node.status === 'running' ? 'executing' : node.status === 'complete' ? 'done' : node.status === 'failed' ? 'failed' : 'planning'];

  const statusLabel = {
    pending: 'Pending',
    running: 'Running',
    complete: 'Complete',
    failed: 'Failed',
  }[node.status];

  return (
    <div
      className="relative border-l border-avo-border pl-4"
      data-testid="tree-node"
      data-node-id={node.id}
      data-status={node.status}
    >
      <div className="relative">
        <div
          className={clsx(
            'mb-1 flex items-center gap-2 rounded px-3 py-2 transition-colors',
            node.status === 'complete' && 'bg-green-900/10',
            node.status === 'running' && 'bg-sky-900/10',
            node.status === 'failed' && 'bg-red-900/10',
            node.status === 'pending' && 'bg-slate-800/20',
          )}
          style={{ marginLeft: `${level * 1.5}rem` }}
        >
          {hasChildren && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-avo-text-muted hover:text-avo-text"
              data-testid={`toggle-${node.id}`}
              aria-label={expanded ? 'Collapse' : 'Expand'}
            >
              {expanded ? '▼' : '▶'}
            </button>
          )}
          {!hasChildren && <div className="w-4" />}

          <span
            className={clsx(
              'text-xs font-medium',
              statusColor === 'status-done' && 'text-green-400',
              statusColor === 'status-executing' && 'text-sky-400',
              statusColor === 'status-failed' && 'text-red-400',
              statusColor === 'status-planning' && 'text-amber-400',
            )}
            data-testid="node-status"
          >
            ● {statusLabel}
          </span>

          <span className="text-avo-text">{node.name}</span>
          <span className="text-xs text-avo-text-muted">
            ({node.type})
          </span>

          {node.toolCalls.length > 0 && (
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="ml-auto text-xs text-avo-text-muted hover:text-avo-text"
              data-testid={`details-${node.id}`}
              aria-label="Toggle tool calls"
            >
              {showDetails ? '▲' : '▼'} Tools ({node.toolCalls.length})
            </button>
          )}
        </div>

        {showDetails && (
          <ToolCallDetails calls={node.toolCalls} />
        )}

        {expanded && hasChildren && (
          <div className="ml-2 border-l border-avo-border">
            {node.children.map((child) => (
              <TreeNode
                key={child.id}
                node={child}
                level={level + 1}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolCallDetails({ calls }: { calls: ToolCall[] }) {
  return (
    <div
      className="mb-2 border-l border-avo-border pl-4"
      data-testid="tool-call-details"
    >
      {calls.map((call) => (
        <div key={call.id} className="mb-2 py-2">
          <div className="flex items-center gap-2">
            <code className="text-sm text-sky-400">tool:</code>
            <span className="font-mono text-sm text-avo-text">
              {call.name}
            </span>
            <span
              className="text-xs"
              data-testid={`tool-status-${call.id}`}
            >
              {call.status === 'running' && '⏳ Running'}
              {call.status === 'complete' && '✓ Done'}
              {call.status === 'error' && '✗ Error'}
            </span>
          </div>
          {call.args && (
            <pre className="mt-1 overflow-x-auto text-xs text-avo-text-muted">
              {JSON.stringify(call.args, null, 2)}
            </pre>
          )}
          {call.result && (
            <pre className="mt-1 overflow-x-auto text-xs text-avo-text-muted bg-avo-bg/30 p-2 rounded">
              {call.result}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}
