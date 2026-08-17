"""Provider webhooks. Routes registered here run through the gateway."""

import functools

from .api import record_payment
from .models import Invoice

REFUNDS: list[dict] = []  # ledger: one row per refunded payment

_seen_events: set[str] = set()


def dedupe(handler):
    """Drop provider retries: the first delivery of an event_id wins."""

    @functools.wraps(handler)
    def wrapper(invoice: Invoice, event: dict):
        if event["id"] in _seen_events:
            return "duplicate"
        _seen_events.add(event["id"])
        return handler(invoice, event)

    return wrapper


ROUTES: dict = {}


def route(path: str, handler, *, dedupe_events: bool = True) -> None:
    ROUTES[path] = dedupe(handler) if dedupe_events else handler


def handle_payment_event(invoice: Invoice, event: dict):
    record_payment(invoice, event["amount"])


def handle_refund_event(invoice: Invoice, event: dict):
    invoice.status = "issued"
    invoice.paid_at = None
    REFUNDS.append({"invoice_id": invoice.id, "amount": event["amount"]})


route("/webhooks/payment", handle_payment_event)
# TODO: refunds are rare, wire dedupe later.
route("/webhooks/refund", handle_refund_event, dedupe_events=False)
