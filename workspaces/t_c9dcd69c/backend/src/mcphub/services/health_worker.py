"""Health monitoring background worker for MCPHub."""
import asyncio
import os
import time
from datetime import datetime

import httpx

from mcphub.db.database import async_session, engine
from mcphub.models import Server
from sqlalchemy import select


async def check_server_health(server: Server) -> dict:
    """Check health of a single server."""
    url = server.homepage_url or server.repository_url
    if not url:
        return {"is_up": False, "status_code": None, "response_time_ms": 0, "error": "No URL"}

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(str(url))
            elapsed = (time.time() - start) * 1000
            return {
                "is_up": resp.status_code < 500,
                "status_code": resp.status_code,
                "response_time_ms": elapsed,
                "error": None,
            }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return {
            "is_up": False,
            "status_code": None,
            "response_time_ms": elapsed,
            "error": str(e),
        }


async def run_health_checks():
    """Run health checks for all approved servers."""
    from mcphub.services.servers import record_health_check

    async with async_session() as session:
        result = await session.execute(
            select(Server).where(Server.status == "approved")
        )
        servers = result.scalars().all()

        for server in servers:
            health = await check_server_health(server)
            await record_health_check(
                session,
                server.id,
                health["status_code"],
                health["response_time_ms"],
                health["is_up"],
                health["error"],
            )


async def main():
    """Main loop for health worker."""
    while True:
        try:
            await run_health_checks()
        except Exception as e:
            print(f"Health check error: {e}")
        await asyncio.sleep(300)  # Run every 5 minutes


if __name__ == "__main__":
    asyncio.run(main())
