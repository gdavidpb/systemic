"""Operations on approval requests. Each one is a single transaction."""

from pathlib import Path
import sqlite3

from .transitions import move

SCHEMA = Path(__file__).with_name("schema.sql")


class SelfReview(Exception):
    pass


def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    return conn


def author_of(conn, request_id):
    row = conn.execute("SELECT author_id FROM requests WHERE id = ?", (request_id,)).fetchone()
    if row is None:
        raise KeyError(request_id)
    return row[0]


def create(conn, request_id, author_id):
    with conn:
        conn.execute("INSERT OR IGNORE INTO authors (id) VALUES (?)", (author_id,))
        conn.execute("INSERT INTO requests (id, author_id) VALUES (?, ?)", (request_id, author_id))


def submit(conn, request_id):
    with conn:
        author = author_of(conn, request_id)
        move(conn, request_id, "draft", "submitted")
        conn.execute("UPDATE authors SET pending_count = pending_count + 1 WHERE id = ?", (author,))


def withdraw(conn, request_id):
    with conn:
        move(conn, request_id, "submitted", "draft")


def apply_decision(conn, request_id, reviewer_id, verdict, at):
    """Decide a request inside the caller's transaction."""
    if verdict not in ("approved", "rejected"):
        raise ValueError(verdict)
    author = author_of(conn, request_id)
    if author == reviewer_id:
        raise SelfReview(reviewer_id)
    move(conn, request_id, "submitted", verdict, decided_by=reviewer_id, decided_at=at)
    conn.execute("UPDATE authors SET pending_count = pending_count - 1 WHERE id = ?", (author,))


def decide(conn, request_id, reviewer_id, verdict, at):
    with conn:
        apply_decision(conn, request_id, reviewer_id, verdict, at)


def status_of(conn, request_id):
    return conn.execute("SELECT status FROM requests WHERE id = ?", (request_id,)).fetchone()[0]


def pending_count(conn, author_id):
    return conn.execute("SELECT pending_count FROM authors WHERE id = ?", (author_id,)).fetchone()[0]
