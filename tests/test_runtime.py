import asyncio

import pytest

from app.models.workspace import Workspace

async def wait_until(
    condition,
    timeout=10,
    interval=0.01,
):
    loop = asyncio.get_running_loop()
    started = loop.time()

    while True:
        if condition():
            return

        if (
            loop.time() - started
            > timeout
        ):
            raise TimeoutError(
                "Condition was not reached"
            )

        await asyncio.sleep(
            interval
        )

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "amount",
    [1, 10, 100, 500],
)
async def test_processes_all_orders(
    runtime,
    amount,
):
    workspace = Workspace()

    workspace.config.cold_start_ms = 1
    workspace.config.processing_time_ms = 1
    workspace.config.max_instances = 10
    workspace.config.idle_timeout_seconds = 0.1

    simulation = runtime["simulation"]

    simulation.start(
        workspace
    )

    await simulation.simulate_load(
        workspace,
        amount,
    )

    await wait_until(
        lambda: (
            runtime["metrics"]
            .get(workspace.id)["processed"]
            == amount
        )
    )

    metrics = runtime["metrics"].get(
        workspace.id
    )

    orders = runtime[
        "database"
    ].list_orders(
        workspace.id
    )

    assert metrics["requests"] == amount
    assert metrics["processed"] == amount
    assert metrics["queued"] == 0
    assert metrics["errors"] == 0

    assert len(orders) == amount

    order_ids = [
        order[0]
        for order in orders
    ]

    assert (
        len(order_ids)
        == len(set(order_ids))
    )

    await simulation.stop(
        workspace.id
    )

@pytest.mark.asyncio
async def test_respects_max_instances(
    runtime,
):
    workspace = Workspace()

    workspace.config.cold_start_ms = 1
    workspace.config.processing_time_ms = 20
    workspace.config.max_instances = 3
    workspace.config.idle_timeout_seconds = 1

    simulation = runtime["simulation"]

    simulation.start(
        workspace
    )

    await simulation.simulate_load(
        workspace,
        100,
    )

    maximum_seen = 0

    while (
        runtime["metrics"]
        .get(workspace.id)["processed"]
        < 100
    ):
        amount = len(
            runtime[
                "autoscaler"
            ].get_instances(
                workspace.id
            )
        )

        maximum_seen = max(
            maximum_seen,
            amount,
        )

        await asyncio.sleep(
            0.01
        )

    assert maximum_seen <= 3

    await simulation.stop(
        workspace.id
    )

@pytest.mark.asyncio
async def test_scales_down_to_zero(
    runtime,
):
    workspace = Workspace()

    workspace.config.cold_start_ms = 1
    workspace.config.processing_time_ms = 1
    workspace.config.max_instances = 2
    workspace.config.idle_timeout_seconds = 0.05

    simulation = runtime["simulation"]

    simulation.start(
        workspace
    )

    await simulation.simulate_load(
        workspace,
        10,
    )

    await wait_until(
        lambda: (
            runtime["metrics"]
            .get(workspace.id)["processed"]
            == 10
        )
    )

    await wait_until(
        lambda: (
            runtime["metrics"]
            .get(workspace.id)[
                "active_instances"
            ]
            == 0
        ),
        timeout=3,
    )

    assert (
        len(
            runtime[
                "autoscaler"
            ].get_instances(
                workspace.id
            )
        )
        == 0
    )

    await simulation.stop(
        workspace.id
    )

@pytest.mark.asyncio
async def test_workspace_isolation(
    runtime,
):
    workspace_a = Workspace()
    workspace_b = Workspace()

    for workspace in (
        workspace_a,
        workspace_b,
    ):
        workspace.config.cold_start_ms = 1
        workspace.config.processing_time_ms = 1
        workspace.config.max_instances = 3
        workspace.config.idle_timeout_seconds = 1

    simulation = runtime["simulation"]

    simulation.start(
        workspace_a
    )

    simulation.start(
        workspace_b
    )

    await simulation.simulate_load(
        workspace_a,
        20,
    )

    await simulation.simulate_load(
        workspace_b,
        30,
    )

    await wait_until(
        lambda: (
            runtime["metrics"]
            .get(workspace_a.id)["processed"]
            == 20
        )
    )

    await wait_until(
        lambda: (
            runtime["metrics"]
            .get(workspace_b.id)["processed"]
            == 30
        )
    )

    orders_a = runtime[
        "database"
    ].list_orders(
        workspace_a.id
    )

    orders_b = runtime[
        "database"
    ].list_orders(
        workspace_b.id
    )

    assert len(orders_a) == 20
    assert len(orders_b) == 30

    await simulation.stop(
        workspace_a.id
    )

    await simulation.stop(
        workspace_b.id
    )

@pytest.mark.asyncio
async def test_reset_workspace(
    runtime,
):
    workspace = Workspace()

    workspace.config.cold_start_ms = 1
    workspace.config.processing_time_ms = 1
    workspace.config.max_instances = 3

    simulation = runtime["simulation"]

    simulation.start(
        workspace
    )

    await simulation.simulate_load(
        workspace,
        20,
    )

    await wait_until(
        lambda: (
            runtime["metrics"]
            .get(workspace.id)["processed"]
            == 20
        )
    )

    await simulation.reset(
        workspace
    )

    metrics = runtime["metrics"].get(
        workspace.id
    )

    assert metrics["requests"] == 0
    assert metrics["queued"] == 0
    assert metrics["processed"] == 0
    assert metrics["active_instances"] == 0
    assert metrics["cold_starts"] == 0
    assert metrics["errors"] == 0

    assert (
        runtime["queue"].size(
            workspace.id
        )
        == 0
    )

    assert (
        runtime["database"]
        .list_orders(
            workspace.id
        )
        == []
    )

    assert (
        runtime["event_log"]
        .get(
            workspace.id
        )
        == []
    )