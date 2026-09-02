import { useStore, useStoreContext } from '../store/StoreProvider';
import { clsx } from 'clsx';
import { useEffect } from 'react';

/**
 * Shows SSE connection status in the header bar.
 * Pulses red when disconnected/error, green when connected.
 */
export function ConnectionStatus() {
  const { api, sse } = useStoreContext();
  const { sseStatus, error, fetchAgents } = useStore();

  useEffect(() => {
    fetchAgents(api);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dotClass = {
    disconnected: 'bg-red-500',
    connecting: 'bg-yellow-400 animate-pulse',
    connected: 'bg-green-500',
    error: 'bg-red-500 animate-pulse',
  }[sseStatus];

  return (
    <div className="flex items-center space-x-3 text-sm">
      <div className="flex items-center space-x-1">
        <div className={clsx('h-2 w-2 rounded-full', dotClass)} />
        <span className="text-avo-text-muted">
          {sseStatus === 'connected'
            ? 'Connected'
            : sseStatus === 'connecting'
            ? 'Connecting...'
            : 'Disconnected'}
        </span>
      </div>
      {error && (
        <span className="text-xs text-red-400" title={error}>
          {error.slice(0, 40)}...
        </span>
      )}
    </div>
  );
}
