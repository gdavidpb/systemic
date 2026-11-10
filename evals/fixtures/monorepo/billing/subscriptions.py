"""Subscription lifecycle: trial -> active -> past_due -> canceled."""

from dataclasses import dataclass
from datetime import datetime

STATUS = {"trial", "active", "past_due", "canceled"}


@dataclass
class Subscription:
    id: str
    status: str = "trial"
    trial_ends: datetime | None = None
    paid_through: datetime | None = None
    failed_charges: int = 0


def activate(sub, paid_through):
    sub.status = "active"
    sub.paid_through = paid_through


def charge_failed(sub):
    sub.failed_charges += 1
    sub.status = "past_due"


def cancel(sub):
    sub.status = "canceled"
