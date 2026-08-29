from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List
from app.core.database import get_db
from app.models.base import Task, BoardColumn, TaskStatus
from app.schemas.board import TaskCreate, TaskUpdate, TaskOut
import json

router = APIRouter()


@router.post("/", response_model=TaskOut)
async def create_task(task_in: TaskCreate, db: AsyncSession = Depends(get_db)):
    # Check WIP limit
    col = await db.get(BoardColumn, task_in.column_id)
    if col and col.wip_limit:
        count = await db.execute(select(Task).where(Task.column_id == col.id))
        if len(count.scalars().all()) >= col.wip_limit:
            raise HTTPException(status_code=400, detail=f"WIP limit reached for column '{col.name}'")
    task = Task(**task_in.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/", response_model=List[TaskOut])
async def list_tasks(column_id: int = None, sprint_id: int = None, db: AsyncSession = Depends(get_db)):
    query = select(Task)
    if column_id:
        query = query.where(Task.column_id == column_id)
    if sprint_id:
        query = query.where(Task.sprint_id == sprint_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, task_in: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    data = task_in.model_dump(exclude_unset=True)
    # Track cycle/lead time based on status changes
    new_status = data.get("status")
    if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
        data["started_at"] = datetime.utcnow()
    elif new_status == TaskStatus.DONE:
        data["completed_at"] = datetime.utcnow()
        if task.started_at:
            data["cycle_time"] = (datetime.utcnow() - task.started_at).total_seconds() / 3600
        if task.created_at:
            data["lead_time"] = (datetime.utcnow() - task.created_at).total_seconds() / 3600
    elif new_status and new_status != TaskStatus.DONE:
        data.pop("completed_at", None)
    for k, v in data.items():
        setattr(task, k, v)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
    return {"status": "deleted"}


# WebSocket for real-time board updates
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, message: dict):
        for conn in self.active:
            await conn.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/board/{board_id}")
async def board_ws(websocket: WebSocket, board_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Broadcast updates to all connected clients
            await manager.broadcast({"board_id": board_id, **data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
