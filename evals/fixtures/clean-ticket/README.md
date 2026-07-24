# Support tickets — specification

Tracks a support request from arrival to closure. Small on purpose: this
module does one thing.

## Lifecycle

```
open ⇄ assigned → resolved → closed
        resolved → assigned  (reopen)
```

- **open**: received, nobody working on it.
- **assigned**: an agent owns it.
- **resolved**: the agent believes it is done; the requester can still reopen.
- **closed**: terminal. Nothing leaves this state.

Every transition is legal in exactly one direction from exactly one state, and
the table in `models.py` is the single source of that truth.

## Operations

| Operation | Transition |
|---|---|
| `assign(ticket, agent)` | `open → assigned` |
| `unassign(ticket)` | `assigned → open` |
| `resolve(ticket)` | `assigned → resolved` |
| `reopen(ticket)` | `resolved → assigned` |
| `close(ticket)` | `resolved → closed` |

Every operation returns `True` if it applied and `False` if the ticket was not
in a state that allows it. Applying an operation twice is safe: the second
call returns `False` and changes nothing.

## Business rules

1. `status` is only ever written by `apply_transition`. No other function
   assigns it.
2. `assignee` is set by `assign` and cleared only by `unassign`. An `open`
   ticket never has one; every later state keeps the agent who owns or owned
   it, so a resolved or closed ticket still records who handled it.
3. `resolved_at` is set on entering `resolved` and cleared only by `reopen`. A
   `closed` ticket keeps it as the record of when the work finished — so
   `resolved_at is None` means exactly "never resolved, or reopened since".
4. Closing is final: no operation leaves `closed`.

## Declared limits

Deliberate, and documented so nobody rediscovers them as bugs:

- **No direct reassignment.** Moving a ticket between agents requires
  `unassign` then `assign`. We accept the extra step to keep rule 2 trivially
  true.
- **No state for spam or duplicates.** They are closed like anything else,
  and the distinction lives in the closing note, not in the lifecycle.
- **No priority or SLA.** Out of scope for this module by design.
