import asyncio

from app.models.order import Order

class EventQueue:
    def __init__(self):
        self.queues: dict[str, asyncio.Queue] = {}

    def get_queue(self, workspace_id: str):
        if workspace_id not in self.queues:
            self.queues[workspace_id] = asyncio.Queue()

        return self.queues[workspace_id]

    async def publish(self, order: Order):
        queue = self.get_queue(order.workspace_id)
        await queue.put(order)

    async def consume(self, workspace_id: str):
        queue = self.get_queue(workspace_id)
        return await queue.get()

    def size(self, workspace_id: str):
        return self.get_queue(workspace_id).qsize()

    def clear(self, workspace_id: str):
        self.queues[workspace_id] = asyncio.Queue()