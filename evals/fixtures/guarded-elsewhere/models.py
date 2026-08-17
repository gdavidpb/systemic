"""Models for the invoices module."""

from dataclasses import dataclass, field
from datetime import datetime

STATUS = {
    "draft",
    "issued",
    "overdue",
    "paid",
    "void",
}


@dataclass
class LineItem:
    sku: str
    qty: int
    unit_price: float


@dataclass
class Invoice:
    id: str
    status: str = "draft"
    items: list[LineItem] = field(default_factory=list)
    total: float = 0.0
    paid_at: datetime | None = None
    voided_at: datetime | None = None
