"""Payment provider webhook."""

from .models import Order, Payment
from .operations import mark_paid


def handle_payment_webhook(order: Order, event: dict) -> None:
    """Process a payment event from the external provider."""
    order.payments.append(Payment(amount=event["amount"], event_id=event["id"]))
    order.total_paid = order.total_paid + event["amount"]
    if order.total_paid >= order.total:
        mark_paid(order)
