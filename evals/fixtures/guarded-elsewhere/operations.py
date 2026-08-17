"""Business operations on invoices. Status preconditions live in guards.py."""

from datetime import UTC, datetime

from .guards import requires_status
from .models import Invoice, LineItem


def _recalc(invoice: Invoice) -> None:
    invoice.total = sum(i.qty * i.unit_price for i in invoice.items)


@requires_status("draft")
def add_line(invoice: Invoice, item: LineItem) -> None:
    invoice.items.append(item)
    _recalc(invoice)


@requires_status("draft")
def remove_line(invoice: Invoice, sku: str) -> None:
    invoice.items = [i for i in invoice.items if i.sku != sku]
    _recalc(invoice)


@requires_status("draft")
def issue(invoice: Invoice) -> None:
    invoice.status = "issued"


@requires_status("issued")
def mark_overdue(invoice: Invoice) -> None:
    invoice.status = "overdue"


@requires_status("issued", "overdue")
def void(invoice: Invoice) -> None:
    invoice.status = "void"
    invoice.voided_at = datetime.now(UTC)


def _apply_payment(invoice: Invoice) -> None:
    invoice.status = "paid"
    invoice.paid_at = datetime.now(UTC)
