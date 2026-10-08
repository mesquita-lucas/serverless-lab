import asyncio
import time
from uuid import uuid4

from app.faas.function_status import FunctionStatus
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
        self.status = FunctionStatus.CREATED
        self.last_used = time.monotonic()

    @property
    def warm(self):
        return self.status in {
            FunctionStatus.IDLE,
            FunctionStatus.BUSY,
        }

    @property
    def busy(self):
        return self.status == FunctionStatus.BUSY

    @property
    def available(self):
        return self.status == FunctionStatus.IDLE

    async def initialize(self):
        if self.status != FunctionStatus.CREATED:
            return

        self.status = FunctionStatus.INITIALIZING

        self.event_log.add(
            self.workspace.id,
            "FUNCTION_CREATED",
            {
                "instance_id": self.id,
            },
        )

        self.metrics.increment(
            self.workspace.id,
            "cold_starts",
        )

        self.event_log.add(
            self.workspace.id,
            "COLD_START",
            {
                "instance_id": self.id,
            },
        )

        await asyncio.sleep(
            self.workspace.config.cold_start_ms / 1000
        )

        self.status = FunctionStatus.IDLE
        self.last_used = time.monotonic()

        self.event_log.add(
            self.workspace.id,
            "FUNCTION_READY",
            {
                "instance_id": self.id,
            },
        )

    def reserve(self):
        if self.status != FunctionStatus.IDLE:
            raise RuntimeError(
                f"Function {self.id} is not available"
            )

        self.status = FunctionStatus.BUSY

    async def invoke(self, order):
        if self.status != FunctionStatus.BUSY:
            raise RuntimeError(
                f"Function {self.id} was not reserved"
            )

        self.event_log.add(
            self.workspace.id,
            "FUNCTION_INVOKED",
            {
                "instance_id": self.id,
                "order_id": order.id,
            },
        )

        try:
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

            return result

        except asyncio.CancelledError:
            self.event_log.add(
                self.workspace.id,
                "FUNCTION_CANCELLED",
                {
                    "instance_id": self.id,
                    "order_id": order.id,
                },
            )

            raise

        except Exception as error:
            self.metrics.increment(
                self.workspace.id,
                "errors",
            )

            self.event_log.add(
                self.workspace.id,
                "FUNCTION_ERROR",
                {
                    "instance_id": self.id,
                    "order_id": order.id,
                    "error": str(error),
                },
            )

            return None

        finally:
            if self.status != FunctionStatus.TERMINATED:
                self.status = FunctionStatus.IDLE
                self.last_used = time.monotonic()

    def terminate(self):
        self.status = FunctionStatus.TERMINATED

        self.event_log.add(
            self.workspace.id,
            "FUNCTION_TERMINATED",
            {
                "instance_id": self.id,
            },
        )