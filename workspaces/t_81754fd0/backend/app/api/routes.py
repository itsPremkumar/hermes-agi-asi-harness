"""API routes for UIGenerator."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.app.models.schemas import (
    ComponentListResponse,
    ExportRequest,
    ExportResponse,
    Framework,
    GenerationRequest,
    GenerationResponse,
    HealthResponse,
)
from backend.app.services.component_library import library
from backend.app.services.generation import generation_service

api_router = APIRouter()


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Health check endpoint."""
    import time
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=time.time() % 100000,
    )


@api_router.post("/generate", response_model=GenerationResponse, tags=["generation"])
async def generate(request: GenerationRequest) -> GenerationResponse:
    """Generate UI from a natural-language description."""
    try:
        return generation_service.generate(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/generate/{gen_id}", response_model=GenerationResponse, tags=["generation"])
async def get_generation(gen_id: str) -> GenerationResponse:
    """Retrieve a previous generation by ID."""
    result = generation_service.get_generation(gen_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Generation not found")
    return result


@api_router.post("/export", response_model=ExportResponse, tags=["export"])
async def export_code(request: ExportRequest) -> ExportResponse:
    """Export a generation in a specific framework."""
    try:
        return generation_service.export(request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/components", response_model=ComponentListResponse, tags=["components"])
async def list_components(
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search query"),
    limit: int = Query(50, ge=1, le=500),
) -> ComponentListResponse:
    """List components with optional filtering."""
    if search:
        comps = library.search(search, limit=limit)
    elif category:
        comps = library.by_category(category)[:limit]
    else:
        comps = library.list_all()[:limit]

    return ComponentListResponse(
        total=library.total,
        components=comps,
        categories=library.categories(),
    )


@api_router.get("/components/{comp_id}")
async def get_component(comp_id: str):
    """Get a single component by ID."""
    comp = library.get(comp_id)
    if comp is None:
        raise HTTPException(status_code=404, detail="Component not found")
    return comp


@api_router.get("/categories", tags=["components"])
async def list_categories() -> dict[str, int]:
    """List all component categories with counts."""
    return {cat: len(library.by_category(cat)) for cat in library.categories()}


@api_router.get("/frameworks", tags=["system"])
async def list_frameworks() -> list[dict[str, str]]:
    """List supported export frameworks."""
    return [
        {"id": f.value, "name": f.name, "label": f.value.replace("_", " + ").title()}
        for f in Framework
    ]
