CREATE TABLE authors (
    id            TEXT PRIMARY KEY,
    pending_count INTEGER NOT NULL DEFAULT 0 CHECK (pending_count >= 0)
);

CREATE TABLE requests (
    id         TEXT PRIMARY KEY,
    author_id  TEXT NOT NULL REFERENCES authors (id),
    status     TEXT NOT NULL DEFAULT 'draft'
               CHECK (status IN ('draft', 'submitted', 'approved', 'rejected')),
    decided_by TEXT,
    decided_at TEXT,
    CHECK ((status IN ('approved', 'rejected')) = (decided_by IS NOT NULL)),
    CHECK ((decided_by IS NULL) = (decided_at IS NULL))
);

CREATE TABLE review_events (
    event_id   TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES requests (id)
);
