"""Handler for the events the review tool delivers."""

import sqlite3

from .operations import apply_decision


def handle_review_event(conn, event):
    """Apply one review decision. The tool may deliver the same event again."""
    try:
        with conn:
            conn.execute(
                "INSERT INTO review_events (event_id, request_id) VALUES (?, ?)",
                (event["id"], event["request_id"]),
            )
            apply_decision(conn, event["request_id"], event["reviewer"], event["verdict"], event["at"])
    except sqlite3.IntegrityError as error:
        if "review_events.event_id" in str(error):
            return "duplicate"
        raise
    return "applied"
