"""Pydantic schemas for MCPHub API."""
from datetime import datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, Field, HttpUrl


# Server schemas
class ServerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    long_description: Optional[str] = None
    author: str = Field(..., min_length=1, max_length=255)
    author_github: Optional[str] = None
    repository_url: Optional[HttpUrl] = None
    homepage_url: Optional[HttpUrl] = None
    version: str = "1.0.0"
    license: str = "MIT"
    mcp_transport: str = "stdio"
    install_command: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None


class ServerCreate(ServerBase):
    pass


class ServerUpdate(BaseModel):
    description: Optional[str] = None
    long_description: Optional[str] = None
    version: Optional[str] = None
    license: Optional[str] = None
    install_command: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    status: Optional[str] = None


class ServerResponse(ServerBase):
    id: str
    slug: str
    status: str
    github_stars: int = 0
    github_forks: int = 0
    downloads: int = 0
    health_score: float = 0.0
    last_health_check: Optional[datetime] = None
    is_discovered: bool = False
    is_featured: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ServerListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    servers: List[ServerResponse]


# Search schemas
class SearchQuery(BaseModel):
    q: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    transport: Optional[str] = None
    sort: str = "relevance"  # relevance, stars, downloads, newest
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class SearchResult(BaseModel):
    total: int
    page: int
    per_page: int
    results: List[ServerResponse]
    facets: Dict[str, Any] = Field(default_factory=dict)


# Submission schemas
class SubmissionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    author: str = Field(..., min_length=1, max_length=255)
    repository_url: Optional[HttpUrl] = None


class SubmissionReview(BaseModel):
    status: str  # approved, rejected
    review_notes: Optional[str] = None


class SubmissionResponse(BaseModel):
    id: str
    server_id: Optional[str]
    name: str
    description: Optional[str]
    author: str
    repository_url: Optional[str]
    status: str
    review_notes: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Health schemas
class HealthCheckResponse(BaseModel):
    id: str
    server_id: str
    status_code: Optional[int]
    response_time_ms: Optional[float]
    is_up: bool
    error_message: Optional[str]
    checked_at: datetime

    class Config:
        from_attributes = True


class ServerHealthSummary(BaseModel):
    server_id: str
    server_name: str
    uptime_percentage: float
    avg_response_time_ms: float
    last_check: Optional[datetime]
    total_checks: int
    is_currently_up: bool


# Analytics schemas
class AnalyticsEventCreate(BaseModel):
    server_id: Optional[str] = None
    event_type: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class AnalyticsSummary(BaseModel):
    total_servers: int
    total_downloads: int
    total_views: int
    top_servers: List[Dict[str, Any]]
    category_distribution: Dict[str, int]
    daily_events: List[Dict[str, Any]]


# Discover schemas
class DiscoverRequest(BaseModel):
    github_topic: str = "mcp-server"
    max_results: int = Field(50, ge=1, le=200)


class DiscoverResult(BaseModel):
    discovered: int
    new_servers: List[Dict[str, Any]]


# Version schemas
class VersionCreate(BaseModel):
    version: str
    changelog: Optional[str] = None
    is_prerelease: bool = False
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class VersionResponse(BaseModel):
    id: str
    server_id: str
    version: str
    changelog: Optional[str]
    is_prerelease: bool
    published_at: datetime
    metadata_json: Dict[str, Any]

    class Config:
        from_attributes = True
