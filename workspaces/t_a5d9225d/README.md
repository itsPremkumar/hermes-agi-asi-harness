# ChainForge — Visual Agent Workflow Builder

ChainForge is a visual no-code platform for building, executing, and deploying AI agent workflows. Drag and drop nodes to create complex multi-step automations with LLMs, tools, logic, and data transforms.

## Features

- **Drag-and-drop workflow designer** — ReactFlow-powered canvas with 100+ built-in nodes
- **100+ built-in nodes** — LLM, Tool, Logic, Transform, Data, Agent, RAG, Vision, Audio
- **Real-time collaboration** — WebSocket-ready architecture
- **Version control** — Track workflow versions and diffs
- **One-click deploy** — Deploy to Docker, Kubernetes, or Lambda
- **Execution history** — Replay and debug past runs
- **Template marketplace** — Save and share workflow templates
- **API for programmatic creation** — Full REST API
- **Export to Python** — Generate runnable Python code from any workflow

## Quick Start

### Backend

```bash
cd backend
pip install -e ".[dev]"
python -m app.main
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App: http://localhost:5173
```

### Docker

```bash
docker-compose up --build
```

## Running Tests

```bash
cd backend
pytest -v
```

## Self-Test

```bash
python scripts/self-test.py
```

## Architecture

```
chainforge/
├── backend/          # FastAPI + SQLAlchemy
│   └── app/
│       ├── api/      # REST routes
│       ├── core/     # Config, database
│       ├── models/   # Pydantic schemas
│       ├── nodes/    # 100+ node definitions
│       ├── services/ # Execution engine
│       ├── codegen/  # Python export
│       └── tests/    # pytest suite
├── frontend/         # React + ReactFlow + Zustand
│   └── src/
│       ├── components/
│       ├── nodes/
│       ├── store/
│       └── services/
├── scripts/
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## License

MIT
