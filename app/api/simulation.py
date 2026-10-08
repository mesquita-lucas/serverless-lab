from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api")

class LoadRequest(BaseModel):
    workspace_id: str
    amount: int

class ConfigRequest(BaseModel):
    workspace_id: str
    discount_threshold: float
    discount_percent: float
    processing_time_ms: int
    cold_start_ms: int
    max_instances: int
    idle_timeout_seconds: int

@router.post("/workspaces")
async def create_workspace(request: Request):
    manager = request.app.state.workspace_manager
    workspace = manager.create()

    return {
        "workspace_id": workspace.id,
    }

@router.post("/simulate")
async def simulate_load(
    body: LoadRequest,
    request: Request,
):
    manager = request.app.state.workspace_manager
    simulation = request.app.state.simulation

    workspace = manager.get(body.workspace_id)

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    simulation.start(workspace)

    await simulation.simulate_load(
        workspace,
        body.amount,
    )

    return {
        "queued": body.amount,
    }

@router.put("/function-config")
async def update_function(
    body: ConfigRequest,
    request: Request,
):
    manager = request.app.state.workspace_manager

    workspace = manager.update_config(
        body.workspace_id,
        discount_threshold=body.discount_threshold,
        discount_percent=body.discount_percent,
        processing_time_ms=body.processing_time_ms,
        cold_start_ms=body.cold_start_ms,
        max_instances=body.max_instances,
        idle_timeout_seconds=body.idle_timeout_seconds,
    )

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return {
        "status": "updated",
    }