"""Queue worker, retries and alerting."""

from .saga import run_saga
from .steps import Booking

TIMEOUT_SECONDS = 2


def handle(booking: Booking, providers, queue, alerts) -> None:
    """Process one booking job off the queue."""
    while True:
        try:
            with providers.timeout(TIMEOUT_SECONDS):
                run_saga(booking, providers)
            return
        except Exception as exc:
            alerts.notify(f"booking {booking.id} failed: {exc}")
            queue.enqueue(booking)


def on_alert(booking_id: str, providers, queue, alerts) -> None:
    """On-call automation: a failure alert triggers an immediate retry."""
    booking = providers.store.load(booking_id)
    queue.enqueue(booking)


def drain_dead_letter(queue, dead_letter) -> None:
    """Cron: move everything in the dead-letter queue back to the main queue."""
    for booking in dead_letter.all():
        queue.enqueue(booking)
        dead_letter.remove(booking)
