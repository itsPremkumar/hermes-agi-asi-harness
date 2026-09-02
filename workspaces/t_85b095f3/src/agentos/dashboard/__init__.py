"""Web dashboard for AgentOS (simple HTTP server)."""

from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs

from agentos import __version__
from agentos.observability import Observability
from agentos.state import StateManager


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    observability: Observability | None = None
    state: StateManager | None = None

    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        routes = {
            "/": self._handle_index,
            "/health": self._handle_health,
            "/metrics": self._handle_metrics,
            "/state": self._handle_state,
            "/spans": self._handle_spans,
        }

        handler = routes.get(path, self._handle_404)
        handler()

    def _handle_index(self) -> None:
        """Serve the dashboard index."""
        html = f"""<!DOCTYPE html>
<html>
<head><title>AgentOS Dashboard</title></head>
<body>
<h1>AgentOS v{__version__}</h1>
<ul>
<li><a href="/health">Health</a></li>
<li><a href="/metrics">Metrics</a></li>
<li><a href="/state">State</a></li>
<li><a href="/spans">Traces</a></li>
</ul>
</body>
</html>"""
        self._send(200, html, "text/html")

    def _handle_health(self) -> None:
        """Serve health status."""
        obs = self.observability or Observability()
        self._send(200, json.dumps(obs.health()), "application/json")

    def _handle_metrics(self) -> None:
        """Serve metrics."""
        obs = self.observability or Observability()
        self._send(200, json.dumps(obs.metrics.summary(), indent=2), "application/json")

    def _handle_state(self) -> None:
        """Serve state keys."""
        state = self.state or StateManager()
        keys = state.list_keys()
        self._send(200, json.dumps({"keys": keys}, indent=2), "application/json")

    def _handle_spans(self) -> None:
        """Serve trace spans."""
        obs = self.observability or Observability()
        spans = [s.to_dict() for s in obs.tracer.get_spans()]
        self._send(200, json.dumps(spans, indent=2, default=str), "application/json")

    def _handle_404(self) -> None:
        """Handle unknown routes."""
        self._send(404, json.dumps({"error": "not found"}), "application/json")

    def _send(self, status: int, body: str, content_type: str) -> None:
        """Send an HTTP response."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging."""
        pass


def create_server(host: str = "127.0.0.1", port: int = 8080,
                  observability: Observability | None = None,
                  state: StateManager | None = None) -> HTTPServer:
    """Create the dashboard HTTP server."""
    DashboardHandler.observability = observability
    DashboardHandler.state = state
    return HTTPServer((host, port), DashboardHandler)


def run_dashboard(host: str = "127.0.0.1", port: int = 8080,
                  observability: Observability | None = None,
                  state: StateManager | None = None) -> None:
    """Run the dashboard server."""
    server = create_server(host, port, observability, state)
    print(f"AgentOS Dashboard running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard...")
        server.shutdown()
