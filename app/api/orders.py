from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/orders")

class OrderRequest(BaseModel):
    workspace_id: str
    product: str
    quantity: int
    unit_price: float

@router.post("")
async def create_order(
    body: OrderRequest,
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

    order = await simulation.submit_order(
        workspace,
        body.product,
        body.quantity,
        body.unit_price,
    )

    return {
        "order_id": order.id,
        "status": "queued",
    }