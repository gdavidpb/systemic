# Job queue — specification

A small durable job queue. Producers enqueue jobs; workers lease one, run it
and report the result. Several workers poll the same store at the same time.

## Lifecycle of a job

| Status | Meaning |
|---|---|
| `queued` | waiting for a worker |
| `leased` | one worker holds it until `leaseUntil` |
| `done` | finished; terminal |
| `dead` | gave up after `MAX_ATTEMPTS` attempts; terminal |

```
queued → leased → done
leased → queued          the worker fails or releases the job, or the lease expires
leased → dead            the job fails on its last attempt
```

## Rules

1. A job is held by at most one worker at a time. `leasedBy` and `leaseUntil`
   are set exactly while the job is `leased`.
2. Only the worker that holds an unexpired lease may renew, complete, fail or
   release the job.
3. A job runs at most `MAX_ATTEMPTS` (3) times; `attempts` counts its leases.
   A job that fails on its last attempt is `dead` and is not retried.
4. `complete` is safe to call again: workers retry it when the acknowledgement
   is lost. `stats.completed` counts each job once, and only when its
   completion was stored.
5. A lease lasts `LEASE_MS`. The reaper returns expired leases to the queue.
6. `done` and `dead` are terminal: a job never leaves them.
7. Jobs are unique by key: enqueueing a key that already exists returns the
   existing job instead of creating another.

## Files

- `store.js` — the jobs table (an in-memory stand-in with the same contract).
- `queue.js` — the operations on a job.
- `worker.js` — the polling loop a worker process runs.
- `queue.test.js` — the tests (`node --test`).
