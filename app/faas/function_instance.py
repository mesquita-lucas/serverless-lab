import asyncio
import time
from uuid import uuid4

from app.faas.order_function import OrderFunction

class FunctionInstance:
    def __init__(
        self,
        workspace,
        database,
        metrics,
        event_log,
    ):
        self.id = str(uuid4())
        self.workspace = workspace
        self.database = database
        self.metrics = metrics
        self.event_log = event_log
        self.function = OrderFunction()
        self.warm = False
        self.busy = False
        self.last_used = time.monotonic()

    async def initialize(self):
        self.event_log.add(
            self.workspace.id,
            "FUNCTION_CREATED",
            {"instance_id": self.id},
        )

        self.metrics.increment(
            self.workspace.id,
            "cold_starts",
        )

        self.event_log.add(
            self.workspace.id,
            "COLD_START",
            {"instance_id": self.id},
        )

        await asyncio.sleep(
            self.workspace.config.cold_start_ms / 1000
        )

        self.warm = True

    async def invoke(self, order):
        if not self.warm:
            await self.initialize()

        self.busy = True

        self.event_log.add(
            self.workspace.id,
            "FUNCTION_INVOKED",
            {
                "instance_id": self.id,
                "order_id": order.id,
            },
        )

        await asyncio.sleep(
            self.workspace.config.processing_time_ms / 1000
        )

        result = self.function.execute(
            order,
            self.workspace.config,
        )

        self.database.save_order(result)

        self.metrics.increment(
            self.workspace.id,
            "processed",
        )

        self.event_log.add(
            self.workspace.id,
            "ORDER_PROCESSED",
            {
                "instance_id": self.id,
                "order_id": order.id,
            },
        )

        self.busy = False
        self.last_used = time.monotonic()

        return result