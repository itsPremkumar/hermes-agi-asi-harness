import { useStore, useStoreContext } from '../store/StoreProvider';
import { StatusBadge } from '../components/StatusBadge';
import { useStore as useStudioStore } from '../store/studioStore';
import type { AVOAgent } from '../types/trace';
import { clsx } from 'clsx';
import { Link } from 'react-router-dom';

/**
 * Agent Grid View — Live canvas showing all running AVO agents.
 * Shows real-time status, resource usage (tokens, cost, CPU),
 * and click-to-inspect for plan + trace.
 */
export default function AgentGridView() {
  const { agents, activeAgentId, setActiveAgent, isLoadingAgents, error } =
    useStore();
  const { api } = useStoreContext();

  const agentList = Object.values(agents);

  if (isLoadingAgents && agentList.length === 0) {
    return (
      <div className="p-8">
        <div className="text-avo-text-muted">Loading agents...</div>
      </div>
    );
  }

  if (error && agentList.length === 0) {
    return (
      <div className="p-8">
        <div className="text-red-400">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-avo-text">Running Agents</h1>
        <div className="text-sm text-avo-text-muted">
          {agentList.length} agent{agentList.length === 1 ? '' : 's'}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {agentList.map((agent) => (
          <AgentCard
            key={agent.id}
            agent={agent}
            isActive={activeAgentId === agent.id}
            onSelect={() => {
              setActiveAgent(agent.id);
              useStudioStore.getState().fetchPlan(api, agent.id);
              useStudioStore.getState().fetchTrace(api, agent.id);
            }}
          />
        ))}
      </div>

      {agentList.length === 0 && !isLoadingAgents && (
        <div className="py-12 text-center text-avo-text-muted">
          No agents running. Start an AVO session to see agents here.
        </div>
      )}
    </div>
  );
}

interface AgentCardProps {
  agent: AVOAgent;
  isActive: boolean;
  onSelect: () => void;
}

function AgentCard({ agent, isActive, onSelect }: AgentCardProps) {
  const { resources, status, name } = agent;

  return (
    <Link
      to={`/agent/${agent.id}`}
      className={clsx(
        'card cursor-pointer transition-all duration-200 hover:border-blue-500',
        isActive && 'ring-2 ring-blue-500',
      )}
      onClick={onSelect}
      data-testid="agent-card"
    >
      <div className="mb-3 flex items-start justify-between">
        <h3 className="font-medium text-avo-text">{name}</h3>
        <StatusBadge status={status} />
      </div>

      <div className="space-y-2 text-sm">
        <ResourceRow
          label="Tokens"
          value={resources.tokens.toLocaleString()}
          unit=""
          color="text-sky-400"
        />
        <ResourceRow
          label="Cost"
          value={`$${resources.cost.toFixed(3)}`}
          unit=""
          color="text-amber-400"
        />
        <ResourceRow
          label="CPU"
          value={resources.cpuMs}
          unit="ms"
          color="text-violet-400"
        />
      </div>

      <div
        className="mt-2 h-1 w-full rounded-full"
        data-testid="progress-bar"
        style={{
          backgroundColor: 'var(--tw-colors-avo-border)',
        }}
      >
        <div
          className="h-1 rounded-full"
          style={{
            width: `${Math.min((resources.cost / 0.5) * 100, 100)}%`,
            backgroundColor: status === 'failed' ? '#f87171' : '#38bdf8',
          }}
        />
      </div>
    </Link>
  );
}

function ResourceRow({
  label,
  value,
  unit,
  color,
}: {
  label: string;
  value: string | number;
  unit: string;
  color: string;
}) {
  return (
    <div className="flex justify-between">
      <span className="text-avo-text-muted">{label}</span>
      <span className={clsx('font-mono', color)}>
        {value}
        {unit}
      </span>
    </div>
  );
}
