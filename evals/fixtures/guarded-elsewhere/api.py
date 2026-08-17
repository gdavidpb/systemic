"""Public entry points for payments."""

from .guards import InvalidStatus
from .models import Invoice
from .operations import _apply_payment


def record_payment(invoice: Invoice, amount: float) -> None:
    if invoice.status not in ("issued", "overdue"):
        raise InvalidStatus(f"payment for an invoice in {invoice.status!r}")
    if amount != invoice.total:
        raise InvalidStatus("partial payments are not supported")
    _apply_payment(invoice)
