"""REST API & WebSocket Server - FastAPI-based API for external integration."""
from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import asyncio, json, uuid

app = FastAPI(title="Hermes AGI/ASI Master API", version="12.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state (replace with DB in production)
missions: Dict[str, Any] = {}
ws_connections: List[WebSocket] = []

class CreateMissionRequest(BaseModel):
    goal: str
    config: Optional[Dict] = None

class MissionResponse(BaseModel):
    id: str
    goal: str
    status: str
    result: Optional[Dict] = None

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "12.0"}

@app.get("/api/missions")
async def list_missions():
    return list(missions.values())

@app.post("/api/missions")
async def create_mission(request: CreateMissionRequest):
    mission_id = str(uuid.uuid4())
    mission = {
        "id": mission_id,
        "goal": request.goal,
        "status": "pending",
        "config": request.config or {},
        "result": None,
    }
    missions[mission_id] = mission
    return mission

@app.get("/api/missions/{mission_id}")
async def get_mission(mission_id: str):
    if mission_id not in missions:
        raise HTTPException(status_code=404, detail="Mission not found")
    return missions[mission_id]

@app.delete("/api/missions/{mission_id}")
async def delete_mission(mission_id: str):
    if mission_id in missions:
        del missions[mission_id]
    return {"status": "deleted"}

@app.websocket("/ws/missions/{mission_id}")
async def mission_websocket(websocket: WebSocket, mission_id: str):
    await websocket.accept()
    ws_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages
            await websocket.send_json({"echo": data})
    except WebSocketDisconnect:
        ws_connections.remove(websocket)

@app.get("/api/stats")
async def get_stats():
    return {
        "total_missions": len(missions),
        "active_missions": sum(1 for m in missions.values() if m["status"] == "running"),
        "completed_missions": sum(1 for m in missions.values() if m["status"] == "completed"),
    }

def run_api(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
