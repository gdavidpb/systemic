"""Models and the transition table for support tickets."""

from dataclasses import dataclass
from datetime import datetime

STATUS = {"open", "assigned", "resolved", "closed"}
FINAL_STATUSES = {"closed"}

# The single source of truth for the lifecycle: (current status, action) -> next
# status. An action absent from this table is not legal from that state.
TRANSITIONS: dict[tuple[str, str], str] = {
    ("open", "assign"): "assigned",
    ("assigned", "unassign"): "open",
    ("assigned", "resolve"): "resolved",
    ("resolved", "reopen"): "assigned",
    ("resolved", "close"): "closed",
}


@dataclass
class Ticket:
    id: str
    subject: str
    status: str = "open"
    assignee: str | None = None
    resolved_at: datetime | None = None


def is_final(ticket: Ticket) -> bool:
    return ticket.status in FINAL_STATUSES


def allowed_actions(ticket: Ticket) -> set[str]:
    """Every action legal from the ticket's current state."""
    return {action for (status, action) in TRANSITIONS if status == ticket.status}
