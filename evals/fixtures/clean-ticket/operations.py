"""Operations on tickets.

Every state change goes through `apply_transition`; nothing else writes
`Ticket.status`. The per-operation functions only carry the field updates that
must accompany their transition.
"""

from datetime import UTC, datetime

from .models import TRANSITIONS, Ticket


def apply_transition(ticket: Ticket, action: str) -> bool:
    """Move the ticket if (status, action) is a declared transition.

    Returns False and changes nothing otherwise — which also makes every
    operation safe to apply twice.
    """
    target = TRANSITIONS.get((ticket.status, action))
    if target is None:
        return False
    ticket.status = target
    return True


def assign(ticket: Ticket, agent: str) -> bool:
    if not apply_transition(ticket, "assign"):
        return False
    ticket.assignee = agent
    return True


def unassign(ticket: Ticket) -> bool:
    if not apply_transition(ticket, "unassign"):
        return False
    ticket.assignee = None
    return True


def resolve(ticket: Ticket) -> bool:
    if not apply_transition(ticket, "resolve"):
        return False
    ticket.resolved_at = datetime.now(UTC)
    return True


def reopen(ticket: Ticket) -> bool:
    if not apply_transition(ticket, "reopen"):
        return False
    ticket.resolved_at = None
    return True


def close(ticket: Ticket) -> bool:
    return apply_transition(ticket, "close")
