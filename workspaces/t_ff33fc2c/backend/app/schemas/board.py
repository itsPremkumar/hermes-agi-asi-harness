from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from app.models.base import TaskStatus, TaskPriority


class UserCreate(BaseModel):
    email: str
    name: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BoardCreate(BaseModel):
    name: str
    description: Optional[str] = None


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    created_at: datetime


class ColumnCreate(BaseModel):
    name: str
    position: int
    wip_limit: Optional[int] = None


class ColumnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    board_id: int
    name: str
    position: int
    wip_limit: Optional[int]


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    story_points: Optional[int] = None
    column_id: int
    assignee_id: Optional[int] = None
    sprint_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    position: Optional[int] = None
    column_id: Optional[int] = None
    assignee_id: Optional[int] = None
    sprint_id: Optional[int] = None
    story_points: Optional[int] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    position: int
    story_points: Optional[int]
    column_id: int
    assignee_id: Optional[int]
    sprint_id: Optional[int]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    cycle_time: Optional[float]
    lead_time: Optional[float]


class SprintCreate(BaseModel):
    name: str
    goal: Optional[str] = None
    start_date: datetime
    end_date: datetime


class SprintUpdate(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class SprintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    goal: Optional[str]
    start_date: datetime
    end_date: datetime
    velocity: Optional[float]
    is_active: bool
    created_at: datetime


class BurndownPoint(BaseModel):
    date: datetime
    remaining_points: float
    ideal_points: float


class AnalyticsOut(BaseModel):
    avg_cycle_time: Optional[float]
    avg_lead_time: Optional[float]
    throughput: int
    completed_this_sprint: int
    wip_count: int
