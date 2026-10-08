import asyncio
import math
import time

from app.faas.function_instance import FunctionInstance

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
        self.running = {}

    def get_instances(self, workspace_id: str):
        if workspace_id not in self.instances:
            self.instances[workspace_id] = []

        return self.instances[workspace_id]

    async def scale(self, workspace):
        instances = self.get_instances(workspace.id)
        queue_size = self.queue.size(workspace.id)

        desired = min(
            workspace.config.max_instances,
            math.ceil(queue_size / 10),
        )

        desired = max(desired, 1 if queue_size else 0)

        while len(instances) < desired:
            instance = FunctionInstance(
                workspace,
                self.database,
                self.metrics,
                self.event_log,
            )

            instances.append(instance)

        self.metrics.set(
            workspace.id,
            "active_instances",
            len(instances),
        )

    async def remove_idle(self, workspace):
        instances = self.get_instances(workspace.id)
        now = time.monotonic()

        remaining = []

        for instance in instances:
            idle_time = now - instance.last_used

            if (
                not instance.busy
                and idle_time
                > workspace.config.idle_timeout_seconds
            ):
                self.event_log.add(
                    workspace.id,
                    "FUNCTION_TERMINATED",
                    {"instance_id": instance.id},
                )
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