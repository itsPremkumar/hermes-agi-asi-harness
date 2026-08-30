"""Health monitoring API router."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from mcphub.db.database import get_db_session
from mcphub.schemas import HealthCheckResponse, ServerHealthSummary
from mcphub.services import servers as svc

router = APIRouter()


async def get_session():
    async for session in get_db_session():
        yield session


@router.get("/{server_id}", response_model=ServerHealthSummary)
async def get_server_health(server_id: str, session=Depends(get_session)):
    summary = await svc.get_health_summary(session, server_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Server not found")
    return summary


@router.post("/{server_id}/check", response_model=HealthCheckResponse)
async def record_health_check(
    server_id: str,
    status_code: Optional[int] = None,
    response_time_ms: float = 0.0,
    is_up: bool = True,
    error_message: Optional[str] = None,
    session=Depends(get_session),
):
    server = await svc.get_server(session, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    await svc.record_health_check(session, server_id, status_code, response_time_ms, is_up, error_message)
    return HealthCheckResponse(
        id="",
        server_id=server_id,
        status_code=status_code,
        response_time_ms=response_time_ms,
        is_up=is_up,
        error_message=error_message,
        checked_at=__import__("datetime").datetime.utcnow(),
    )
