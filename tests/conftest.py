import pytest

from app.baas.database import Database
from app.baas.queue import EventQueue
from app.faas.autoscaler import Autoscaler
from app.observability.event_log import EventLog
from app.observability.metrics import Metrics
from app.services.simulation_service import (
    SimulationService,
)

@pytest.fixture
def runtime(tmp_path):
    database = Database(
        tmp_path / "test.db"
    )

    queue = EventQueue()
    metrics = Metrics()
    event_log = EventLog()

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
        database,
    )

    return {
        "database": database,
        "queue": queue,
        "metrics": metrics,
        "event_log": event_log,
        "autoscaler": autoscaler,
        "simulation": simulation,
    }