"""GridMind AI Platform — FastAPI server."""

from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gridmind.api import router
from gridmind.config import get_settings
from gridmind.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    yield
    # cleanup could go here (close Redis, etc.)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-Powered Smart Grid Management Platform — Load Prediction, Fault Detection, Renewable Integration",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.get("/", tags=["root"])
    def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
        }

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health():
        import datetime
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            service=settings.app_name,
            timestamp=datetime.datetime.utcnow().isoformat(),
        )

    return app


app = create_app()


def main():
    settings = get_settings()
    uvicorn.run(
        "gridmind.server:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
