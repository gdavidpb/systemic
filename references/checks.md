# The 12 systemic checks — how to detect each one

Operational guide for Phase 2. For each check: what to look for, how to detect
it in code or documents, and how to calibrate severity. Checks 1, 2, 10 and 11
come directly from the GST framework; the rest are practical
extensions of the same principle (system consistency) for real software with
queues, retries and concurrency.

**On the severities below**: they describe the typical case for each check,
not a ceiling. The authoritative rubric is the one in `SKILL.md` — rate by the
damage the finding actually causes. When a check's usual severity and the
rubric disagree, the rubric wins.

## 1. Closure

**What**: every operation on the system's elements produces an element the
system represents.
**Detect**: list the valid values of each state field (enum, constants, CHECK
constraint, docs). Then find every write to that field (assignments, UPDATE,
`.status =`) and verify the written value belongs to the set. Also look for
operation results with no branch that handles them (a `match`/`if-elif` with
no case for a producible value).
**Severity**: critical if the out-of-system state gets persisted; high if it
only lives in memory.

## 2. Operator ambiguity (the `A U B` problem)

**What**: an operator with more than one reasonable interpretation.
**Detect**: parameters that change meaning based on their value or type
(`value <= 1` means fraction, otherwise amount); boolean flags that fork
semantics; the same function with different effects depending on the caller;
names that promise one thing and do another. In documents: operations
described without specifying order, side or unit.
**Severity**: high if two current callers already interpret it differently;
medium if it is a latent trap.

## 3. Transition completeness (state × operator matrix)

**What**: for every (state, operator) pair the answer must be: a defined
transition, an explicit prohibition (guard with a clear error), or — the
finding — a **hole**: the operation proceeds without considering that state.
**Detect**: build the matrix. Look for operators that mutate state without
checking the current state (missing guard). Contrast with declared rules ("a
shipped order cannot be canceled") — a missing guard that contradicts a
declared rule is an INCONSISTENCY, not just a hole.
**Severity**: critical if the hole bypasses business validation (payments,
stock); high for other holes with mutation.

## 4. Reachability

**What**: states no operation produces (unreachable), non-terminal states
with no exit (absorbing), transitions no flow executes (dead).
**Detect**: for each declared state, find who writes it and who exits it. A
declared state with no writers is unreachable (or its writer lives outside
the system — note it as a limit). A non-final state without outgoing
transitions is a trap.
**Severity**: medium (unreachable = dead component); high if real data is
trapped in an absorbing state.

## 5. Illegal states representable

**What**: the model allows persisting combinations the business forbids.
**Detect**: identify fields that co-vary with state (`paid_at` only with
`status ∈ {accepted, closed}`; `deleted_at` excludes `active=true`). Check
whether any operator can write the forbidden combination (missing guard,
partial updates) and whether the schema permits it (no constraint). The
pattern recommendation is "make illegal states unrepresentable": model so the
combination cannot exist (sum types, constraints, a single source field).
**Severity**: critical when money/inventory is involved; high otherwise.

## 6. Invariants and partial failure

**What**: properties that must always hold (Σ payments = total paid;
stock ≥ 0) and what happens when the operator maintaining them fails halfway.
**Detect**: find operations with multiple writes (two tables, table +
external API, table + file) without a transaction or compensation. Ask: if it
fails after write 1 and before write 2, which invariant is broken? Who
repairs it? `TODO: transaction` comments are confessions.
**Severity**: critical with money/stock; high with business state.

## 7. Idempotency and re-entry (closure under repetition)

**What**: applying the same operator twice (queue retry, redelivered webhook,
double click) must leave the system in the same state as applying it once.
**Detect**: find the re-invokable entry points (webhooks, queue handlers,
crons) and check for dedup (event id, marker, UPSERT, idempotency key). An
`append` or `+=` in a webhook handler without dedup is the classic pattern.
**Severity**: critical if it duplicates money/business records; high if it
duplicates visible effects (messages, emails).

## 8. Concurrency

**What**: two operators acting on the same element at the same time.
**Detect**: look for read-modify-write without lock or version (read total,
add, save); states two flows can mutate (user + job); `SELECT` then `UPDATE`
without `FOR UPDATE`/an atomic claim. Ask whether the operators commute — if
order changes the result and nothing serializes them, there is a lost update.
**Severity**: critical with money; high with business state; medium if the
window is theoretical and the domain tolerates it.

## 9. Symmetry / operator duality

**What**: operators without an inverse or cycle closer: open/close,
lock/release, hold/resume, subscribe/unsubscribe, pause/resume.
**Detect**: for every operator that acquires, marks, or enters a special
state, find who releases/unmarks/exits. If nothing does — or only a manual
path does (hand-run SQL) — it is a structural leak.
**Severity**: high if it accumulates resources or blocks business flow;
medium if a manual exit is documented.

## 10. Minimal expression (double source of truth)

**What**: a derivable component also materialized as a primitive.
**Detect**: stored values that are also computed (saved total +
`sum(items)`); replicas without invalidation; caches without TTL or an
invalidation event; the same concept modeled in two places with different
update rules. Check whether ALL writers of the primitive also update the
derived value (or vice versa) — if one does not, they already drift.
**Severity**: high if both are used for decisions; medium if the derived one
is presentation-only.

## 11. System limits

**What**: requirements (current or imminent) outside the set representable by
the current components.
**Detect**: hacks are the evidence — hardcoded special cases, magic strings
encoding unmodeled semantics, "temporary" parameters, comments saying "this
does not support X". State the limit positively: "the system cannot represent
Y because component Z is missing" (evens + addition cannot make 7 without an
odd number).
**Severity**: medium by default (structural debt); high if the business is
already asking for the unrepresentable figure.

## 12. Feedback loops

**What**: components whose output feeds their own input with amplification:
retries that create more load that creates more failures that create more
retries; compensations that trigger the flow they compensate; alerts that
cause actions that cause alerts.
**Detect**: map cycles in the call/event graph (retry + queue + timeout +
trigger). Ask for the damper: backoff, circuit breaker, retry cap, dedup. A
cycle without a damper is an amplification loop waiting for its day.
**Severity**: high without a damper on a critical path; medium with a partial
damper.

---

## Declared vs built (cross-cutting)

Transversal to all checks: the README/spec/docstring promises the
*silhouette* and the code builds the *figure*. When they diverge, report the
INCONSISTENCY citing **both** pieces of evidence (the declaration and the
code) — it is the most useful finding for the team because nobody needs to
decide which one is right to know something is wrong.
