import asyncio

from app.models.order import Order

class SimulationService:
    def __init__(
        self,
        queue,
        autoscaler,
        metrics,
        event_log,
    ):
        self.queue = queue
        self.autoscaler = autoscaler
        self.metrics = metrics
        self.event_log = event_log
        self.tasks = {}

    async def submit_order(
        self,
        workspace,
        product,
        quantity,
        unit_price,
    ):
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
            {"order_id": order.id},
        )

        return order

    async def simulate_load(
        self,
        workspace,
        amount,
    ):
        for _ in range(amount):
            await self.submit_order(
                workspace,
                "Ingresso Pista",
                1,
                120.0,
            )

    async def process_once(self, workspace):
        await self.autoscaler.tick(workspace)

        instances = self.autoscaler.get_instances(
            workspace.id
        )

        available = [
            instance
            for instance in instances
            if not instance.busy
        ]

        queue = self.queue.get_queue(workspace.id)

        for instance in available:
            if queue.empty():
                break

            order = await queue.get()

            asyncio.create_task(
                instance.invoke(order)
            )

        self.metrics.set(
            workspace.id,
            "queued",
            queue.qsize(),
        )

    async def run(self, workspace):
        while True:
            await self.process_once(workspace)
            await asyncio.sleep(0.1)

    def start(self, workspace):
        if workspace.id in self.tasks:
            return

        self.tasks[workspace.id] = asyncio.create_task(
            self.run(workspace)
        )