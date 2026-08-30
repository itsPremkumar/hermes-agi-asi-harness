# MCPHub — Universal MCP Server Registry & Discovery

> Discover, install, and manage 500+ MCP servers for AI agents

[![CI](https://github.com/itsPremkumar/mcphub/actions/workflows/ci.yml/badge.svg)](https://github.com/itsPremkumar/mcphub/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)

MCPHub is the central registry and discovery platform for Model Context Protocol (MCP) servers. It provides a searchable catalog, health monitoring, analytics, and tooling to install and manage MCP servers.

## Features

- **Searchable Registry** — Browse and search 500+ MCP servers by name, category, transport, tags
- **Server Submission & Review** — Submit your MCP servers for inclusion, with admin review workflow
- **Auto-Discovery** — GitHub topic scanning to automatically find new MCP servers
- **Version Tracking** — Track server versions, changelogs, and releases
- **Health Monitoring** — Real-time uptime and latency checks
- **Analytics Dashboard** — Usage statistics, top servers, category distribution
- **CLI Tool** — Install servers from the command line
- **SDK** — Python and TypeScript SDKs for building MCP servers
- **VS Code Extension** — Browse and install servers from within VS Code

## Quick Start

### Using Docker

```bash
docker-compose up -d
# API: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Manual Setup

```bash
# Install
pip install -e ".[dev]"

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://mcphub:mcphub@localhost:5432/mcphub"
export REDIS_URL="redis://localhost:6379/0"

# Run API
uvicorn mcphub.main:app --reload
```

### CLI Usage

```bash
# Search
mcphub search "web scraping"

# Install
mcphub install web-scraper

# Browse
mcphub list --sort stars

# Submit your server
mcphub submit MyServer --author "Your Name" --description "A great MCP server"
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/servers` | List servers |
| `POST /api/v1/servers` | Create server |
| `GET /api/v1/servers/{id}` | Get server by ID |
| `PATCH /api/v1/servers/{id}` | Update server |
| `DELETE /api/v1/servers/{id}` | Delete server |
| `GET /api/v1/search` | Search servers |
| `POST /api/v1/submissions` | Submit a server |
| `POST /api/v1/submissions/{id}/review` | Review a submission |
| `GET /api/v1/health/{id}` | Get server health summary |
| `POST /api/v1/health/{id}/check` | Record health check |
| `GET /api/v1/analytics` | Get analytics summary |
| `POST /api/v1/discover` | Trigger discovery scan |
| `GET /api/v1/discover/topics` | List discoverable topics |

## Project Structure

```
mcphub/
├── backend/           # FastAPI backend
│   └── src/mcphub/
│       ├── api/       # API route handlers
│       ├── db/        # Database & Redis
│       ├── models/    # SQLAlchemy models
│       ├── schemas/   # Pydantic schemas
│       └── services/  # Business logic
├── cli/               # CLI tool (mcphub)
├── sdk/               # SDKs
│   ├── python/        # Python SDK
│   └── typescript/    # TypeScript SDK
├── frontend/          # Next.js frontend
├── vscode-extension/  # VS Code extension
├── scripts/           # Utility scripts
├── .github/           # CI/CD workflows
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Python SDK

```python
from mcp_sdk import create_server

server = create_server(
    name="my-server",
    version="1.0.0",
    description="My MCP server",
    author="Me",
)

@server.tool(name="greet", description="Greet a user")
def greet(name: str) -> str:
    return f"Hello, {name}!"

# Generate manifest for MCPHub
manifest = server.generate_manifest()
```

## TypeScript SDK

```typescript
import { createServer } from "@mcphub/sdk";

const server = createServer({
  name: "my-server",
  version: "1.0.0",
  description: "My MCP server",
});

server.registerTool({
  name: "greet",
  description: "Greet a user",
  inputSchema: { type: "object", properties: { name: { type: "string" } } },
  handler: (args) => `Hello, ${args.name}!`,
});
```

## Development

```bash
# Run tests
pytest backend/tests -v

# Run linter
ruff check backend/src cli sdk/python

# Type check
mypy backend/src mcphub
```

## License

MIT © Prem Kumar
