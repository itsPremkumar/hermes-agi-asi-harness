"""Auto-discovery API router."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from mcphub.db.database import get_db_session
from mcphub.schemas import DiscoverRequest, DiscoverResult
from mcphub.models import Server, ServerStatus
from sqlalchemy import select

router = APIRouter()


async def get_session():
    async for session in get_db_session():
        yield session


@router.post("", response_model=DiscoverResult)
async def discover_servers(data: DiscoverRequest, session=Depends(get_session)):
    """Discover MCP servers from GitHub topic scanning (simulated)."""
    # In production, this would scan GitHub for repos tagged with the topic
    # For now, return a placeholder response
    discovered = 0
    new_servers = []

    # Simulate discovery by checking for servers with is_discovered=True
    result = await session.execute(
        select(Server).where(Server.is_discovered == True).limit(data.max_results)
    )
    existing = result.scalars().all()
    discovered = len(existing)

    return DiscoverResult(
        discovered=discovered,
        new_servers=[{"id": s.id, "name": s.name, "repository_url": s.repository_url} for s in existing],
    )


@router.get("/topics")
async def list_discoverable_topics():
    """List GitHub topics that can be scanned for MCP servers."""
    return {
        "topics": [
            "mcp-server",
            "model-context-protocol",
            "mcp-tool",
            "ai-agent-tool",
            "llm-tool",
        ]
    }
