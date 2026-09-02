import { useStore } from '../store/StoreProvider';
import { useEffect } from 'react';
import type { TraceEvent, CausalEdge, AgentTrace } from '../types/trace';
import { useStore as useStudioStore } from '../store/studioStore';
import { clsx } from 'clsx';

/**
 * Trace Graph View — Causality reconstruction of why agents made decisions.
 * Integrates with @agent-architect's langgraph-checkpointer events.
 * Exports to MCP trace server for cross-session analysis.
 */
export default function TraceGraphView() {
  const { traces, activeAgentId } = useStore();

  const trace: AgentTrace | undefined = activeAgentId
    ? traces[activeAgentId]
    : undefined;

  if (!trace) {
    return (
      <div className="p-8">
        <div className="card">
          <h2 className="mb-2 text-lg font-semibold text-avo-text">
            Trace Graph
          </h2>
          <p className="text-avo-text-muted">
            Select an agent to view its causal trace graph. This reconstructs
            WHY each decision was made, not just what happened.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-avo-text">
          Trace Graph — {trace.agentId}
        </h2>
        <button
          onClick={() => {
            // Export trace as JSON for MCP trace server consumption
            const blob = new Blob([JSON.stringify(trace, null, 2)], {
              type: 'application/json',
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `trace-${trace.agentId}.json`;
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="px-3 py-1 text-sm text-avo-text-muted hover:text-avo-text border border-avo-border rounded"
          data-testid="export-trace"
        >
          Export to MCP
        </button>
      </div>

      {trace.events.length === 0 && (
        <p className="text-avo-text-muted">No trace events recorded.</p>
      )}

      <div className="space-y-2">
        {trace.causalEdges.map((edge, i) => (
          <CausalEdgeView key={`${edge.causeEventId}-${edge.effectEventId}`} edge={edge} events={trace.events} />
        ))}
      </div>

      <div className="mt-6">
        <h3 className="mb-2 text-sm font-medium text-avo-text-muted">
          Event Timeline
        </h3>
        <EventTimeline events={trace.events} />
      </div>
    </div>
  );
}

interface CausalEdgeViewProps {
  edge: CausalEdge;
  events: TraceEvent[];
}

function CausalEdgeView({ edge, events }: CausalEdgeViewProps) {
  const causeEvent = events.find((e) => e.id === edge.causeEventId);
  const effectEvent = events.find((e) => e.id === edge.effectEventId);

  return (
    <div
      className="card space-y-1"
      data-testid="causal-edge"
    >
      <div className="text-xs text-avo-text-muted">
        Relation: <span className="text-avo-text">{edge.relation}</span>
      </div>
      <div className="text-sm">
        <span className="text-avo-text-muted">Cause:</span>{' '}
        <span data-testid="cause-event">{causeEvent?.type ?? 'unknown'}</span>
      </div>
      <div className="text-sm">
        <span className="text-avo-text-muted">Effect:</span>{' '}
        <span data-testid="effect-event">{effectEvent?.type ?? 'unknown'}</span>
      </div>
    </div>
  );
}

function EventTimeline({ events }: { events: TraceEvent[] }) {
  return (
    <div className="space-y-1" data-testid="event-timeline">
      {events.map((event) => (
        <EventRow key={event.id} event={event} />
      ))}
    </div>
  );
}

function EventRow({ event }: { event: TraceEvent }) {
  const eventColor: Record<TraceEvent['type'], string> = {
    agent_step: 'bg-amber-400',
    tool_call_started: 'bg-sky-400',
    tool_call_completed: 'bg-green-400',
    checkpoint_created: 'bg-violet-400',
    loop_detected: 'bg-red-400',
  };

  return (
    <div
      className="flex items-start gap-3 rounded px-3 py-2 text-sm"
      data-testid="event-row"
      data-event-type={event.type}
    >
      <div className="flex-shrink-0 pt-0.5">
        <div className={clsx('h-2 w-2 rounded-full', eventColor[event.type])} />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <code className="text-xs text-avo-text-muted">
            {event.type}
          </code>
          <span className="text-xs text-avo-text-muted">
            {new Date(event.timestamp).toLocaleTimeString()}
          </span>
        </div>
        <div className="mt-0.5 text-avo-text break-all">
          {formatEventContent(event)}
        </div>
      </div>
    </div>
  );
}

function formatEventContent(event: TraceEvent): string {
  switch (event.type) {
    case 'agent_step':
      return event.thought
        ? `${event.thought.slice(0, 80)}...`
        : `Status: ${event.status}`;
    case 'tool_call_started':
      return `${event.toolName}(${JSON.stringify(event.args).slice(0, 60)})`;
    case 'tool_call_completed':
      return `${event.toolName}: ${event.result.slice(0, 80)}`;
    case 'checkpoint_created':
      return `Checkpoint ${event.checkpointId}: ${event.stateSummary.slice(0, 80)}`;
    case 'loop_detected':
      return `Loop detected on ${event.toolName} (${event.repeatCount}x)`;
    default:
      return '';
  }
}
