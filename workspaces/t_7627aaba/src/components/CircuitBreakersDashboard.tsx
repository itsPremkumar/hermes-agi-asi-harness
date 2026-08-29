import { useStore, useStoreContext } from '../store/StoreProvider';
import { DEFAULT_CIRCUIT_BREAKERS } from '../types/trace';
import type { CircuitBreakerConfig, CircuitBreakerState } from '../types/trace';
import { clsx } from 'clsx';
import { useState } from 'react';

/**
 * Circuit Breakers Dashboard.
 * Controls cost, step, timeout, and loop-detection budgets.
 * - Cost: $0.50 budget cap per run (configurable)
 * - Steps: 1000-step budget (prevent runaway)
 * - Time: 30s-per-call timeout (configurable)
 * - Loop detection: 3 identical calls → auto-interrupt
 */
export default function CircuitBreakersDashboard() {
  const { circuitBreakers, updateBreakers } = useStore();
  const { api } = useStoreContext();
  const [isEditing, setIsEditing] = useState(false);
  const [draftConfig, setDraftConfig] = useState<CircuitBreakerConfig>({
    ...circuitBreakers.config,
  });

  const handleSave = async () => {
    await updateBreakers(api, draftConfig);
    setIsEditing(false);
  };

  const handleReset = () => {
    setDraftConfig(DEFAULT_CIRCUIT_BREAKERS);
  };

  const costPercent = (circuitBreakers.currentCost / circuitBreakers.config.costCapUSD) * 100;
  const stepPercent = (circuitBreakers.stepsConsumed / circuitBreakers.config.stepBudget) * 100;

  const isTripped = circuitBreakers.tripped;

  return (
    <div className="p-4">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-avo-text">
          Circuit Breakers
        </h1>
        {isTripped && (
          <span
            className="text-xs font-medium text-red-400"
            data-testid="tripped-badge"
          >
            TRIPPED: {circuitBreakers.trippedBreaker} — {circuitBreakers.trippedReason}
          </span>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Cost Cap */}
        <BreakerCard
          title="Cost Cap"
          icon="💰"
          currentValue={circuitBreakers.currentCost}
          maxValue={circuitBreakers.config.costCapUSD}
          unit="$"
          percent={costPercent}
          status={circuitBreakers.trippedBreaker === 'cost' ? 'tripped' : 'ok'}
          isEditing={isEditing}
          draftValue={draftConfig.costCapUSD}
          onDraftChange={(v) =>
            setDraftConfig({ ...draftConfig, costCapUSD: v })
          }
          data-testid="breaker-cost"
        />

        {/* Step Budget */}
        <BreakerCard
          title="Step Budget"
          icon="📊"
          currentValue={circuitBreakers.stepsConsumed}
          maxValue={circuitBreakers.config.stepBudget}
          unit=""
          percent={stepPercent}
          status={circuitBreakers.trippedBreaker === 'steps' ? 'tripped' : 'ok'}
          isEditing={isEditing}
          draftValue={draftConfig.stepBudget}
          onDraftChange={(v) =>
            setDraftConfig({ ...draftConfig, stepBudget: v })
          }
          data-testid="breaker-steps"
        />

        {/* Timeout */}
        <BreakerCard
          title="Call Timeout"
          icon="⏱️"
          currentValue={circuitBreakers.config.timeoutSeconds}
          maxValue={60}
          unit="s"
          percent={(circuitBreakers.config.timeoutSeconds / 60) * 100}
          status="configured"
          isEditing={isEditing}
          draftValue={circuitBreakers.config.timeoutSeconds}
          onDraftChange={(v) =>
            setDraftConfig({ ...draftConfig, timeoutSeconds: v })
          }
          data-testid="breaker-timeout"
        />

        {/* Loop Detection */}
        <BreakerCard
          title="Loop Detection"
          icon="🔄"
          currentValue={circuitBreakers.config.loopDetectionThreshold}
          maxValue={10}
          unit="x"
          percent={(circuitBreakers.config.loopDetectionThreshold / 10) * 100}
          status="configured"
          isEditing={isEditing}
          draftValue={circuitBreakers.config.loopDetectionThreshold}
          onDraftChange={(v) =>
            setDraftConfig({ ...draftConfig, loopDetectionThreshold: v })
          }
          data-testid="breaker-loop"
        />
      </div>

      {/* Controls */}
      <div className="mt-6 flex gap-2">
        {!isEditing ? (
          <button
            onClick={() => setIsEditing(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm"
            data-testid="edit-button"
          >
            Edit Configuration
          </button>
        ) : (
          <>
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded text-sm"
              data-testid="save-button"
            >
              Save
            </button>
            <button
              onClick={handleReset}
              className="px-4 py-2 bg-avo-surface hover:bg-avo-border text-avo-text rounded text-sm border border-avo-border"
              data-testid="reset-button"
            >
              Reset to Defaults
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="px-4 py-2 text-avo-text-muted hover:text-avo-text rounded text-sm"
              data-testid="cancel-button"
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
}

interface BreakerCardProps {
  title: string;
  icon: string;
  currentValue: number;
  maxValue: number;
  unit: string;
  percent: number;
  status: 'ok' | 'tripped' | 'configured';
  isEditing: boolean;
  draftValue: number;
  onDraftChange: (value: number) => void;
}

function BreakerCard({
  title,
  icon,
  currentValue,
  maxValue,
  unit,
  percent,
  status,
  isEditing,
  draftValue,
  onDraftChange,
}: BreakerCardProps) {
  const isTripped = status === 'tripped';
  const progressBarColor = isTripped
    ? 'bg-red-500'
    : status === 'ok'
    ? 'bg-sky-400'
    : 'bg-slate-500';

  return (
    <div
      className="card"
      data-testid={`breaker-card-${title.toLowerCase().replace(/\s/g, '-')}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-medium text-avo-text">{title}</h3>
        <span className="text-xl">{icon}</span>
      </div>

      <div className="mb-2 text-2xl font-bold text-avo-text">
        {currentValue}
        {unit}
        <span className="text-sm font-normal text-avo-text-muted">
          {' '}
          / {isEditing ? draftValue : maxValue}
          {unit}
        </span>
      </div>

      {!isEditing && (
        <>
          <div className="h-2 w-full rounded-full bg-slate-800">
            <div
              className={clsx('h-2 rounded-full transition-all', progressBarColor)}
              style={{ width: `${Math.min(percent, 100)}%` }}
              data-testid={`progress-${title.toLowerCase().replace(/\s/g, '-')}`}
            />
          </div>
          {isTripped && (
            <p className="mt-1 text-xs text-red-400">
              BREAKER TRIPPED
            </p>
          )}
        </>
      )}

      {isEditing && (
        <input
          type="number"
          value={draftValue}
          onChange={(e) => onDraftChange(Number(e.target.value))}
          className="w-full bg-avo-bg border border-avo-border rounded px-2 py-1 text-sm text-avo-text focus:outline-none focus:ring-1 focus:ring-blue-500"
          data-testid={`config-${title.toLowerCase().replace(/\s/g, '-')}`}
        />
      )}
    </div>
  );
}
