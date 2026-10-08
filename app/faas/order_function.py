from app.models.order import Order, ProcessedOrder
from app.models.function_config import FunctionConfig

class OrderFunction:
    def execute(self, order: Order, config: FunctionConfig):
        original_total = order.total
        discount = 0.0

        if original_total > config.discount_threshold:
            discount = original_total * config.discount_percent / 100

        final_total = original_total - discount

        return ProcessedOrder(
            order_id=order.id,
            workspace_id=order.workspace_id,
            product=order.product,
            quantity=order.quantity,
            original_total=original_total,
            discount=discount,
            final_total=final_total,
        )