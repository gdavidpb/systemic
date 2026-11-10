# Coverage map

Every behavior the skill promises, and the cases that exercise it. **Forward
evals** (`evals.json`, by id) run the skill and grade what it writes.
**Deterministic tests** check what can be checked without a model:
`test_systemic_check.py` mutates the golden run to prove that a gate rejects
the violation (classes named after the gate), and `test_adversarial_fixtures.py`
executes the defects planted in the fixtures, so the evals' answer key is
itself tested.

A row with no eval is a gap. When you add a check, a rule or a gate, add a
row here and the case that covers it.

## The twelve checks

| # | Check | Positive case (a finding) | Restraint case (clean, refuted or not verifiable) |
|---|---|---|---|
| 1 | Closure | 1, 4, 8, 14 (refund_pending) | 6 |
| 2 | Operator ambiguity | 1 (apply_discount), 2 (good condition) | 12 |
| 3 | Transition completeness | 1, 17, 19 | 6, 7 (decorator guards) |
| 4 | Reachability | 1 (in_review), 5 (dead-letter), 19 (trial_ends) | 6, 7 (void is terminal) |
| 5 | Illegal states representable | 1 (mark_paid), 2 (suspended), 17 (sold unit changes hands) | 6 |
| 6 | Invariants and partial failure | 1 (ship), 5 (compensation), 17 (sell before charge) | 6 |
| 7 | Idempotency and re-entry | 1, 2, 7 (refund replay, failed-payment retry) | 6, 7 (dedup wrapper) |
| 8 | Concurrency | 17 (lost update on reserve) | 6, 10 (in-memory: not verifiable) |
| 9 | Symmetry | 1 (hold without resume) | 6, 7 (declared terminals) |
| 10 | Minimal expression | 1, 2, 7 (alias drift) | 7 (_recalc), 10 (historical snapshot) |
| 11 | System limits | 17 (bundles special-cased) | 6 (declared limits are not defects) |
| 12 | Feedback loops | 5 (retry, alert, dead-letter loops) | 6, 1 (clean) |

## Invariant categories and test coverage (F2, F5)

| Behavior | Forward evals | Deterministic |
|---|---|---|
| Catalog with every machine covered | 15, 16, 17 | `G2Model` |
| Implicit machine (co-varying fields) | 17 | `G2Model` (fields required) |
| Category left empty when nothing supports it | 15, 16 (concurrency, atomicity) | — |
| `asserted` with the right technique | 15 (deliver guard), 16, 17 | `G5Tests` (technique fit) |
| `weak`: wrong starting state, single delivery, happy path, partial assertion | 15, 16, 17 | `G5Tests` |
| `contradicted` naming the finding it enshrines | 15, 17 | `G5Tests` |
| `uncovered` with what was searched | 15, 19 | `G5Tests` |
| `not_verifiable` (tests excluded) | 20 | — |
| Technique `example`, `sequence` | 15 | — |
| Technique `property` | 16, 17 | — |
| Technique `metamorphic` | 17 | — |
| Technique `fault_injection` | 17 | — |
| Technique `repetition` | 16 | — |
| Trap: assertion on a mock | 17 | — |
| Trap: snapshot of defective output | 17 | `StockReservations` |
| Trap: `assertRaises(Exception)` | 17 | — |
| Trap: concurrency without an interleaving | 17 | — |
| Trap: setup that relies on a defect without asserting it | 15 | — |
| Finding `detected` (a red test) | 17 | `FixtureSuites` |
| Finding `enshrined` | 15, 17 | `G5Tests`, `FixtureSuites` |
| Finding `undetected` | 15, 17, 19 | `G5Tests` |
| Finding `not_assessed` (tests excluded) | 20 | `G5Tests` |
| Suite `in_scope` | 15, 16, 17 | golden run |
| Suite `absent` | 5, 10, 19 | `G5Tests` |
| Suite `out_of_scope` | 20 | — |
| Matrix cells tested | 16 (all), 17 | `G5Tests`, `G7Report` |
| The suite is read, never run | 15, 16, 17 | — |
| Gaps never become findings or change counts | 15, 17 | `G7Report` |

## Audit of the findings (F4)

| Behavior | Forward evals | Deterministic |
|---|---|---|
| Evidence re-check (quote at the cited line) | 1 | `G4Findings` |
| Refutation: guard in a decorator, dedup in middleware, guarding caller | 7, 12 | — |
| Refutation does not hide recovery defects | 7, 11 | `AdversarialFixtures` |
| Dedup: one finding per root cause | 1 | `G4Findings` |
| Independent causes stay separate | 7, 10 | `AdversarialFixtures` |
| Severity by damage, not domain | 1, 10 | — |
| Justified `critical` (scope, why unrecoverable) | 17 (sweep deletes sales) | `G4Findings` |
| `low` for a bounded fragility | 6, 7 | — |
| Conditional impact without invented latency | 5 | `AdversarialFixtures` |
| Labels INCONSISTENCY, RISK (condition), AMBIGUITY (question) | 1, 2, 5, 17 | `G3Checks` |

## Run, scope and delivery

| Behavior | Forward evals | Deterministic |
|---|---|---|
| `needs_scope` on an unfocused repository | 18 | `G0Scope` |
| graphify read first and disclosed in `full` | 18, 19 | `G7Report` |
| Design document with no code | 2 | — |
| Real repository | 3 | — |
| Report outside fixtures and read-only targets | all | `G0Scope` |
| Name collision: keep the file, new slug | 20 | — |
| Profile `quick` (auto) | 1, 15, 16 | `G0Scope` |
| Profile `standard` (explicit, one log per phase) | 20 | `G0Scope` |
| Language from the conversation | 10, 11, 12, 13 | — |
| Language named explicitly | 4 | — |
| Mode `functional` by default | 11, 13, 15, 18, 20 | `G7Report` |
| Mode `full` only when asked | 1–10, 12, 14, 16, 17, 19 | `G0Scope` |
| Functional hides methodology and internal ids | 11, 15 | `G7Report` |
| Re-audit from a Markdown-only report | 8 | `G6Reaudit` |
| Re-audit by fingerprint | 14 | `G6Reaudit` |
| `resolved` with evidence of the fix | 8, 14 | `G6Reaudit` |
| `not_verified` antecedent | 9, 13 | `G6Reaudit` |
| Mode change keeps the history | 13 | — |
| Incomplete run discloses why | — | `G0Scope`, `RunState` |
| Gates checked by hand without Python | — | — |
| No artifact, HTML or server | 1, 2, 3 | `G7Report` (no HTML) |

The last two rows are known gaps: an incomplete run and a run without Python
cannot be induced reliably from a prompt, so they are covered only by the
validator's own tests or not at all.
