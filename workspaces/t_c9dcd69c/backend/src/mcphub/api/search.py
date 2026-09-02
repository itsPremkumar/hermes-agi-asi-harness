"""Search API router."""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from mcphub.db.database import get_db_session
from mcphub.schemas import SearchQuery, SearchResult, ServerResponse
from mcphub.models import Server, ServerStatus
from sqlalchemy import select, or_, func

router = APIRouter()


async def get_session():
    async for session in get_db_session():
        yield session


@router.get("", response_model=SearchResult)
async def search_servers(
    q: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    transport: Optional[str] = None,
    sort: str = "relevance",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session=Depends(get_session),
):
    query = select(Server).where(Server.status == ServerStatus.APPROVED)
    count_query = select(func.count(Server.id)).where(Server.status == ServerStatus.APPROVED)

    if q:
        like = f"%{q}%"
        filter_ = or_(
            Server.name.ilike(like),
            Server.description.ilike(like),
            Server.author.ilike(like),
        )
        query = query.where(filter_)
        count_query = count_query.where(filter_)

    if category:
        query = query.where(Server.category == category)
        count_query = count_query.where(Server.category == category)

    if transport:
        query = query.where(Server.mcp_transport == transport)
        count_query = count_query.where(Server.mcp_transport == transport)

    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        for tag in tag_list:
            query = query.where(Server.tags.contains([tag]))
            count_query = count_query.where(Server.tags.contains([tag]))

    # Sorting
    if sort == "stars":
        query = query.order_by(Server.github_stars.desc())
    elif sort == "downloads":
        query = query.order_by(Server.downloads.desc())
    elif sort == "health":
        query = query.order_by(Server.health_score.desc())
    elif sort == "newest":
        query = query.order_by(Server.created_at.desc())
    else:
        query = query.order_by(Server.github_stars.desc())

    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    servers = result.scalars().all()

    total_result = await session.execute(count_query)
    total = total_result.scalar()

    # Build facets
    cat_result = await session.execute(
        select(Server.category, func.count(Server.id))
        .where(Server.status == ServerStatus.APPROVED)
        .group_by(Server.category)
    )
    facets = {"categories": {c or "uncategorized": cnt for c, cnt in cat_result.all()}}

    return SearchResult(
        total=total,
        page=page,
        per_page=per_page,
        results=[ServerResponse.model_validate(s) for s in servers],
        facets=facets,
    )
