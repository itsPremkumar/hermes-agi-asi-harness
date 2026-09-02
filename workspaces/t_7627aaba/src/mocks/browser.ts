/**
 * MSW browser setup — import this in dev mode to intercept network requests
 * with the mock service worker.
 *
 * Usage in main.tsx (dev-only):
 *   if (import.meta.env.DEV) {
 *     import('./mocks/browser').then(({ startMockServiceWorker }) =>
 *       startMockServiceWorker()
 *     );
 *   }
 */
import { setupWorker } from 'msw/browser';
import { handlers, streamHandler } from './handlers';

export const worker = setupWorker(...handlers, streamHandler);

export function startMockServiceWorker() {
  return worker.start({
    onUnhandledRequest: 'bypass',
  });
}
