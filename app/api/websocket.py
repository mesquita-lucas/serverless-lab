import asyncio

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

router = APIRouter()

@router.websocket(
    "/ws/{workspace_id}"
)
async def workspace_socket(
    websocket: WebSocket,
    workspace_id: str,
):
    await websocket.accept()

    app = websocket.scope["app"]

    metrics = app.state.metrics
    event_log = app.state.event_log
    autoscaler = app.state.autoscaler
    manager = app.state.workspace_manager

    workspace = manager.get(
        workspace_id
    )

    if not workspace:
        await websocket.close(
            code=1008
        )
        return

    try:
        while True:
            manager.get(
                workspace_id
            )

            instances = (
                autoscaler.get_instances(
                    workspace_id
                )
            )

            await websocket.send_json(
                {
                    "metrics": metrics.get(
                        workspace_id
                    ),
                    "instances": [
                        {
                            "id": instance.id,
                            "status": (
                                instance.status.value
                            ),
                            "warm": instance.warm,
                            "busy": instance.busy,
                        }
                        for instance
                        in instances
                    ],
                    "logs": event_log.get(
                        workspace_id
                    )[-20:],
                }
            )

            await asyncio.sleep(
                0.25
            )

    except WebSocketDisconnect:
        pass