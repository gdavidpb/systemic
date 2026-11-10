# Invariants and how tests protect them

Read this file in F2, to build the invariant catalog, and again in F5, to
audit the tests against it. The catalog is written to `model.json.invariants`
and the audit to `tests.json`; see `references/run-contracts.md`.

An **invariant** is a property the system must keep in every reachable state
or along every execution: "the total is the sum of the items", "a shipped
order is never canceled", "a redelivered webhook changes nothing". The checks
of F3 ask whether the code keeps them. F5 asks a different question: **if the
code stopped keeping one, would the test suite notice?**

Line coverage cannot answer that. It says which code ran, not which property a
test would defend. A test that calls `refund()` and asserts nothing about the
status covers every line of `refund()` and protects no invariant.

## The eight categories

Every invariant gets exactly one category: the one whose violation it
describes. Each category names the kind of test that can catch a violation;
an invariant asserted by a test of the wrong kind is only `weak`.

| Category | What it states | Examples | Related checks | Techniques that can catch a violation |
|---|---|---|---|---|
| `state` | Every state or field combination an operator writes is representable and legal | `status ∈ STATUS`; `paid_at` set exactly when `status ∈ {paid, shipped}`; `stock ≥ 0` | 1, 5 | any |
| `transition` | Only the declared transitions happen; every forbidden one is refused | "a shipped order cannot be canceled"; "refund requires a captured payment" | 3 | any |
| `logical` | Business relations and conservation laws between values | Σ payments = `total_paid`; debits + credits = 0; total = Σ items | 6, 10 | any |
| `temporal` | Properties of whole executions: something bad never happens in that order (safety), something good eventually happens (liveness), a value only grows, a final state is never left | never shipped before paid; every `pending` ends or expires; `version` only increases | 4, 9, 12 | `sequence`, `stateful`, `property` |
| `repetition` | Applying an operation again changes nothing; effects happen at most once | a redelivered webhook does not charge twice; a retried job does not duplicate rows | 7 | `repetition`, `stateful` |
| `concurrency` | Operations that run at the same time commute or are serialized | no lost update on a balance; one lock holder at a time | 8 | `concurrency` |
| `atomicity` | All or nothing; a compensation restores the invariant; every acquire has a release | if the write to B fails, A is rolled back; a reservation is released when shipping fails | 6, 9 | `fault_injection` |
| `algebraic` | Relations between operators: inverses, round trips, commutativity, neutral elements | refund after charge is the identity; `parse(render(x)) = x`; discounts commute | 2, 9, 10 | `metamorphic`, `property` |

Choose by the violation, not by the code that maintains it. "A paused order
resumes to the state it was in" is `algebraic` (resume undoes hold); "every
paused order is eventually resumed or canceled" is `temporal`.

## Building the catalog (F2)

- **Declared** invariants come from the claims `D-n` of F1: README rules,
  docstrings, spec sentences, comments such as `# must never be negative`.
  Link each one to its claims.
- **Inferred** invariants come from the model: every declared state set
  implies a `state` invariant; every guard and every declared forbidden
  transition implies a `transition` invariant; every terminal state implies a
  `temporal` one ("never left"); every re-invokable entry point implies a
  `repetition` one; every multi-write operation implies an `atomicity` one;
  every pair of dual operators implies an `algebraic` one.
- Every machine has at least one invariant. Keep the catalog to the
  properties that matter for the scope: one invariant per rule, not one per
  line. An invariant the code already violates belongs in the catalog all the
  same — it is what the tests should be defending.
- A category with nothing in scope stays empty. Do not invent a concurrency
  invariant for a module nothing runs concurrently; the empty row in the
  report is itself information.

## Recognizing the technique of a test (F5)

Read the test, not its name. Classify by what the test body does:

| Technique | What the test body does |
|---|---|
| `example` | One setup, one operation, assertions on the result |
| `sequence` | Several operations in a meaningful order, with assertions along or after the trace; a fake clock to test deadlines |
| `property` | Generated inputs (Hypothesis, fast-check, QuickCheck, jqwik, table-driven loops over a whole domain) with a universal assertion |
| `stateful` | Generated sequences of operations against a model (`RuleBasedStateMachine`, model-based testing) |
| `repetition` | The same operation or event applied twice or more, including a retry after a failed first attempt and a delayed replay |
| `concurrency` | Threads, tasks or transactions forced to interleave (barriers, latches, two sessions on the same row) |
| `fault_injection` | A dependency made to fail between two writes (a mock that raises, a killed connection), then assertions on what remains |
| `metamorphic` | Two compositions of operators compared with each other rather than with a fixed value |

## Coverage levels

Each invariant gets exactly one level:

- **asserted** — a test contains an assertion that would fail if the
  invariant were violated, and its technique is one that can catch that
  category. Cite the assertion line.
- **weak** — tests exercise the operators involved, but no assertion would
  fail on a violation, or the technique cannot reach it. Typical cases: the
  happy path of a guard (cancel tried only from an allowed state); an
  idempotency rule tested with a single delivery; an atomicity rule tested
  without making anything fail; an equality asserted only at the one moment
  it cannot have drifted yet.
- **contradicted** — a test asserts the opposite of the invariant: it would
  fail if the code were fixed. Cite the assertion. Name the confirmed finding
  it enshrines; when there is none, explain the conflict (usually the
  specification and the test disagree, which is a question for the owner).
- **uncovered** — no test touches it. Say what you searched for.
- **not_verifiable** — the tests are outside the scope or could not be read.

Never run the suite. A green suite proves the assertions hold, not that they
assert the invariants; a red suite proves nothing about which invariant
broke. Read the assertions.

## Traps that look like coverage

Before you mark an invariant `asserted`, rule these out:

- **Asserting the double instead of the state.** `mock.assert_called_once()`
  says the courier was called, not that inventory and shipping stayed
  consistent.
- **Snapshots and golden files.** A snapshot taken from defective output
  asserts the defect. Check what the snapshot contains.
- **Shared fixtures that skip the interesting state.** A fixture that always
  builds a `draft` order means no test ever starts from `shipped`.
- **Exception tests that catch too much.** `assertRaises(Exception)` around
  three calls passes when the wrong one raises.
- **Parametrized tests.** Read the parameter list: it may cover the forbidden
  state, or it may not.
- **Helpers with assertions.** An assertion inside a helper counts; cite the
  helper's line and the test that calls it.

Search before you conclude `uncovered`: helpers, fixtures, parametrizations,
conftest files, base classes and test utilities in other directories.

## Crossing tests with findings

For every confirmed finding of F4, record what the suite does about it:

- **detected** — a test asserts the correct behavior and fails today because
  of this defect.
- **undetected** — no test would fail because of it. Say what is missing.
- **enshrined** — a test asserts the defective behavior and passes because of
  it: fixing the defect turns the suite red. This is the most expensive kind
  of gap, because it tells whoever fixes the bug that they broke something.

These are coverage records, not new findings: they never change a finding's
severity or the count line.
