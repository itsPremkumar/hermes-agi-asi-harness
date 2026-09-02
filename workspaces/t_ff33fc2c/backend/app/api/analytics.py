from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import List
from app.core.database import get_db
from app.models.base import Task, Sprint, TaskStatus
from app.schemas.board import BurndownPoint, AnalyticsOut

router = APIRouter()


@router.get("/burndown/{sprint_id}", response_model=List[BurndownPoint])
async def burndown(sprint_id: int, db: AsyncSession = Depends(get_db)):
    sprint = await db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    result = await db.execute(
        select(Task).where(Task.sprint_id == sprint_id)
    )
    tasks = result.scalars().all()
    total_points = sum(t.story_points or 0 for t in tasks)
    if total_points == 0:
        return []
    days = max((sprint.end_date - sprint.start_date).days, 1)
    points_per_day = total_points / days
    points_done_by_day = {}
    for t in tasks:
        if t.status == TaskStatus.DONE and t.completed_at:
            day = (t.completed_at - sprint.start_date).days
            points_done_by_day[day] = points_done_by_day.get(day, 0) + (t.story_points or 0)
    series = []
    cumulative_done = 0
    for d in range(days + 1):
        cumulative_done += points_done_by_day.get(d, 0)
        remaining = total_points - cumulative_done
        ideal = total_points - points_per_day * d
        point_date = sprint.start_date + timedelta(days=d)
        series.append(BurndownPoint(
            date=point_date,
            remaining_points=max(remaining, 0),
            ideal_points=max(ideal, 0),
        ))
    return series


@router.get("/cycle-time", response_model=AnalyticsOut)
async def cycle_time(
    sprint_id: int = None,
    column_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Task)
    if sprint_id:
        query = query.where(Task.sprint_id == sprint_id)
    if column_id:
        query = query.where(Task.column_id == column_id)
    result = await db.execute(query)
    tasks = result.scalars().all()
    completed = [t for t in tasks if t.status == TaskStatus.DONE]
    cycle_times = [t.cycle_time for t in completed if t.cycle_time is not None]
    lead_times = [t.lead_time for t in completed if t.lead_time is not None]
    wip = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
    avg_cycle = sum(cycle_times) / len(cycle_times) if cycle_times else None
    avg_lead = sum(lead_times) / len(lead_times) if lead_times else None
    return AnalyticsOut(
        avg_cycle_time=avg_cycle,
        avg_lead_time=avg_lead,
        throughput=len(completed),
        completed_this_sprint=len(completed) if sprint_id else 0,
        wip_count=len(wip),
    )
