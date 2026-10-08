import asyncio

from app.models.order import Order

class SimulationService:
    def __init__(
        self,
        queue,
        autoscaler,
        metrics,
        event_log,
        database,
    ):
        self.queue = queue
        self.autoscaler = autoscaler
        self.metrics = metrics
        self.event_log = event_log
        self.database = database

        self.runtime_tasks = {}
        self.invocation_tasks = {}
        self.cleanup_task = None

    def get_invocation_tasks(self, workspace_id: str):
        if workspace_id not in self.invocation_tasks:
            self.invocation_tasks[workspace_id] = set()

        return self.invocation_tasks[workspace_id]

    async def submit_order(
        self,
        workspace,
        product,
        quantity,
        unit_price,
    ):
        workspace.touch()

        order = Order(
            workspace_id=workspace.id,
            product=product,
            quantity=quantity,
            unit_price=unit_price,
        )

        await self.queue.publish(order)

        self.metrics.increment(
            workspace.id,
            "requests",
        )

        self.metrics.set(
            workspace.id,
            "queued",
            self.queue.size(workspace.id),
        )

        self.event_log.add(
            workspace.id,
            "REQUEST_RECEIVED",
            {
                "order_id": order.id,
            },
        )

        return order

    async def simulate_load(
        self,
        workspace,
        amount,
    ):
        workspace.touch()

        for _ in range(amount):
            await self.submit_order(
                workspace,
                "Ingresso Pista",
                1,
                120.0,
            )

    async def invoke_instance(
        self,
        workspace_id,
        instance,
        order,
        source_queue,
    ):
        try:
            await instance.invoke(order)
        finally:
            source_queue.task_done()

            self.metrics.set(
                workspace_id,
                "queued",
                source_queue.qsize(),
            )

    def dispatch(
        self,
        workspace_id,
        instance,
        order,
        source_queue,
    ):
        instance.reserve()

        task = asyncio.create_task(
            self.invoke_instance(
                workspace_id,
                instance,
                order,
                source_queue,
            )
        )

        tasks = self.get_invocation_tasks(
            workspace_id
        )

        tasks.add(task)

        def remove_task(completed_task):
            tasks.discard(completed_task)

        task.add_done_callback(remove_task)

    async def process_once(self, workspace):
        await self.autoscaler.tick(workspace)

        instances = self.autoscaler.get_instances(
            workspace.id
        )

        available = [
            instance
            for instance in instances
            if instance.available
        ]

        source_queue = self.queue.get_queue(
            workspace.id
        )

        for instance in available:
            if source_queue.empty():
                break

            order = source_queue.get_nowait()

            self.dispatch(
                workspace.id,
                instance,
                order,
                source_queue,
            )

        self.metrics.set(
            workspace.id,
            "queued",
            source_queue.qsize(),
        )

    async def run(self, workspace):
        try:
            while True:
                await self.process_once(workspace)

                if self.queue.size(workspace.id) > 0:
                    await asyncio.sleep(0.01)
                else:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            raise

    def start(self, workspace):
        existing = self.runtime_tasks.get(
            workspace.id
        )

        if existing and not existing.done():
            return

        self.runtime_tasks[workspace.id] = (
            asyncio.create_task(
                self.run(workspace)
            )
        )

    async def stop(self, workspace_id: str):
        runtime_task = self.runtime_tasks.pop(
            workspace_id,
            None,
        )

        if runtime_task:
            runtime_task.cancel()

            try:
                await runtime_task
            except asyncio.CancelledError:
                pass

        invocation_tasks = self.invocation_tasks.pop(
            workspace_id,
            set(),
        )

        for task in invocation_tasks:
            task.cancel()

        if invocation_tasks:
            await asyncio.gather(
                *invocation_tasks,
                return_exceptions=True,
            )

    async def reset(self, workspace):
        await self.stop(workspace.id)

        self.autoscaler.clear_workspace(
            workspace.id
        )

        self.queue.clear(
            workspace.id
        )

        self.database.clear_workspace(
            workspace.id
        )

        self.metrics.reset(
            workspace.id
        )

        self.event_log.clear(
            workspace.id
        )

        workspace.touch()

    async def remove_workspace(self, workspace):
        await self.reset(workspace)

    async def cleanup_expired(
        self,
        workspace_manager,
        interval_seconds=60,
    ):
        try:
            while True:
                await asyncio.sleep(
                    interval_seconds
                )

                expired = (
                    workspace_manager.expired_ids()
                )

                for workspace_id in expired:
                    workspace = (
                        workspace_manager.get(
                            workspace_id,
                            touch=False,
                        )
                    )

                    if not workspace:
                        continue

                    await self.remove_workspace(
                        workspace
                    )

                    workspace_manager.remove(
                        workspace_id
                    )

        except asyncio.CancelledError:
            raise

    def start_cleanup(
        self,
        workspace_manager,
    ):
        if (
            self.cleanup_task
            and not self.cleanup_task.done()
        ):
            return

        self.cleanup_task = asyncio.create_task(
            self.cleanup_expired(
                workspace_manager
            )
        )

    async def shutdown(self):
        if self.cleanup_task:
            self.cleanup_task.cancel()

            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        workspace_ids = list(
            self.runtime_tasks.keys()
        )

        for workspace_id in workspace_ids:
            await self.stop(
                workspace_id
            )