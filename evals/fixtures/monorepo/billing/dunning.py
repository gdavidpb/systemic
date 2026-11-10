"""Retry failed renewals."""

from .subscriptions import cancel, charge_failed

MAX_FAILURES = 3


def on_renewal_failed(sub):
    charge_failed(sub)
    if sub.failed_charges >= MAX_FAILURES:
        cancel(sub)
