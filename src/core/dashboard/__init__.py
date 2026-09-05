"""Web Dashboard - FastAPI + WebSocket dashboard server.

The monitoring logic (plugins, missions, health, events, config) has no
third-party dependencies and always imports. The HTTP server itself needs
``fastapi`` (``pip install -e ".[api]"``); when it is missing, ``app`` is
``None`` and only the route table is skipped.
"""
from __future__ import annotations

from typing import Any

from .config import ConfigEditor
from .events import EventLog
from .health import HealthMonitor, HealthStatus
from .missions import MissionController
from .plugins import PluginManager

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse
except ImportError:  # minimal installs: logic stays importable, server disabled
    FastAPI = None  # type: ignore[assignment,misc]
    Request = None  # type: ignore[assignment,misc]
    HTMLResponse = None  # type: ignore[assignment,misc]

FASTAPI_AVAILABLE = FastAPI is not None

app: Any = FastAPI(title="Hermes AGI Dashboard") if FASTAPI_AVAILABLE else None

# Shared state
plugins = PluginManager()
missions = MissionController()
health = HealthMonitor()
events = EventLog()
config = ConfigEditor()

# Seed some data
plugins.register("web-search", "1.0", "Web search plugin", ["search", "browse"])
plugins.register("code-gen", "1.0", "Code generation plugin", ["codegen", "refactor"])
plugins.register("memory", "1.0", "Memory plugin", ["memory", "context"])
health.update("api", HealthStatus.HEALTHY, 5.0, "API healthy")
health.update("database", HealthStatus.HEALTHY, 2.0, "DB connected")
events.info("Dashboard loaded", "system")

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Hermes AGI Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }
        .header { background: #1e293b; padding: 1rem 2rem; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 1rem; }
        .header h1 { font-size: 1.5rem; color: #38bdf8; }
        .status { display: flex; gap: 1rem; margin-left: auto; }
        .status span { background: #334155; padding: 0.5rem 1rem; border-radius: 4px; font-size: 0.875rem; }
        .status .online { background: #059669; }
        .main { display: grid; grid-template-columns: 300px 1fr; height: calc(100vh - 60px); }
        .sidebar { background: #1e293b; border-right: 1px solid #334155; padding: 1rem; overflow-y: auto; }
        .sidebar h3 { color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
        .nav-item { padding: 0.75rem 1rem; border-radius: 6px; cursor: pointer; margin-bottom: 0.25rem; transition: all 0.2s; }
        .nav-item:hover { background: #334155; }
        .nav-item.active { background: #0ea5e9; color: white; }
        .content { padding: 2rem; overflow-y: auto; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 1.5rem; }
        .card h4 { color: #94a3b8; font-size: 0.875rem; margin-bottom: 0.5rem; }
        .card .value { font-size: 2rem; font-weight: bold; color: #f8fafc; }
        .card .sub { font-size: 0.75rem; color: #64748b; margin-top: 0.25rem; }
        .log { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 1rem; font-family: monospace; font-size: 0.75rem; max-height: 400px; overflow-y: auto; }
        .log-entry { padding: 0.25rem 0; border-bottom: 1px solid #1e293b; }
        .log-entry.info { color: #38bdf8; }
        .log-entry.success { color: #4ade80; }
        .log-entry.error { color: #f87171; }
        .btn { background: #0ea5e9; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
        .btn:hover { background: #0284c7; }
        .input { background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 0.75rem; border-radius: 6px; width: 100%; margin-bottom: 1rem; }
        .mission-item { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 1rem; margin-bottom: 0.5rem; }
        .mission-item.running { border-left: 3px solid #fbbf24; }
        .mission-item.completed { border-left: 3px solid #4ade80; }
        .mission-item.failed { border-left: 3px solid #f87171; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Hermes AGI</h1>
        <div class="status">
            <span class="online">● Online</span>
            <span id="plugins-count">""" + str(plugins.active_count()) + """ plugins</span>
            <span id="missions-count">""" + str(missions.count()) + """ missions</span>
        </div>
    </div>
    <div class="main">
        <div class="sidebar">
            <h3>Navigation</h3>
            <div class="nav-item active" onclick="showTab('overview')">Overview</div>
            <div class="nav-item" onclick="showTab('plugins')">Plugins</div>
            <div class="nav-item" onclick="showTab('missions')">Missions</div>
            <div class="nav-item" onclick="showTab('health')">Health</div>
            <div class="nav-item" onclick="showTab('events')">Events</div>
            <div class="nav-item" onclick="showTab('config')">Config</div>
        </div>
        <div class="content">
            <div id="overview">
                <div class="grid">
                    <div class="card"><h4>Total Missions</h4><div class="value" id="total-missions">0</div></div>
                    <div class="card"><h4>Completed</h4><div class="value" id="completed-missions">0</div></div>
                    <div class="card"><h4>Running</h4><div class="value" id="running-missions">0</div></div>
                    <div class="card"><h4>Plugins</h4><div class="value" id="active-plugins">""" + str(plugins.active_count()) + """</div></div>
                </div>
                <h3>Quick Actions</h3>
                <input type="text" class="input" id="goal-input" placeholder="Enter a goal">
                <button class="btn" onclick="startMission()">Start Mission</button>
            </div>
            <div id="plugins" style="display:none"><h2>Plugins</h2><div id="plugins-list"></div></div>
            <div id="missions" style="display:none"><h2>Missions</h2><div id="missions-list"></div></div>
            <div id="health" style="display:none"><h2>Health</h2><div id="health-list"></div></div>
            <div id="events" style="display:none"><h2>Event Log</h2><div class="log" id="events-list"></div></div>
            <div id="config" style="display:none"><h2>Configuration</h2><div id="config-list"></div></div>
        </div>
    </div>
    <script>
        function showTab(tab) {
            document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active'));
            event.target.classList.add('active');
            ['overview','plugins','missions','health','events','config'].forEach(t => {
                document.getElementById(t).style.display = t === tab ? 'block' : 'none';
            });
            if (tab === 'plugins') loadPlugins();
            if (tab === 'missions') loadMissions();
            if (tab === 'health') loadHealth();
            if (tab === 'events') loadEvents();
            if (tab === 'config') loadConfig();
        }
        async function startMission() {
            const goal = document.getElementById('goal-input').value;
            if (!goal) return;
            await fetch('/api/missions', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({goal}) });
            loadMissions();
        }
        async function loadPlugins() {
            const resp = await fetch('/api/plugins');
            const data = await resp.json();
            document.getElementById('plugins-list').innerHTML = data.map(p =>
                '<div class="mission-item"><strong>' + p.name + '</strong> v' + p.version +
                '<div style="color:#94a3b8;font-size:0.75rem;">' + p.id + ' - ' + p.status + '</div></div>'
            ).join('');
        }
        async function loadMissions() {
            const resp = await fetch('/api/missions');
            const data = await resp.json();
            document.getElementById('missions-list').innerHTML = data.map(m =>
                '<div class="mission-item ' + m.status + '"><strong>' + m.goal + '</strong>' +
                '<div style="color:#94a3b8;font-size:0.75rem;">' + m.id + ' - ' + m.status + '</div></div>'
            ).join('');
        }
        async function loadHealth() {
            const resp = await fetch('/api/health');
            const data = await resp.json();
            document.getElementById('health-list').innerHTML = Object.entries(data.components).map(([k,v]) =>
                '<div class="mission-item"><strong>' + k + '</strong><div style="color:#94a3b8;font-size:0.75rem;">' + v + '</div></div>'
            ).join('');
        }
        async function loadEvents() {
            const resp = await fetch('/api/events');
            const data = await resp.json();
            document.getElementById('events-list').innerHTML = data.map(e =>
                '<div class="log-entry ' + e.level + '">[' + new Date(e.timestamp * 1000).toLocaleTimeString() + '] ' + e.message + '</div>'
            ).join('');
        }
        async function loadConfig() {
            const resp = await fetch('/api/config');
            const data = await resp.json();
            document.getElementById('config-list').innerHTML = Object.entries(data).map(([k,v]) =>
                '<div class="mission-item"><strong>' + k + '</strong><div style="color:#94a3b8;font-size:0.75rem;">' + v + '</div></div>'
            ).join('');
        }
    </script>
</body>
</html>
"""

if app is not None:  # server routes require fastapi
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return DASHBOARD_HTML

    @app.get("/api/status")
    async def status():
        return {
            "status": "running",
            "version": "2.1.0",
            "plugins": plugins.count(),
            "missions": missions.count(),
            "health": health.overall_status().value,
        }

    @app.get("/api/plugins")
    async def list_plugins():
        return [
            {"id": p.id, "name": p.name, "version": p.version, "status": p.status.value, "capabilities": p.capabilities}
            for p in plugins.list_all()
        ]

    @app.post("/api/plugins")
    async def register_plugin(req: Request):
        body = await req.json()
        p = plugins.register(body.get("name", ""), body.get("version", "0.1.0"), body.get("description", ""), body.get("capabilities", []))
        events.info(f"Plugin registered: {p.name}", "plugins")
        return {"id": p.id, "name": p.name}

    @app.delete("/api/plugins/{plugin_id}")
    async def unregister_plugin(plugin_id: str):
        if plugins.unregister(plugin_id):
            events.info(f"Plugin unregistered: {plugin_id}", "plugins")
            return {"status": "removed"}
        return {"error": "not found"}

    @app.post("/api/plugins/{plugin_id}/enable")
    async def enable_plugin(plugin_id: str):
        return {"status": "enabled" if plugins.enable(plugin_id) else "not found"}

    @app.post("/api/plugins/{plugin_id}/disable")
    async def disable_plugin(plugin_id: str):
        return {"status": "disabled" if plugins.disable(plugin_id) else "not found"}

    @app.get("/api/missions")
    async def list_missions():
        return [
            {"id": m.id, "goal": m.goal, "status": m.status.value}
            for m in missions.list_all()
        ]

    @app.post("/api/missions")
    async def create_mission(req: Request):
        body = await req.json()
        m = missions.create(body.get("goal", ""))
        events.info(f"Mission created: {m.goal}", "missions")
        return {"id": m.id, "goal": m.goal}

    @app.post("/api/missions/{mission_id}/start")
    async def start_mission(mission_id: str):
        missions.start(mission_id)
        return {"status": "started"}

    @app.post("/api/missions/{mission_id}/complete")
    async def complete_mission(mission_id: str):
        missions.complete(mission_id)
        events.success(f"Mission completed: {mission_id}", "missions")
        return {"status": "completed"}

    @app.post("/api/missions/{mission_id}/fail")
    async def fail_mission(mission_id: str, req: Request):
        body = await req.json()
        missions.fail(mission_id, body.get("error", ""))
        events.error(f"Mission failed: {mission_id}", "missions")
        return {"status": "failed"}

    @app.get("/api/health")
    async def get_health():
        return {
            "overall": health.overall_status().value,
            "components": {k: v.status.value for k, v in health.get_all().items()},
        }

    @app.get("/api/events")
    async def get_events():
        return [
            {"id": e.id, "message": e.message, "level": e.level.value, "timestamp": e.timestamp}
            for e in events.get_recent(100)
        ]

    @app.get("/api/config")
    async def get_config():
        return {k: v.value for k, v in config._config.items()}

    @app.post("/api/config")
    async def set_config(req: Request):
        body = await req.json()
        for key, value in body.items():
            config.set(key, value)
        events.info("Configuration updated", "config")
        return {"status": "updated"}

    def run_dashboard(host: str = "0.0.0.0", port: int = 8080):
        import uvicorn
        uvicorn.run(app, host=host, port=port)
