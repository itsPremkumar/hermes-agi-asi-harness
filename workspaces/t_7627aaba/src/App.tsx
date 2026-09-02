import { Routes, Route, Link, NavLink } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { ConnectionStatus } from '../components/ConnectionStatus';
import AgentDetailView from '../views/AgentDetailView';

const AgentGridView = lazy(() => import('../views/AgentGridView'));
const PlanVisualization = lazy(() => import('../views/PlanVisualization'));
const TraceGraphView = lazy(() => import('../views/TraceGraphView'));
const ChatInterface = lazy(() => import('../components/ChatInterface'));
const CircuitBreakersDashboard = lazy(
  () => import('../components/CircuitBreakersDashboard'),
);

/**
 * Dashboard shell with navigation placeholders for:
 * Agent Grid, Plans, Traces, Chat, Breakers
 */
export default function App() {
  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-avo-border bg-avo-surface px-4 py-2">
        <div className="flex items-center space-x-4">
          <Link to="/" className="text-xl font-bold text-avo-text">
            AVOStudio
          </Link>
          <nav className="flex space-x-2">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `px-3 py-1 text-sm rounded ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-avo-text-muted hover:text-avo-text'
                }`
              }
            >
              Agent Grid
            </NavLink>
            <NavLink
              to="/plans"
              className={({ isActive }) =>
                `px-3 py-1 text-sm rounded ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-avo-text-muted hover:text-avo-text'
                }`
              }
            >
              Plans
            </NavLink>
            <NavLink
              to="/traces"
              className={({ isActive }) =>
                `px-3 py-1 text-sm rounded ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-avo-text-muted hover:text-avo-text'
                }`
              }
            >
              Traces
            </NavLink>
            <NavLink
              to="/chat"
              className={({ isActive }) =>
                `px-3 py-1 text-sm rounded ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-avo-text-muted hover:text-avo-text'
                }`
              }
            >
              Chat
            </NavLink>
            <NavLink
              to="/breakers"
              className={({ isActive }) =>
                `px-3 py-1 text-sm rounded ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-avo-text-muted hover:text-avo-text'
                }`
              }
            >
              Breakers
            </NavLink>
          </nav>
        </div>
        <ConnectionStatus />
      </header>

      <main className="flex-1 overflow-y-auto">
        <Suspense
          fallback={
            <div className="p-8 text-avo-text-muted">Loading...</div>
          }
        >
          <Routes>
            <Route path="/" element={<AgentGridView />} />
            <Route path="/plans" element={<PlanPlaceholderView />} />
            <Route path="/traces" element={<TraceGraphView />} />
            <Route path="/chat" element={<ChatInterface />} />
            <Route path="/breakers" element={<CircuitBreakersDashboard />} />
            <Route path="/agent/:agentId" element={<AgentDetailView />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}

/**
 * Plans nav placeholder — wraps the lazy PlanVisualization.
 * When no active agent is selected, it shows a lightweight placeholder.
 */
function PlanPlaceholderView() {
  return (
    <div className="p-4">
      <div className="card">
        <h2 className="mb-2 text-lg font-semibold text-avo-text">Plan Overview</h2>
        <p className="text-sm text-avo-text-muted">
          Navigate to an agent detail page to view its plan tree.
          This is a placeholder for the Plans dashboard route.
        </p>
      </div>
      <div className="mt-4 card">
        <PlanVisualization />
      </div>
    </div>
  );
}
