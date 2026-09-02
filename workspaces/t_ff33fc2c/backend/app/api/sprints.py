from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List
from app.core.database import get_db
from app.models.base import Sprint, Task, TaskStatus
from app.schemas.board import SprintCreate, SprintUpdate, SprintOut

router = APIRouter()


@router.post("/", response_model=SprintOut)
async def create_sprint(sprint_in: SprintCreate, db: AsyncSession = Depends(get_db)):
    sprint = Sprint(**sprint_in.model_dump())
    db.add(sprint)
    await db.commit()
    await db.refresh(sprint)
    return sprint


@router.get("/", response_model=List[SprintOut])
async def list_sprints(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Sprint))
    return result.scalars().all()


@router.get("/{sprint_id}", response_model=SprintOut)
async def get_sprint(sprint_id: int, db: AsyncSession = Depends(get_db)):
    sprint = await db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return sprint


@router.patch("/{sprint_id}", response_model=SprintOut)
async def update_sprint(sprint_id: int, sprint_in: SprintUpdate, db: AsyncSession = Depends(get_db)):
    sprint = await db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    data = sprint_in.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(sprint, k, v)
    await db.commit()
    await db.refresh(sprint)
    return sprint


@router.post("/{sprint_id}/complete")
async def complete_sprint(sprint_id: int, db: AsyncSession = Depends(get_db)):
    sprint = await db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    # Calculate velocity: sum of story points for completed tasks
    result = await db.execute(
        select(func.coalesce(func.sum(Task.story_points), 0)).where(
            Task.sprint_id == sprint_id, Task.status == TaskStatus.DONE
        )
    )
    velocity = result.scalar()
    sprint.velocity = float(velocity)
    sprint.is_active = False
    await db.commit()
    return {"velocity": velocity, "sprint_id": sprint_id}
