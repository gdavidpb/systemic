"""Models for the orders module."""

from dataclasses import dataclass, field
from datetime import datetime

STATUS = {
    "draft",
    "pending_payment",
    "in_review",
    "paid",
    "shipped",
    "delivered",
    "canceled",
    "on_hold",
}

FINAL_STATUSES = {"delivered", "canceled"}


@dataclass
class Item:
    sku: str
    qty: int
    price: float


@dataclass
class Payment:
    amount: float
    event_id: str


@dataclass
class Order:
    id: str
    status: str = "draft"
    items: list[Item] = field(default_factory=list)
    payments: list[Payment] = field(default_factory=list)
    total: float = 0.0
    total_paid: float = 0.0
    paid_at: datetime | None = None
    held_from: str | None = None


def calc_total(order: Order) -> float:
    """The canonical total: sum of the items."""
    return sum(i.qty * i.price for i in order.items)


def is_final(order: Order) -> bool:
    return order.status in FINAL_STATUSES
