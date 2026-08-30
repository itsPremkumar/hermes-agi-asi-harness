"""Database models for MCPHub."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Float, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class ServerStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class Server(Base):
    __tablename__ = "servers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    long_description = Column(Text, nullable=True)
    author = Column(String(255), nullable=False)
    author_github = Column(String(255), nullable=True)
    repository_url = Column(String(500), nullable=True)
    homepage_url = Column(String(500), nullable=True)
    version = Column(String(50), default="1.0.0")
    license = Column(String(100), default="MIT")
    status = Column(SQLEnum(ServerStatus), default=ServerStatus.PENDING, index=True)
    mcp_transport = Column(String(50), default="stdio")  # stdio, http, sse
    install_command = Column(String(500), nullable=True)
    tags = Column(JSON, default=list)
    category = Column(String(100), nullable=True, index=True)
    github_stars = Column(Integer, default=0)
    github_forks = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    health_score = Column(Float, default=0.0)
    last_health_check = Column(DateTime, nullable=True)
    is_discovered = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_by = Column(String(255), nullable=True)

    submissions = relationship("Submission", back_populates="server", cascade="all, delete-orphan")
    versions = relationship("ServerVersion", back_populates="server", cascade="all, delete-orphan")
    health_checks = relationship("HealthCheck", back_populates="server", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_id = Column(String, ForeignKey("servers.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=False)
    repository_url = Column(String(500), nullable=True)
    status = Column(SQLEnum(ServerStatus), default=ServerStatus.PENDING)
    review_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    server = relationship("Server", back_populates="submissions")


class ServerVersion(Base):
    __tablename__ = "server_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_id = Column(String, ForeignKey("servers.id"), nullable=False)
    version = Column(String(50), nullable=False)
    changelog = Column(Text, nullable=True)
    is_prerelease = Column(Boolean, default=False)
    published_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)

    server = relationship("Server", back_populates="versions")


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_id = Column(String, ForeignKey("servers.id"), nullable=False)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    is_up = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)

    server = relationship("Server", back_populates="health_checks")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_id = Column(String, ForeignKey("servers.id"), nullable=True)
    event_type = Column(String(50), nullable=False, index=True)  # view, install, search, api_call
    ip_hash = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
