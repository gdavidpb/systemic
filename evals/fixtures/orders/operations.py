"""Business operations on orders."""

from datetime import UTC, datetime

from .models import Item, Order


def add_item(order: Order, item: Item) -> None:
    order.items.append(item)


def apply_discount(order: Order, value: float) -> None:
    """Apply a discount to the order."""
    if value <= 1:
        order.total = order.total * (1 - value)
    else:
        order.total = order.total - value


def checkout(order: Order) -> None:
    order.total = sum(i.qty * i.price for i in order.items)
    order.status = "pending_payment"


def mark_paid(order: Order) -> None:
    order.paid_at = datetime.now(UTC)
    order.status = "paid"


def cancel(order: Order) -> None:
    order.status = "canceled"


def hold(order: Order) -> None:
    order.held_from = order.status
    order.status = "on_hold"


def refund(order: Order) -> None:
    order.status = "refund_pending"


def ship(order: Order, inventory, courier) -> None:
    inventory.reserve(order.items)
    # TODO: wrap in a transaction — if the courier call fails, inventory
    # stays decremented with no shipped order.
    courier.notify(order.id)
    order.status = "shipped"


def deliver(order: Order) -> None:
    if order.status != "shipped":
        raise ValueError("only shipped orders can be delivered")
    order.status = "delivered"
