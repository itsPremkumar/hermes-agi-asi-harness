"""Tests for MCPHub API."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from mcphub.main import app
from mcphub.models import Base, Server, ServerStatus
from mcphub.db import database, set_test_session_factory

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_mcphub.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_session():
    async with test_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
def use_test_db():
    """Switch to test database for all tests."""
    set_test_session_factory(test_session_factory)
    yield
    set_test_session_factory(None)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test and drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "MCPHub"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_healthz(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_list_servers_empty(client):
    resp = await client.get("/api/v1/servers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["servers"] == []


@pytest.mark.asyncio
async def test_create_server(client):
    payload = {
        "name": "TestServer",
        "description": "A test MCP server",
        "author": "testuser",
        "category": "developer-tools",
        "tags": ["test", "mcp"],
    }
    resp = await client.post("/api/v1/servers", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "TestServer"
    assert data["slug"] == "testserver"
    assert data["status"] == "approved"


@pytest.mark.asyncio
async def test_get_server(client):
    # Create first
    payload = {
        "name": "GetTestServer",
        "description": "Test get",
        "author": "testuser",
    }
    resp = await client.post("/api/v1/servers", json=payload)
    server_id = resp.json()["id"]

    # Get by ID
    resp = await client.get(f"/api/v1/servers/{server_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetTestServer"


@pytest.mark.asyncio
async def test_get_server_not_found(client):
    resp = await client.get("/api/v1/servers/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_server(client):
    payload = {"name": "UpdateTest", "author": "testuser"}
    resp = await client.post("/api/v1/servers", json=payload)
    server_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/servers/{server_id}", json={"description": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated"


@pytest.mark.asyncio
async def test_delete_server(client):
    payload = {"name": "DeleteTest", "author": "testuser"}
    resp = await client.post("/api/v1/servers", json=payload)
    server_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/servers/{server_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/servers/{server_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_servers(client):
    # Create test servers
    for i in range(3):
        await client.post("/api/v1/servers", json={
            "name": f"SearchServer{i}",
            "description": f"Search test {i}",
            "author": "searchuser",
            "category": "search",
        })

    resp = await client.get("/api/v1/search?q=SearchServer")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_create_submission(client):
    payload = {
        "name": "NewSubmission",
        "description": "A submitted server",
        "author": "submitter",
    }
    resp = await client.post("/api/v1/submissions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "NewSubmission"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_review_submission(client):
    # Create submission
    payload = {"name": "ReviewMe", "author": "submitter"}
    resp = await client.post("/api/v1/submissions", json=payload)
    sub_id = resp.json()["id"]

    # Approve it
    resp = await client.post(f"/api/v1/submissions/{sub_id}/review", json={
        "status": "approved",
        "review_notes": "Looks good",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_analytics_summary(client):
    resp = await client.get("/api/v1/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_servers" in data
    assert "total_downloads" in data


@pytest.mark.asyncio
async def test_track_download(client):
    payload = {"name": "DownloadTest", "author": "testuser"}
    resp = await client.post("/api/v1/servers", json=payload)
    server_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/servers/{server_id}/download")
    assert resp.status_code == 200
    assert resp.json()["downloads"] == 1


@pytest.mark.asyncio
async def test_add_version(client):
    payload = {"name": "VersionTest", "author": "testuser"}
    resp = await client.post("/api/v1/servers", json=payload)
    server_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/servers/{server_id}/versions", json={
        "version": "2.0.0",
        "changelog": "Major update",
    })
    assert resp.status_code == 201
    assert resp.json()["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_list_versions(client):
    payload = {"name": "VersionListTest", "author": "testuser"}
    resp = await client.post("/api/v1/servers", json=payload)
    server_id = resp.json()["id"]

    await client.post(f"/api/v1/servers/{server_id}/versions", json={"version": "1.0.0"})
    await client.post(f"/api/v1/servers/{server_id}/versions", json={"version": "2.0.0"})

    resp = await client.get(f"/api/v1/servers/{server_id}/versions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_discover_topics(client):
    resp = await client.get("/api/v1/discover/topics")
    assert resp.status_code == 200
    assert "topics" in resp.json()
