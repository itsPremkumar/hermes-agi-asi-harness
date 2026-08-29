# UIGenerator — AI UI Generator

AI-powered UI generation platform. Generate UI from descriptions, sketches, and screenshots.

## Features

- **AI Generation**: Generate UI from natural-language descriptions
- **Component Library**: 500+ components across 8 categories
- **Multi-Framework Export**: React, Vue, Angular, HTML/CSS
- **Responsive**: Auto-responsive, mobile-first, accessible
- **REST API**: Full API for generation, components, and export

## Tech Stack

- **Frontend**: React, TypeScript, TailwindCSS, Vite
- **Backend**: Python, FastAPI, Pydantic
- **Infrastructure**: Docker, docker-compose

## Quick Start

### With Docker

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Backend Only

```bash
cd backend
pip install -e ".[dev]"
uvicorn backend.app.main:app --reload
```

### Frontend Only

```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/generate` | Generate UI from description |
| GET | `/api/v1/generate/{id}` | Get generation by ID |
| POST | `/api/v1/export` | Export generation in framework |
| GET | `/api/v1/components` | List/search components |
| GET | `/api/v1/components/{id}` | Get component by ID |
| GET | `/api/v1/categories` | List categories |
| GET | `/api/v1/frameworks` | List supported frameworks |

## Example

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"description": "A login form with email and password", "framework": "react"}'
```

## Testing

```bash
pytest backend/tests/ -v --cov
```

## License

MIT
