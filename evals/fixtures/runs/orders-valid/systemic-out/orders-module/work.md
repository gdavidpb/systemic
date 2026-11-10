# Work log — orders-module

Profile `quick`: one log for every phase.

## F0 Scope
Four source files and one test module of the orders fixture; full mode requested explicitly; language follows the conversation (en).

## F1 Silhouette
All five files read in full; test_orders.py recorded with role test. Nine declared claims extracted from README.md (D-1..D-9).

## F2 Model
One system, three elements, ten operators, one explicit machine with nine states (eight declared plus refund_pending). Eight invariants catalogued: state 1, transition 2, logical 1, temporal 1, repetition 1, atomicity 1, algebraic 1; no concurrency invariant, since nothing in scope runs concurrently.

## F3 Verification
Ten candidates. Checks 5, 8 and 11 not verifiable; check 12 clean.

## F4 Audit
C-10 rejected: deliver guards its source state. C-9 merged into the refund closure finding. Eight confirmed.

## F5 Test audit
Six tests read, none run. I-3 asserted by the refusal test of deliver. I-1 contradicted: the refund test asserts refund_pending, so the suite enshrines the closure finding. I-2, I-4, I-6 and I-7 weak (wrong starting state, single delivery, happy path only). I-5 and I-8 uncovered after searching for any call on a final order or to hold. Four of nineteen testable matrix cells exercised. Seven findings undetected.

## F6 Reconcile
Skipped: no previous report.

## F7 Report
Rendered full mode from findings.json, checks.json, model.json and tests.json.
