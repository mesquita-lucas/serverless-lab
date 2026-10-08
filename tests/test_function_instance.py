import pytest

from app.faas.function_instance import (
    FunctionInstance,
)
from app.faas.function_status import (
    FunctionStatus,
)
from app.models.order import Order
from app.models.workspace import Workspace


@pytest.mark.asyncio
async def test_function_lifecycle(
    runtime,
):
    workspace = Workspace()

    workspace.config.cold_start_ms = 1
    workspace.config.processing_time_ms = 1

    instance = FunctionInstance(
        workspace,
        runtime["database"],
        runtime["metrics"],
        runtime["event_log"],
    )

    assert (
        instance.status
        == FunctionStatus.CREATED
    )

    await instance.initialize()

    assert (
        instance.status
        == FunctionStatus.IDLE
    )

    assert instance.warm
    assert not instance.busy

    order = Order(
        workspace_id=workspace.id,
        product="Ingresso",
        quantity=1,
        unit_price=100,
    )

    instance.reserve()

    assert (
        instance.status
        == FunctionStatus.BUSY
    )

    assert instance.busy

    await instance.invoke(
        order
    )

    assert (
        instance.status
        == FunctionStatus.IDLE
    )

    assert not instance.busy


@pytest.mark.asyncio
async def test_function_cannot_be_reserved_twice(
    runtime,
):
    workspace = Workspace()

    workspace.config.cold_start_ms = 1

    instance = FunctionInstance(
        workspace,
        runtime["database"],
        runtime["metrics"],
        runtime["event_log"],
    )

    await instance.initialize()

    instance.reserve()

    with pytest.raises(
        RuntimeError
    ):
        instance.reserve()


@pytest.mark.asyncio
async def test_one_cold_start_per_instance(
    runtime,
):
    workspace = Workspace()

    workspace.config.cold_start_ms = 1

    instance = FunctionInstance(
        workspace,
        runtime["database"],
        runtime["metrics"],
        runtime["event_log"],
    )

    await instance.initialize()
    await instance.initialize()

    metrics = runtime["metrics"].get(
        workspace.id
    )

    assert (
        metrics["cold_starts"]
        == 1
    )

class BrokenDatabase:
    def save_order(
        self,
        order,
    ):
        raise RuntimeError(
            "Database failure"
        )

@pytest.mark.asyncio
async def test_function_returns_to_idle_after_error(
    runtime,
):
    workspace = Workspace()

    workspace.config.cold_start_ms = 1
    workspace.config.processing_time_ms = 1

    instance = FunctionInstance(
        workspace,
        BrokenDatabase(),
        runtime["metrics"],
        runtime["event_log"],
    )

    await instance.initialize()

    order = Order(
        workspace_id=workspace.id,
        product="Ingresso",
        quantity=1,
        unit_price=100,
    )

    instance.reserve()

    await instance.invoke(
        order
    )

    assert (
        instance.status
        == FunctionStatus.IDLE
    )

    metrics = runtime["metrics"].get(
        workspace.id
    )

    assert metrics["errors"] == 1