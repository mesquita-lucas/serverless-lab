import asyncio
import math
import time

from app.faas.function_instance import FunctionInstance
from app.faas.function_status import FunctionStatus

class Autoscaler:
    def __init__(
        self,
        queue,
        database,
        metrics,
        event_log,
    ):
        self.queue = queue
        self.database = database
        self.metrics = metrics
        self.event_log = event_log
        self.instances = {}
        self.backlog_per_instance = 10

    def get_instances(self, workspace_id: str):
        if workspace_id not in self.instances:
            self.instances[workspace_id] = []

        return self.instances[workspace_id]

    def count_by_status(
        self,
        workspace_id: str,
        status: FunctionStatus,
    ):
        return sum(
            1
            for instance in self.get_instances(workspace_id)
            if instance.status == status
        )

    async def scale(self, workspace):
        instances = self.get_instances(workspace.id)
        queue_size = self.queue.size(workspace.id)

        busy_instances = self.count_by_status(
            workspace.id,
            FunctionStatus.BUSY,
        )

        if queue_size == 0:
            desired = len(instances)
        else:
            backlog_instances = math.ceil(
                queue_size / self.backlog_per_instance
            )

            desired = busy_instances + backlog_instances

            desired = max(
                desired,
                1,
            )

            desired = min(
                desired,
                workspace.config.max_instances,
            )

        amount_to_create = max(
            0,
            desired - len(instances),
        )

        new_instances = []

        for _ in range(amount_to_create):
            instance = FunctionInstance(
                workspace,
                self.database,
                self.metrics,
                self.event_log,
            )

            instances.append(instance)
            new_instances.append(instance)

        self.metrics.set(
            workspace.id,
            "active_instances",
            len(instances),
        )

        if new_instances:
            await asyncio.gather(
                *[
                    instance.initialize()
                    for instance in new_instances
                ]
            )

    async def remove_idle(self, workspace):
        instances = self.get_instances(workspace.id)
        now = time.monotonic()

        remaining = []

        for instance in instances:
            idle_time = now - instance.last_used

            should_remove = (
                instance.status == FunctionStatus.IDLE
                and idle_time
                > workspace.config.idle_timeout_seconds
            )

            if should_remove:
                instance.terminate()
            else:
                remaining.append(instance)

        self.instances[workspace.id] = remaining

        self.metrics.set(
            workspace.id,
            "active_instances",
            len(remaining),
        )

    async def tick(self, workspace):
        await self.scale(workspace)
        await self.remove_idle(workspace)

    def clear_workspace(self, workspace_id: str):
        instances = self.get_instances(workspace_id)

        for instance in instances:
            if instance.status != FunctionStatus.TERMINATED:
                instance.terminate()

        self.instances.pop(
            workspace_id,
            None,
        )

        self.metrics.set(
            workspace_id,
            "active_instances",
            0,
        )