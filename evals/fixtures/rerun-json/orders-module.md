# Systemic analysis — orders module

## Executive summary

First pass over the state machine of the orders module (`models.py`,
`operations.py`). Two findings: critical: 0 · high: 2 · medium: 0 · low: 0.
Items, discounts, payments, the webhook and shipping were left out of this
pass and remain unverified.

## Findings

### [high] [INCONSISTENCY] refund() writes a status outside the system

- **Check**: 1
- **Evidence**: `operations.py:40` — `order.status = "refund_pending"`, a
  value absent from `STATUS` (`models.py:6`)
- **Systemic diagnosis**: the operator produces a state the system cannot
  represent.
- **Recommendation**: declare the state and its exits, or remove the operator.

### [high] [RISK] deliver() accepts any status

- **Check**: 3
- **Evidence**: `operations.py:51` — `order.status = "delivered"` with no
  guard on the current status
- **Systemic diagnosis**: a hole in the state × operator matrix.
- **Recommendation**: guard `deliver()` so only `shipped` orders are delivered.

## Limits and not-verified

| # | Check | Verdict | Evidence / why |
|---|---|---|---|
| 1 | Closure | findings | refund writes refund_pending |
| 2 | Operator ambiguity | not verifiable | discounts were out of this pass |
| 3 | Transition completeness | findings | deliver has no guard |
| 4 | Reachability | not verifiable | not examined in this pass |
| 5 | Illegal states representable | not verifiable | not examined in this pass |
| 6 | Invariants and partial failure | not verifiable | shipping was out of this pass |
| 7 | Idempotency | not verifiable | the webhook was out of this pass |
| 8 | Concurrency | not verifiable | not examined in this pass |
| 9 | Symmetry | not verifiable | not examined in this pass |
| 10 | Minimal expression | not verifiable | totals were out of this pass |
| 11 | System limits | not verifiable | not examined in this pass |
| 12 | Feedback loops | not verifiable | not examined in this pass |
