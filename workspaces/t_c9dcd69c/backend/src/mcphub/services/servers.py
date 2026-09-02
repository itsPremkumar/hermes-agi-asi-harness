"""Service layer for server operations."""
import uuid
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from mcphub.models import Server, ServerVersion, HealthCheck, AnalyticsEvent, Submission, ServerStatus
from mcphub.schemas import ServerCreate, ServerUpdate, ServerListResponse, ServerResponse


def slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


async def list_servers(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort: str = "newest",
) -> ServerListResponse:
    query = select(Server)
    count_query = select(func.count(Server.id))

    filters = []
    if status:
        filters.append(Server.status == ServerStatus(status))
    else:
        filters.append(Server.status == ServerStatus.APPROVED)
    if category:
        filters.append(Server.category == category)
    if tag:
        filters.append(Server.tags.contains([tag]))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Sorting
    if sort == "stars":
        query = query.order_by(Server.github_stars.desc())
    elif sort == "downloads":
        query = query.order_by(Server.downloads.desc())
    elif sort == "health":
        query = query.order_by(Server.health_score.desc())
    else:
        query = query.order_by(Server.created_at.desc())

    # Pagination
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    servers = result.scalars().all()

    total_result = await session.execute(count_query)
    total = total_result.scalar()

    return ServerListResponse(
        total=total,
        page=page,
        per_page=per_page,
        servers=[ServerResponse.model_validate(s) for s in servers],
    )


async def get_server(session: AsyncSession, server_id: str) -> Optional[Server]:
    result = await session.execute(select(Server).where(Server.id == server_id))
    return result.scalar_one_or_none()


async def get_server_by_slug(session: AsyncSession, slug: str) -> Optional[Server]:
    result = await session.execute(select(Server).where(Server.slug == slug))
    return result.scalar_one_or_none()


async def create_server(session: AsyncSession, data: ServerCreate, submitted_by: Optional[str] = None) -> Server:
    server = Server(
        id=str(uuid.uuid4()),
        slug=slugify(data.name),
        name=data.name,
        description=data.description,
        long_description=data.long_description,
        author=data.author,
        author_github=data.author_github,
        repository_url=str(data.repository_url) if data.repository_url else None,
        homepage_url=str(data.homepage_url) if data.homepage_url else None,
        version=data.version,
        license=data.license,
        mcp_transport=data.mcp_transport,
        install_command=data.install_command,
        tags=data.tags,
        category=data.category,
        status=ServerStatus.APPROVED,
        submitted_by=submitted_by,
    )
    session.add(server)
    await session.commit()
    await session.refresh(server)
    return server


async def update_server(session: AsyncSession, server_id: str, data: ServerUpdate) -> Optional[Server]:
    server = await get_server(session, server_id)
    if not server:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "status" and value:
            value = ServerStatus(value)
        setattr(server, key, value)

    server.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(server)
    return server


async def delete_server(session: AsyncSession, server_id: str) -> bool:
    result = await session.execute(delete(Server).where(Server.id == server_id))
    await session.commit()
    return result.rowcount > 0


async def increment_downloads(session: AsyncSession, server_id: str):
    await session.execute(
        update(Server)
        .where(Server.id == server_id)
        .values(downloads=Server.downloads + 1)
    )
    await session.commit()


async def log_event(
    session: AsyncSession,
    event_type: str,
    server_id: Optional[str] = None,
    ip_hash: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[Dict] = None,
):
    event = AnalyticsEvent(
        id=str(uuid.uuid4()),
        server_id=server_id,
        event_type=event_type,
        ip_hash=ip_hash,
        user_agent=user_agent,
        metadata_json=metadata or {},
    )
    session.add(event)
    await session.commit()


# --- Submissions ---
async def create_submission(session: AsyncSession, data) -> Submission:
    sub = Submission(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        author=data.author,
        repository_url=str(data.repository_url) if data.repository_url else None,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


async def review_submission(session: AsyncSession, sub_id: str, status: str, notes: str, reviewer: str) -> Optional[Submission]:
    result = await session.execute(select(Submission).where(Submission.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        return None

    sub.status = ServerStatus(status)
    sub.review_notes = notes
    sub.reviewed_by = reviewer
    sub.reviewed_at = datetime.utcnow()

    if status == "approved":
        # Auto-create server from approved submission
        server = Server(
            id=str(uuid.uuid4()),
            slug=slugify(sub.name),
            name=sub.name,
            description=sub.description,
            author=sub.author,
            repository_url=sub.repository_url,
            status=ServerStatus.APPROVED,
            submitted_by=sub.author,
            is_discovered=True,
        )
        session.add(server)
        await session.flush()
        sub.server_id = server.id

    await session.commit()
    await session.refresh(sub)
    return sub


async def list_submissions(session: AsyncSession, status_filter: Optional[str] = None, limit: int = 50) -> List[Submission]:
    query = select(Submission).order_by(Submission.created_at.desc()).limit(limit)
    if status_filter:
        query = query.where(Submission.status == ServerStatus(status_filter))
    result = await session.execute(query)
    return result.scalars().all()


# --- Versions ---
async def add_version(session: AsyncSession, server_id: str, data) -> Optional[ServerVersion]:
    ver = ServerVersion(
        id=str(uuid.uuid4()),
        server_id=server_id,
        version=data.version,
        changelog=data.changelog,
        is_prerelease=data.is_prerelease,
        metadata_json=data.metadata_json,
    )
    session.add(ver)
    await session.commit()
    await session.refresh(ver)
    return ver


async def list_versions(session: AsyncSession, server_id: str) -> List[ServerVersion]:
    result = await session.execute(
        select(ServerVersion)
        .where(ServerVersion.server_id == server_id)
        .order_by(ServerVersion.published_at.desc())
    )
    return result.scalars().all()


# --- Health ---
async def record_health_check(session: AsyncSession, server_id: str, status_code: Optional[int], response_time: float, is_up: bool, error: Optional[str] = None):
    check = HealthCheck(
        id=str(uuid.uuid4()),
        server_id=server_id,
        status_code=status_code,
        response_time_ms=response_time,
        is_up=is_up,
        error_message=error,
    )
    session.add(check)

    # Update server health score
    score = 100.0 if is_up else 0.0
    await session.execute(
        update(Server)
        .where(Server.id == server_id)
        .values(health_score=score, last_health_check=datetime.utcnow())
    )
    await session.commit()


async def get_health_summary(session: AsyncSession, server_id: str) -> Optional[Dict[str, Any]]:
    server = await get_server(session, server_id)
    if not server:
        return None

    # Last 24h checks
    since = datetime.utcnow() - timedelta(hours=24)
    result = await session.execute(
        select(func.count(HealthCheck.id), func.avg(HealthCheck.response_time_ms))
        .where(and_(HealthCheck.server_id == server_id, HealthCheck.checked_at >= since))
    )
    total, avg_rt = result.first() or (0, 0)

    up_result = await session.execute(
        select(func.count(HealthCheck.id))
        .where(and_(HealthCheck.server_id == server_id, HealthCheck.is_up == True, HealthCheck.checked_at >= since))
    )
    up_count = up_result.scalar() or 0

    uptime = (up_count / total * 100) if total > 0 else 0

    return {
        "server_id": server_id,
        "server_name": server.name,
        "uptime_percentage": round(uptime, 2),
        "avg_response_time_ms": round(avg_rt or 0, 2),
        "last_check": server.last_health_check,
        "total_checks": total,
        "is_currently_up": server.health_score > 0,
    }


# --- Analytics ---
async def get_analytics_summary(session: AsyncSession) -> Dict[str, Any]:
    servers_count = await session.execute(select(func.count(Server.id)))
    downloads = await session.execute(select(func.sum(Server.downloads)))
    views = await session.execute(
        select(func.count(AnalyticsEvent.id)).where(AnalyticsEvent.event_type == "view")
    )

    # Top servers by downloads
    top_result = await session.execute(
        select(Server.name, Server.downloads)
        .where(Server.status == ServerStatus.APPROVED)
        .order_by(Server.downloads.desc())
        .limit(10)
    )
    top_servers = [{"name": n, "downloads": d} for n, d in top_result.all()]

    # Category distribution
    cat_result = await session.execute(
        select(Server.category, func.count(Server.id))
        .group_by(Server.category)
    )
    cats = {c or "uncategorized": cnt for c, cnt in cat_result.all()}

    # Daily events (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    daily_result = await session.execute(
        select(
            func.strftime('%Y-%m-%d', AnalyticsEvent.created_at).label('day'),
            func.count(AnalyticsEvent.id),
        )
        .where(AnalyticsEvent.created_at >= week_ago)
        .group_by('day')
        .order_by('day')
    )
    daily = [{"day": str(d), "count": c} for d, c in daily_result.all()]

    return {
        "total_servers": servers_count.scalar() or 0,
        "total_downloads": downloads.scalar() or 0,
        "total_views": views.scalar() or 0,
        "top_servers": top_servers,
        "category_distribution": cats,
        "daily_events": daily,
    }
