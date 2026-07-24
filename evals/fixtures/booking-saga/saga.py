"""Saga orchestrator."""

from .steps import STEPS, Booking


def run_saga(booking: Booking, providers) -> None:
    """Run every step; on failure, undo what was already done."""
    for i, (name, step, _) in enumerate(STEPS):
        try:
            step(booking, providers)
            booking.completed.append(name)
        except Exception:
            _compensate_from(booking, providers, i)
            raise


def _compensate_from(booking: Booking, providers, i: int) -> None:
    for _, _, compensate in reversed(STEPS[: i - 1]):
        compensate(booking, providers)
