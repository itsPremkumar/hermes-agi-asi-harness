"""Database connection and session management."""
import os
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://mcphub:mcphub@localhost:5432/mcphub",
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=20)
async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Test override
_test_session_factory: Optional[sessionmaker] = None


def set_test_session_factory(factory: Optional[sessionmaker]):
    """Set a test session factory (call with None to reset)."""
    global _test_session_factory
    _test_session_factory = factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for dependency injection."""
    factory = _test_session_factory or async_session_factory
    async with factory() as session:
        yield session


class Database:
    """Async database helper."""

    async def connect(self):
        pass

    async def disconnect(self):
        await engine.dispose()

    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async for s in get_db_session():
            yield s


database = Database()
