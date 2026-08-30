"""Servers API router."""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query

from mcphub.db.database import get_db_session
from mcphub.schemas import (
    ServerCreate,
    ServerUpdate,
    ServerResponse,
    ServerListResponse,
    VersionCreate,
    VersionResponse,
)
from mcphub.services import servers as svc

router = APIRouter()


async def get_session():
    async for session in get_db_session():
        yield session


@router.get("", response_model=ServerListResponse)
async def list_servers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort: str = "newest",
    session=Depends(get_session),
):
    return await svc.list_servers(
        session, page=page, per_page=per_page, status=status, category=category, tag=tag, sort=sort
    )


@router.post("", response_model=ServerResponse, status_code=201)
async def create_server(data: ServerCreate, session=Depends(get_session)):
    server = await svc.create_server(session, data)
    await svc.log_event(session, "api_call", server_id=server.id, metadata={"action": "create"})
    return server


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(server_id: str, session=Depends(get_session)):
    server = await svc.get_server(session, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.get("/slug/{slug}", response_model=ServerResponse)
async def get_server_by_slug(slug: str, session=Depends(get_session)):
    server = await svc.get_server_by_slug(session, slug)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.patch("/{server_id}", response_model=ServerResponse)
async def update_server(server_id: str, data: ServerUpdate, session=Depends(get_session)):
    server = await svc.update_server(session, server_id, data)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.delete("/{server_id}", status_code=204)
async def delete_server(server_id: str, session=Depends(get_session)):
    ok = await svc.delete_server(session, server_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Server not found")


@router.post("/{server_id}/download", response_model=ServerResponse)
async def track_download(server_id: str, session=Depends(get_session)):
    server = await svc.get_server(session, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    await svc.increment_downloads(session, server_id)
    await svc.log_event(session, "install", server_id=server_id)
    # Refresh to get updated download count
    await session.refresh(server)
    return server


@router.post("/{server_id}/versions", response_model=VersionResponse, status_code=201)
async def add_version(server_id: str, data: VersionCreate, session=Depends(get_session)):
    version = await svc.add_version(session, server_id, data)
    if not version:
        raise HTTPException(status_code=404, detail="Server not found")
    return version


@router.get("/{server_id}/versions", response_model=list[VersionResponse])
async def list_versions(server_id: str, session=Depends(get_session)):
    return await svc.list_versions(session, server_id)
