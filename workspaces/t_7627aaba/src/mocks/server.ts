/**
 * MSW test setup — intercepts fetch/XMLHttpRequest in the test environment.
 * Import this in tests/setup.ts or in individual test files.
 *
 * Usage:
 *   import { server } from './mocks/server';
 *   import { beforeAll, afterEach, afterAll } from 'vitest';
 *
 *   beforeAll(() => server.listen());
 *   afterEach(() => server.resetHandlers());
 *   afterAll(() => server.close());
 */
import { setupServer } from 'msw/node';
import { handlers, streamHandler } from './handlers';

export const server = setupServer(...handlers, streamHandler);
