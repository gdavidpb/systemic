# Approval requests — specification

Authors write requests and submit them for review. A reviewer approves or
rejects each one. The review tool delivers decisions as events.

## Lifecycle of a request

```
draft → submitted → approved
                  → rejected
submitted → draft                 the author withdraws it
```

`approved` and `rejected` are terminal.

## Rules

1. Only the transitions above happen. They are declared once, in
   `transitions.py`, and every operation goes through it.
2. `decided_by` and `decided_at` are set exactly when a request is approved or
   rejected. The schema enforces it.
3. A request is decided once. Two reviewers deciding at the same time: one
   wins and the other is told the request moved.
4. The review tool may deliver the same event more than once. A repeated
   event changes nothing. An event that could not be applied is not
   remembered, so the tool can deliver it again later.
5. A reviewer cannot decide their own request.
6. `authors.pending_count` is the number of requests the author has in
   `submitted`. The author's dashboard shows it; nothing else reads it.

## Files

- `schema.sql` — the tables and their constraints (SQLite).
- `transitions.py` — the transition table and the one function that moves a
  request.
- `operations.py` — create, submit, withdraw, decide.
- `reviews.py` — the handler for review events.
- `test_approvals.py` — the tests.
