# TaskForge — Open Source Kanban + Sprint Planning Tool

Production-grade Kanban board with sprint planning, velocity tracking, burndown charts, WIP limits, cycle-time analytics, and CSV/PDF/JSON export.

## Tech Stack
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2 (async), PostgreSQL, WebSockets
- **Auth:** JWT (HS256), bcrypt password hashing
- **Frontend:** React, TypeScript, Vite (coming soon)

## Quick Start

```bash
# 1. Install deps (uv recommended)
cd backend
uv pip install -e ".[dev]"

# 2. Set up PostgreSQL and env
export TASKFORGE_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/taskforge"
export TASKFORGE_SECRET_KEY="change-me"

# 3. Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. API docs
open http://localhost:8000/docs
```

## API Overview

| Endpoint | Description |
|----------|-------------|
| `POST /auth/register` | Register new user |
| `POST /auth/login` | Login, get JWT |
| `GET /boards` | List boards |
| `POST /boards` | Create board |
| `POST /boards/{id}/columns` | Add column |
| `GET /tasks` | List tasks (filter by column_id / sprint_id) |
| `PATCH /tasks/{id}` | Update task (auto-tracks cycle/lead time) |
| `GET /tasks/ws/board/{board_id}` | WebSocket real-time updates |
| `POST /sprints` | Create sprint |
| `POST /sprints/{id}/complete` | Complete sprint, compute velocity |
| `GET /analytics/burndown/{sprint_id}` | Burndown data |
| `GET /analytics/cycle-time` | Average cycle/lead time |
| `GET /export/csv` | Export tasks to CSV |
| `GET /export/pdf` | Export board to PDF |
| `GET /export/json` | Export board to JSON |

## OUTPUT LAW

All code in workspace. Git commit must succeed. Pushed to GitHub.
Push target: itsPremkumar/taskforge-oss
