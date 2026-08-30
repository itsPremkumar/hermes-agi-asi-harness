"""Analytics API router."""
from typing import Optional

from fastapi import APIRouter, Depends

from mcphub.db.database import get_db_session
from mcphub.schemas import AnalyticsEventCreate, AnalyticsSummary
from mcphub.services import servers as svc

router = APIRouter()


async def get_session():
    async for session in get_db_session():
        yield session


@router.get("", response_model=AnalyticsSummary)
async def get_analytics(session=Depends(get_session)):
    return await svc.get_analytics_summary(session)


@router.post("/events", status_code=201)
async def track_event(data: AnalyticsEventCreate, session=Depends(get_session)):
    await svc.log_event(
        session,
        event_type=data.event_type,
        server_id=data.server_id,
        metadata=data.metadata_json,
    )
    return {"status": "ok"}
