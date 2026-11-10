"""Tests for approval requests."""

import sqlite3
import unittest
from unittest import mock

from . import operations
from .operations import SelfReview, connect, create, decide, pending_count, status_of, submit, withdraw
from .reviews import handle_review_event
from .transitions import IllegalTransition, StaleRequest, move

# The lifecycle as the specification draws it, written out here by hand.
SPEC = {
    "draft": {"submitted"},
    "submitted": {"draft", "approved", "rejected"},
    "approved": set(),
    "rejected": set(),
}


def request_in(status):
    conn = connect()
    create(conn, "r1", "ana")
    if status != "draft":
        submit(conn, "r1")
    if status in ("approved", "rejected"):
        decide(conn, "r1", "bob", status, "2026-01-01T10:00")
    return conn


def event(event_id="e1", verdict="approved", reviewer="bob"):
    return {"id": event_id, "request_id": "r1", "reviewer": reviewer, "verdict": verdict, "at": "2026-01-01T10:00"}


class TransitionTest(unittest.TestCase):
    def test_only_the_specified_transitions_are_possible(self):
        for source, allowed in SPEC.items():
            for target in SPEC:
                with self.subTest(source=source, target=target):
                    conn = request_in(source)
                    fields = {"decided_by": "bob", "decided_at": "t"} if target in ("approved", "rejected") else {}
                    if target in allowed:
                        with conn:
                            move(conn, "r1", source, target, **fields)
                        self.assertEqual(status_of(conn, "r1"), target)
                    else:
                        with self.assertRaises(IllegalTransition):
                            move(conn, "r1", source, target, **fields)
                        self.assertEqual(status_of(conn, "r1"), source)

    def test_a_request_someone_else_moved_is_refused(self):
        conn = request_in("submitted")
        decide(conn, "r1", "bob", "approved", "2026-01-01T10:00")
        with self.assertRaises(StaleRequest):
            decide(conn, "r1", "cleo", "rejected", "2026-01-01T10:01")
        self.assertEqual(status_of(conn, "r1"), "approved")

    def test_a_reviewer_cannot_decide_their_own_request(self):
        conn = request_in("submitted")
        with self.assertRaises(SelfReview):
            decide(conn, "r1", "ana", "approved", "2026-01-01T10:00")
        self.assertEqual(status_of(conn, "r1"), "submitted")


class SchemaTest(unittest.TestCase):
    def test_a_decision_without_a_reviewer_cannot_be_stored(self):
        conn = request_in("submitted")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("UPDATE requests SET status = 'approved' WHERE id = 'r1'")

    def test_a_reviewer_on_an_undecided_request_cannot_be_stored(self):
        conn = request_in("submitted")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("UPDATE requests SET decided_by = 'bob', decided_at = 't' WHERE id = 'r1'")

    def test_an_unknown_status_cannot_be_stored(self):
        conn = request_in("draft")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("UPDATE requests SET status = 'archived' WHERE id = 'r1'")


class ReviewEventTest(unittest.TestCase):
    def test_a_repeated_event_changes_nothing(self):
        conn = request_in("submitted")
        self.assertEqual(handle_review_event(conn, event()), "applied")
        before = conn.execute("SELECT * FROM requests").fetchall(), pending_count(conn, "ana")
        self.assertEqual(handle_review_event(conn, event()), "duplicate")
        after = conn.execute("SELECT * FROM requests").fetchall(), pending_count(conn, "ana")
        self.assertEqual(after, before)

    def test_an_event_that_fails_can_be_delivered_again(self):
        conn = request_in("submitted")
        with mock.patch.object(operations, "move", side_effect=sqlite3.OperationalError("disk I/O error")):
            with self.assertRaises(sqlite3.OperationalError):
                handle_review_event(conn, event())
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM review_events").fetchone()[0], 0)
        self.assertEqual(status_of(conn, "r1"), "submitted")
        self.assertEqual(handle_review_event(conn, event()), "applied")
        self.assertEqual(status_of(conn, "r1"), "approved")


class PendingCountTest(unittest.TestCase):
    def test_submitting_shows_one_pending_request(self):
        conn = request_in("submitted")
        self.assertEqual(pending_count(conn, "ana"), 1)

    def test_a_decided_request_is_no_longer_pending(self):
        conn = request_in("approved")
        self.assertEqual(pending_count(conn, "ana"), 0)

    def test_withdrawing_returns_the_request_to_draft(self):
        conn = request_in("submitted")
        withdraw(conn, "r1")
        self.assertEqual(status_of(conn, "r1"), "draft")
