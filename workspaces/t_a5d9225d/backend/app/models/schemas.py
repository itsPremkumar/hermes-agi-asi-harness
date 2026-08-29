"""Pydantic models for ChainForge."""
from pydantic import BaseModel, Field
from typing import Any
from enum import Enum
from datetime import datetime


class NodeType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    LOOP = "loop"
    CONDITION = "condition"
    INPUT = "input"
    OUTPUT = "output"
    TRANSFORM = "transform"
    HTTP = "http"
    CODE = "code"
    DELAY = "delay"
    WEBHOOK = "webhook"
    SWITCH = "switch"
    MERGE = "merge"
    SPLIT = "split"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    DATABASE = "database"
    FILE = "file"
    EMAIL = "email"
    SCHEDULER = "scheduler"
    CUSTOM = "custom"


class NodeStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


class Position(BaseModel):
    x: float = 0
    y: float = 0


class NodePort(BaseModel):
    id: str
    name: str
    type: str = "any"  # any, string, number, boolean, array, object
    required: bool = False


class WorkflowNode(BaseModel):
    id: str
    type: str
    name: str = ""
    position: Position = Position()
    data: dict[str, Any] = {}
    inputs: list[NodePort] = []
    outputs: list[NodePort] = []
    status: NodeStatus = NodeStatus.IDLE


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: str | None = None
    targetHandle: str | None = None
    label: str | None = None


class Workflow(BaseModel):
    id: str
    name: str
    description: str = ""
    nodes: list[WorkflowNode] = []
    edges: list[WorkflowEdge] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    tags: list[str] = []


class ExecutionResult(BaseModel):
    node_id: str
    status: NodeStatus
    output: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0


class WorkflowExecution(BaseModel):
    id: str
    workflow_id: str
    status: NodeStatus = NodeStatus.RUNNING
    results: list[ExecutionResult] = []
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    total_duration_ms: int = 0


class Template(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = "general"
    workflow: Workflow
    author: str = "ChainForge"
    downloads: int = 0
    tags: list[str] = []


class ExportRequest(BaseModel):
    workflow_id: str
    format: str = "python"  # python, json, yaml


class DeployRequest(BaseModel):
    workflow_id: str
    target: str = "docker"  # docker, kubernetes, lambda
