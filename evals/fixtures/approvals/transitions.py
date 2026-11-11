"""The request lifecycle: the transition table and the one function that applies it."""

STATES = ("draft", "submitted", "approved", "rejected")
TERMINAL = ("approved", "rejected")

ALLOWED = {
    ("draft", "submitted"),
    ("submitted", "draft"),
    ("submitted", "approved"),
    ("submitted", "rejected"),
}


class IllegalTransition(Exception):
    pass


class StaleRequest(Exception):
    """The request was not in the expected state: someone else moved it first."""


def move(conn, request_id, source, target, **fields):
    """Move a request from source to target in a single statement.

    The WHERE clause compares the current status, so a request that another
    writer already moved matches no row.
    """
    if (source, target) not in ALLOWED:
        raise IllegalTransition(f"{source} -> {target}")
    columns = ["status", *fields]
    assignments = ", ".join(f"{column} = ?" for column in columns)
    cursor = conn.execute(
        f"UPDATE requests SET {assignments} WHERE id = ? AND status = ?",
        [target, *fields.values(), request_id, source],
    )
    if cursor.rowcount != 1:
        raise StaleRequest(f"{request_id} is not {source}")
