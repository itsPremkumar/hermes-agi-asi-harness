import { createContext, useContext, ReactNode, useEffect, useRef } from 'react';
import { useStudioStore, processTraceEvent } from './studioStore';
import type { AvoStudioApi } from '../lib/api';
import { AvoStudioApi as ApiClass } from '../lib/api';
import { SseClient } from '../lib/sse';
import type { SseClientInterface } from '../lib/sse';
import type { TraceEvent } from '../types/trace';

interface StoreContextValue {
  api: AvoStudioApi;
  sse: SseClientInterface;
}

const StoreContext = createContext<StoreContextValue | null>(null);

export const useStore = useStudioStore;

export function StoreProvider({ children }: { children: ReactNode }) {
  const apiRef = useRef<AvoStudioApi>();
  const sseRef = useRef<SseClientInterface>();

  if (!apiRef.current) {
    apiRef.current = new ApiClass();
  }

  if (!sseRef.current) {
    sseRef.current = new SseClient({ url: '/stream' });
  }

  const api = apiRef.current;
  const sse = sseRef.current;

  useEffect(() => {
    sse.connect();

    const handleEvent = (event: TraceEvent) => {
      processTraceEvent(useStudioStore, event);
    };

    const unsub = sse.subscribe(handleEvent);

    return () => {
      unsub();
      sse.disconnect();
    };
  }, [sse]);

  return (
    <StoreContext.Provider value={{ api, sse }}>
      {children}
    </StoreContext.Provider>
  );
}

export function useStoreContext() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStoreContext must be used within StoreProvider');
  return ctx;
}
