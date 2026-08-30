"""MCPHub — Universal MCP Server Registry & Discovery."""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcphub.api import servers, search, submissions, health, analytics, discover
from mcphub.db import database, redis_client

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    await database.connect()
    await redis_client.connect()
    logger.info("MCPHub API started")
    yield
    await database.disconnect()
    await redis_client.disconnect()
    logger.info("MCPHub API stopped")


app = FastAPI(
    title="MCPHub",
    description="Universal MCP Server Registry & Discovery Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(servers.router, prefix="/api/v1/servers", tags=["servers"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(submissions.router, prefix="/api/v1/submissions", tags=["submissions"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(discover.router, prefix="/api/v1/discover", tags=["discover"])


@app.get("/")
async def root():
    return {"name": "MCPHub", "version": "1.0.0", "docs": "/docs"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
