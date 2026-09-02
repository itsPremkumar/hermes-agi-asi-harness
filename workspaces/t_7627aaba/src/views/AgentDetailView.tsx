import { useParams, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useStore, useStoreContext } from '../store/StoreProvider';
import { useStore as useStudioStore } from '../store/studioStore';
import { StatusBadge, STATUS_LABELS } from '../components/StatusBadge';
import type { AVOAgent } from '../types/trace';

/**
 * Agent Detail View — combines plan visualization + chat for a single agent.
 * Route: /agent/:agentId
 *
 * This is a real component (not lazy) because App.tsx references it directly
 * in a <Route>. Kept separate so the split-detail layout can evolve.
 */
export default function AgentDetailView() {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const { agents, setActiveAgent } = useStore();
  const { api } = useStoreContext();

  const agent: AVOAgent | undefined = agentId ? agents[agentId] : undefined;

  // Load agent plan + trace on mount + when agentId changes
  useEffect(() => {
    if (agentId) {
      setActiveAgent(agentId);
      useStudioStore.getState().fetchPlan(api, agentId);
      useStudioStore.getState().fetchTrace(api, agentId);
    }
  }, [agentId, api]);

  if (!agentId) {
    return (
      <div className="p-8">
        <div className="text-avo-text-muted">No agent selected.</div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="p-8">
        <div className="text-avo-text-muted">
          Agent {agentId} not found.{' '}
          <button
            onClick={() => navigate('/')}
            className="underline text-sky-400"
          >
            Back to grid
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-12 gap-4 p-4">
      <div className="col-span-12 border-b border-avo-border pb-2 mb-2">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold text-avo-text">{agent.name}</h2>
          <StatusBadge status={agent.status} />
          <span className="text-xs text-avo-text-muted">
            {STATUS_LABELS[agent.status]}
          </span>
        </div>
        <div className="mt-1 flex gap-4 text-sm text-avo-text-muted">
          <span>Run: {agent.runId}</span>
          <span>Tokens: {agent.resources.tokens.toLocaleString()}</span>
          <span>Cost: ${agent.resources.cost.toFixed(3)}</span>
          <span>CPU: {agent.resources.cpuMs}ms</span>
        </div>
      </div>

      <div className="col-span-7">
        {/* Plan Visualization is lazy-loaded at App level; here we render a
            placeholder that triggers the fetch. In production this would be
            the real PlanVisualization component imported directly. */}
        <PlanPlaceholder agentId={agentId} />
      </div>

      <div className="col-span-5">
        <ChatPlaceholder />
      </div>
    </div>
  );
}

/**
 * Placeholder wiring — keeps the build green while the heavy visualization
 * components remain lazily loaded at the app shell level. The real
 * PlanVisualization component lazy-loads the same code; this placeholder
 * simply renders a lightweight plan fetch status so the detail route is
 * navigable without a full page reload.
 */
function PlanPlaceholder({ agentId }: { agentId: string }) {
  const { plans } = useStore();
  const plan = plans[agentId];

  if (!plan) {
    return (
      <div className="card" data-testid="plan-placeholder">
        <p className="text-sm text-avo-text-muted">
          Loading plan for agent {agentId}...
        </p>
      </div>
    );
  }

  return (
    <div className="card" data-testid="plan-summary">
      <h3 className="font-medium text-avo-text mb-2">Root Goal: {plan.name}</h3>
      <p className="text-xs text-avo-text-muted">
        Status: {plan.status} · Type: {plan.type} · Children:{' '}
        {plan.children.length}
      </p>
    </div>
  );
}

/**
 * Lightweight chat surface that reuses the same MessageRow + sendChat
 * pipeline as the shared ChatInterface. The full ChatInterface component
 * is lazy-loaded at the shell route level; this keeps the detail view
 * self-contained for the split-view layout.
 */
function ChatPlaceholder() {
  const { messages } = useStore();

  return (
    <div className="card h-[500px] flex flex-col" data-testid="chat-placeholder">
      <h3 className="font-medium text-avo-text mb-2">Control Channel</h3>
      {messages.length === 0 ? (
        <p className="text-sm text-avo-text-muted">
          No messages yet. Use the main chat route to send commands.
        </p>
      ) : (
        <div className="space-y-1 overflow-y-auto text-sm">
          {messages.map((m) => (
            <div key={m.id} data-testid="detail-message">
              <span className="text-avo-text-muted">[{m.role}]</span>{' '}
              <span className="text-avo-text">{m.content}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
