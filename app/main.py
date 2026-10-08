from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.orders import router as orders_router
from app.api.simulation import router as simulation_router
from app.api.websocket import router as websocket_router
from app.baas.database import Database
from app.baas.queue import EventQueue
from app.faas.autoscaler import Autoscaler
from app.observability.event_log import EventLog
from app.observability.metrics import Metrics
from app.services.simulation_service import SimulationService
from app.services.workspace_manager import WorkspaceManager

app = FastAPI(title="Serverless Lab")

database = Database()
queue = EventQueue()
metrics = Metrics()
event_log = EventLog()
workspace_manager = WorkspaceManager()

autoscaler = Autoscaler(
    queue,
    database,
    metrics,
    event_log,
)

simulation = SimulationService(
    queue,
    autoscaler,
    metrics,
    event_log,
)

app.state.database = database
app.state.queue = queue
app.state.metrics = metrics
app.state.event_log = event_log
app.state.workspace_manager = workspace_manager
app.state.autoscaler = autoscaler
app.state.simulation = simulation

app.include_router(orders_router)
app.include_router(simulation_router)
app.include_router(websocket_router)

frontend = Path("app/frontend")

app.mount(
    "/static",
    StaticFiles(directory=frontend),
    name="static",
)

@app.get("/")
async def index():
    return FileResponse(frontend / "index.html")