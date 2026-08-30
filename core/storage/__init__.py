"""
Database & Storage Layer - Persistent storage for all system data.

Supports SQLite (local) and PostgreSQL (production).
Uses SQLAlchemy ORM with async support.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Enum as SQLEnum, Float,
    ForeignKey, Integer, String, Text, create_engine, select, func
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class MissionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Trajectory(Base):
    """Stores complete execution trajectories."""
    __tablename__ = "trajectories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False)
    goal = Column(Text, nullable=False)
    scenario_type = Column(String)
    complexity = Column(String)
    status = Column(String, default=MissionStatus.PENDING.value)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Usage tracking
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    
    # Relationships
    steps = relationship("TrajectoryStep", back_populates="trajectory", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="trajectory", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "goal": self.goal,
            "scenario_type": self.scenario_type,
            "complexity": self.complexity,
            "status": self.status,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "steps": [s.to_dict() for s in self.steps],
            "artifacts": [a.to_dict() for a in self.artifacts],
        }


class Mission(Base):
    """Stores mission metadata."""
    __tablename__ = "missions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    goal = Column(Text, nullable=False)
    scenario_type = Column(String)
    complexity = Column(String)
    status = Column(String, default=MissionStatus.PENDING.value)
    
    # Configuration
    config = Column(JSON, default={})
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Results
    result = Column(JSON)
    error = Column(Text)
    
    # Usage tracking
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    
    def to_dict(self):
        return {
            "id": self.id,
            "goal": self.goal,
            "scenario_type": self.scenario_type,
            "complexity": self.complexity,
            "status": self.status,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "result": self.result,
            "error": self.error,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
        }


class TrajectoryStep(Base):
    """Stores individual step execution data."""
    __tablename__ = "trajectory_steps"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trajectory_id = Column(String, ForeignKey("trajectories.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    name = Column(String)
    step_type = Column(String)
    
    # Execution data
    status = Column(String, default=StepStatus.PENDING.value)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_ms = Column(Float)
    
    # Input/Output
    input_data = Column(JSON)
    output_data = Column(JSON)
    error = Column(Text)
    
    # Modules used
    modules_used = Column(JSON, default=[])
    agent_role = Column(String)
    
    # Decisions made
    decisions = Column(JSON, default=[])
    
    # Usage tracking
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    
    # Relationships
    trajectory = relationship("Trajectory", back_populates="steps")
    
    def to_dict(self):
        return {
            "id": self.id,
            "step_number": self.step_number,
            "name": self.name,
            "step_type": self.step_type,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "modules_used": self.modules_used,
            "agent_role": self.agent_role,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
        }


class Artifact(Base):
    """Stores artifacts generated during execution."""
    __tablename__ = "artifacts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4__))
    trajectory_id = Column(String, ForeignKey("trajectories.id"))
    name = Column(String, nullable=False)
    artifact_type = Column(String)
    content = Column(Text)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trajectory = relationship("Trajectory", back_populates="artifacts")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "artifact_type": self.artifact_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata,
        }


class SkillModel(Base):
    """Stores learned skills."""
    __tablename__ = "skills"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    steps = Column(JSON, default=[])
    source_trajectory = Column(String)
    benchmark_score = Column(Float, default=0.0)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default={})
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "verified": self.verified,
            "benchmark_score": self.benchmark_score,
        }


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = "sqlite+aiosqlite:///hermes_agi.db"
        
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init_db(self):
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session."""
        return self.async_session()
    
    async def close(self):
        """Close database connection."""
        await self.engine.dispose()


class TrajectoryStore:
    """Store and retrieve execution trajectories."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_trajectory(self, mission_id: str, goal: str,
                                 scenario_type: str = None,
                                 complexity: str = None) -> str:
        """Create a new trajectory."""
        async with self.db.get_session() as session:
            trajectory = Trajectory(
                mission_id=mission_id,
                goal=goal,
                scenario_type=scenario_type,
                complexity=complexity,
            )
            session.add(trajectory)
            await session.commit()
            return trajectory.id
    
    async def add_step(self, trajectory_id: str, step_number: int,
                       name: str, step_type: str, modules: List[str],
                       agent_role: str) -> str:
        """Add a step to a trajectory."""
        async with self.db.get_session() as session:
            step = TrajectoryStep(
                trajectory_id=trajectory_id,
                step_number=step_number,
                name=name,
                step_type=step_type,
                modules_used=modules,
                agent_role=agent_role,
            )
            session.add(step)
            await session.commit()
            return step.id
    
    async def complete_step(self, step_id: str, output: Any,
                            tokens: int = 0, cost: float = 0.0):
        """Mark a step as completed."""
        async with self.db.get_session() as session:
            step = await session.get(TrajectoryStep, step_id)
            if step:
                step.status = StepStatus.COMPLETED.value
                step.completed_at = datetime.utcnow()
                step.output_data = output if isinstance(output, dict) else {"output": str(output)}
                step.tokens_used = tokens
                step.cost = cost
                await session.commit()
    
    async def complete_trajectory(self, trajectory_id: str,
                                   status: str, total_tokens: int = 0,
                                   total_cost: float = 0.0):
        """Mark a trajectory as completed."""
        async with self.db.get_session() as session:
            trajectory = await session.get(Trajectory, trajectory_id)
            if trajectory:
                trajectory.status = status
                trajectory.completed_at = datetime.utcnow()
                trajectory.total_tokens = total_tokens
                trajectory.total_cost = total_cost
                await session.commit()
    
    async def get_trajectory(self, trajectory_id: str) -> Optional[Dict]:
        """Get a trajectory by ID."""
        async with self.db.get_session() as session:
            trajectory = await session.get(Trajectory, trajectory_id)
            return trajectory.to_dict() if trajectory else None
    
    async def get_all_trajectories(self, limit: int = 100) -> List[Dict]:
        """Get all trajectories."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(Trajectory).order_by(Trajectory.created_at.desc()).limit(limit)
            )
            return [t.to_dict() for t in result.scalars().all()]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get trajectory statistics."""
        async with self.db.get_session() as session:
            total = await session.execute(select(func.count(Trajectory.id)))
            completed = await session.execute(
                select(func.count(Trajectory.id)).where(
                    Trajectory.status == MissionStatus.COMPLETED.value
                )
            )
            failed = await session.execute(
                select(func.count(Trajectory.id)).where(
                    Trajectory.status == MissionStatus.FAILED.value
                )
            )
            total_cost = await session.execute(
                select(func.sum(Trajectory.total_cost))
            )
            
            return {
                "total": total.scalar(),
                "completed": completed.scalar(),
                "failed": failed.scalar(),
                "total_cost": total_cost.scalar() or 0.0,
            }


class MissionStore:
    """Store and retrieve missions."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_mission(self, goal: str, scenario_type: str = None,
                             complexity: str = None,
                             config: Dict = None) -> str:
        """Create a new mission."""
        async with self.db.get_session() as session:
            mission = Mission(
                goal=goal,
                scenario_type=scenario_type,
                complexity=complexity,
                config=config or {},
            )
            session.add(mission)
            await session.commit()
            return mission.id
    
    async def update_mission(self, mission_id: str, **kwargs):
        """Update a mission."""
        async with self.db.get_session() as session:
            mission = await session.get(Mission, mission_id)
            if mission:
                for key, value in kwargs.items():
                    if hasattr(mission, key):
                        setattr(mission, key, value)
                await session.commit()
    
    async def get_mission(self, mission_id: str) -> Optional[Dict]:
        """Get a mission by ID."""
        async with self.db.get_session() as session:
            mission = await session.get(Mission, mission_id)
            return mission.to_dict() if mission else None
    
    async def get_all_missions(self, limit: int = 100) -> List[Dict]:
        """Get all missions."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(Mission).order_by(Mission.created_at.desc()).limit(limit)
            )
            return [m.to_dict() for m in result.scalars().all()]


class SkillStore:
    """Store and retrieve learned skills."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    async def create_skill(self, name: str, description: str,
                           steps: List[Dict], source_trajectory: str = None) -> str:
        """Create a new skill."""
        async with self.db.get_session() as session:
            skill = SkillModel(
                name=name,
                description=description,
                steps=steps,
                source_trajectory=source_trajectory,
            )
            session.add(skill)
            await session.commit()
            return skill.id
    
    async def get_skill(self, skill_id: str) -> Optional[Dict]:
        """Get a skill by ID."""
        async with self.db.get_session() as session:
            skill = await session.get(SkillModel, skill_id)
            return skill.to_dict() if skill else None
    
    async def get_all_skills(self) -> List[Dict]:
        """Get all skills."""
        async with self.db.get_session() as session:
            result = await session.execute(select(SkillModel))
            return [s.to_dict() for s in result.scalars().all()]
    
    async def verify_skill(self, skill_id: str, score: float):
        """Mark a skill as verified."""
        async with self.db.get_session() as session:
            skill = await session.get(SkillModel, skill_id)
            if skill:
                skill.verified = True
                skill.benchmark_score = score
                await session.commit()
