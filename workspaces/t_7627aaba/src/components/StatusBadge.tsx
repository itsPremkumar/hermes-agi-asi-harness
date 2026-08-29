import { clsx } from 'clsx';
import { AgentStatus } from '../types/trace';
import { AGENT_STATUS_COLOR } from '../types/trace';

export const STATUS_LABELS: Record<AgentStatus, string> = {
  idle: 'Idle',
  planning: 'Planning',
  executing: 'Executing',
  observing: 'Observing',
  done: 'Done',
  failed: 'Failed',
};

interface StatusBadgeProps {
  status: AgentStatus;
  className?: string;
}

/**
 * Reusable status badge used across AgentGrid, PlanTree, and Chat.
 */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  const colorClass = AGENT_STATUS_COLOR[status];
  return (
    <span
      className={clsx(
        'status-badge',
        className,
        status === 'done' && 'bg-green-900/30 text-green-400',
        status === 'failed' && 'bg-red-900/30 text-red-400',
        status === 'planning' && 'bg-amber-900/30 text-amber-400',
        status === 'executing' && 'bg-sky-900/30 text-sky-400',
        status === 'observing' && 'bg-violet-900/30 text-violet-400',
        status === 'idle' && 'bg-slate-800 text-slate-400',
      )}
      data-testid="status-badge"
      data-status={status}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
