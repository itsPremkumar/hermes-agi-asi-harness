"""Web Dashboard - FastAPI + WebSocket dashboard server."""
from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent

app = FastAPI(title="Hermes AGI Dashboard")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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
            <span id="plugins-count">82 plugins</span>
            <span id="missions-count">0 missions</span>
        </div>
    </div>
    <div class="main">
        <div class="sidebar">
            <h3>Navigation</h3>
            <div class="nav-item active" onclick="showTab('overview')">Overview</div>
            <div class="nav-item" onclick="showTab('missions')">Missions</div>
            <div class="nav-item" onclick="showTab('trajectories')">Trajectories</div>
            <div class="nav-item" onclick="showTab('code')">Code Gen</div>
            <div class="nav-item" onclick="showTab('security')">Security</div>
            <div class="nav-item" onclick="showTab('logs')">Logs</div>
        </div>
        <div class="content">
            <div id="overview">
                <div class="grid">
                    <div class="card">
                        <h4>Total Missions</h4>
                        <div class="value" id="total-missions">0</div>
                        <div class="sub">All time</div>
                    </div>
                    <div class="card">
                        <h4>Completed</h4>
                        <div class="value" id="completed-missions">0</div>
                        <div class="sub">Successful executions</div>
                    </div>
                    <div class="card">
                        <h4>Running</h4>
                        <div class="value" id="running-missions">0</div>
                        <div class="sub">Active missions</div>
                    </div>
                    <div class="card">
                        <h4>Cost</h4>
                        <div class="value" id="total-cost">$0.00</div>
                        <div class="sub">LLM usage</div>
                    </div>
                </div>
                <h3 style="margin-bottom: 1rem;">Quick Actions</h3>
                <input type="text" class="input" id="goal-input" placeholder="Enter a goal (e.g., Build a REST API with authentication)">
                <button class="btn" onclick="startMission()">Start Mission</button>
            </div>
            <div id="missions" style="display:none">
                <h2>Missions</h2>
                <div id="missions-list"></div>
            </div>
            <div id="trajectories" style="display:none">
                <h2>Trajectories</h2>
                <div id="trajectories-list"></div>
            </div>
            <div id="code" style="display:none">
                <h2>Code Generation</h2>
                <textarea class="input" rows="5" id="code-spec" placeholder="Describe the code you want to generate..."></textarea>
                <button class="btn" onclick="generateCode()">Generate</button>
                <pre id="code-output" style="margin-top:1rem;background:#0f172a;padding:1rem;border-radius:8px;"></pre>
            </div>
            <div id="security" style="display:none">
                <h2>Security Scan</h2>
                <input type="text" class="input" id="scan-path" placeholder="Path to scan">
                <button class="btn" onclick="runSecurityScan()">Scan</button>
                <div id="security-results"></div>
            </div>
            <div id="logs" style="display:none">
                <h2>System Logs</h2>
                <div class="log" id="logs-content"></div>
            </div>
        </div>
    </div>
    <script>
        function showTab(tab) {
            document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active'));
            event.target.classList.add('active');
            ['overview','missions','trajectories','code','security','logs'].forEach(t => {
                document.getElementById(t).style.display = t === tab ? 'block' : 'none';
            });
        }
        
        async function startMission() {
            const goal = document.getElementById('goal-input').value;
            if (!goal) return;
            
            const resp = await fetch('/api/missions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({goal})
            });
            const mission = await resp.json();
            addLog('Started mission: ' + mission.id, 'success');
            loadMissions();
        }
        
        async function loadMissions() {
            const resp = await fetch('/api/missions');
            const missions = await resp.json();
            document.getElementById('missions-list').innerHTML = missions.map(m => `
                <div class="mission-item ${m.status}">
                    <strong>${m.goal}</strong>
                    <div style="color:#94a3b8;font-size:0.75rem;">${m.id} - ${m.status}</div>
                </div>
            `).join('');
            document.getElementById('total-missions').textContent = missions.length;
            document.getElementById('completed-missions').textContent = missions.filter(m => m.status === 'completed').length;
            document.getElementById('running-missions').textContent = missions.filter(m => m.status === 'running').length;
        }
        
        async function generateCode() {
            const spec = document.getElementById('code-spec').value;
            const resp = await fetch('/api/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({spec})
            });
            const result = await resp.json();
            document.getElementById('code-output').textContent = result.code || result.error;
        }
        
        async function runSecurityScan() {
            const path = document.getElementById('scan-path').value;
            const resp = await fetch('/api/scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path})
            });
            const result = await resp.json();
            document.getElementById('security-results').innerHTML = (result.findings || []).map(f => `
                <div class="card" style="margin-top:0.5rem;border-left:3px solid ${f.severity === 'CRITICAL' ? '#f87171' : '#fbbf24'}">
                    <strong>${f.rule_id}</strong> - ${f.severity}
                    <div style="color:#94a3b8;font-size:0.75rem;">${f.message} at ${f.file}:${f.line}</div>
                </div>
            `).join('');
        }
        
        function addLog(msg, type = 'info') {
            const logs = document.getElementById('logs-content');
            logs.innerHTML += `<div class="log-entry ${type}">[${new Date().toLocaleTimeString()}] ${msg}</div>`;
            logs.scrollTop = logs.scrollHeight;
        }
        
        // Load initial data
        loadMissions();
        addLog('Dashboard loaded', 'success');
        
        // WebSocket for real-time updates
        const ws = new WebSocket(`ws://${window.location.host}/ws/live`);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            addLog(data.message, data.type);
        };
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML

@app.get("/api/status")
async def status():
    return {"status": "running", "version": "12.0", "plugins": 82}

def run_dashboard(host: str = "0.0.0.0", port: int = 8080):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
