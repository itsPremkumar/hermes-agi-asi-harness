/**
 * MSW request handlers for the AVOStudio mock API.
 * Intercepts REST endpoints and the SSE /stream endpoint.
 *
 * @see src/mocks/browser.ts  (browser/worker setup)
 * @see src/mocks/server.ts   (test/node setup)
 * @see src/mocks/fixtures/   (realistic sample data)
 */
import { http, HttpResponse } from 'msw';
import type {
  AVOAgent,
  AgentPlanNode,
  AgentTrace,
  CircuitBreakerConfig,
  TraceEvent,
} from '../types/trace';
import { agentsFixture } from './fixtures/agents';
import { planFixture } from './fixtures/plan';
import { traceFixture, eventsFixture } from './fixtures/traces';

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

const API = '/api';

export const handlers = [
  // GET /api/agents
  http.get(`${API}/agents`, async () => {
    await delay(50);
    return HttpResponse.json({ agents: agentsFixture });
  }),

  // GET /api/agents/:id
  http.get(`${API}/agents/:id`, async ({ params }) => {
    await delay(30);
    const agent = agentsFixture.find((a) => a.id === params.id);
    if (!agent) {
      return HttpResponse.json({ error: 'Agent not found' }, { status: 404 });
    }
    return HttpResponse.json({ agent });
  }),

  // GET /api/plans/:agentId
  http.get(`${API}/plans/:agentId`, async () => {
    await delay(80);
    return HttpResponse.json({ plan: planFixture });
  }),

  // GET /api/traces/:agentId
  http.get(`${API}/traces/:agentId`, async () => {
    await delay(60);
    return HttpResponse.json({ trace: traceFixture });
  }),

  // POST /api/chat
  http.post(`${API}/chat`, async ({ request }) => {
    const body = await request.json();
    await delay(120);
    return HttpResponse.json({
      ok: true,
      reply: `Acknowledged: ${JSON.stringify(body)}`,
    });
  }),

  // GET /api/circuit-breakers
  http.get(`${API}/circuit-breakers`, async () => {
    await delay(30);
    const config: CircuitBreakerConfig = {
      costCapUSD: 0.5,
      stepBudget: 1000,
      timeoutSeconds: 30,
      loopDetectionThreshold: 3,
    };
    return HttpResponse.json(config);
  }),

  // PUT /api/circuit-breakers
  http.put(`${API}/circuit-breakers`, async ({ request }) => {
    const updates = (await request.json()) as Partial<CircuitBreakerConfig>;
    await delay(50);
    return HttpResponse.json({
      costCapUSD: updates.costCapUSD ?? 0.5,
      stepBudget: updates.stepBudget ?? 1000,
      timeoutSeconds: updates.timeoutSeconds ?? 30,
      loopDetectionThreshold: updates.loopDetectionThreshold ?? 3,
    });
  }),
];

// SSE endpoint — returns a stream of trace events on /stream
export const streamHandler = http.get(`${API.replace('/api', '')}/stream`, async () => {
  const stream = new TransformStream();
  const writer = stream.writable.getWriter();
  const encoder = new TextEncoder();

  let i = 0;
  const interval = setInterval(() => {
    const event: TraceEvent = {
      ...eventsFixture[i % eventsFixture.length],
      id: `event-${Date.now()}-${i}`,
    };
    writer.write(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
    i++;
  }, 1000);

  // Clean up after 30s
  setTimeout(() => clearInterval(interval), 30000);

  writer.close();

  return new HttpResponse(stream.readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  });
});
