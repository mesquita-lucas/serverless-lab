import time
from dataclasses import dataclass
from uuid import uuid4

@dataclass
class Order:
    workspace_id: str
    product: str
    quantity: int
    unit_price: float
    id: str = ""
    created_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())

        if not self.created_at:
            self.created_at = time.monotonic()

    @property
    def total(self):
        return self.quantity * self.unit_price

@dataclass
class ProcessedOrder:
    order_id: str
    workspace_id: str
    product: str
    quantity: int
    original_total: float
    discount: float
    final_total: float