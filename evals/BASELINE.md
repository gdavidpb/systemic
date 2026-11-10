# Baseline — the held-out cases with the skill and without it

What the skill adds, measured on the two cases its text was never tuned
against (evals 24 and 25, `split: holdout`). Each case ran twice from the
same request: once following the skill, once with no skill at all.

Read the numbers for what they are: **one run per cell**, graded by reading
each report against the case's assertions and, for the skill runs, by
`systemic_check.py all`. One run cannot separate a real difference from
noise. Re-run and replace this table when the skill changes; do not edit the
skill to move a number here.

Recorded 2026-11-10, on the skill as of the commit that added this file.

## Result

Assertions are split in two. **Substance** is what a reader needs to be true
whatever the format: the planted defects found, the defended paths not
reported, the test gaps judged correctly. **Form and process** is what only
the skill promises: honesty labels, the invariant coverage table, technique
labels the validator accepts, the suite read and not run, a workspace that
validates.

| Case | Run | Substance | Form and process | Tokens | Time |
|---|---|---|---|---|---|
| 24 `job-leases` (JavaScript) | with skill | 10 / 10 | 4 / 4 | 236k | 18.8 min |
| | without | 10 / 10 | 0 / 4 | 109k | 5.1 min |
| 25 `approvals` (Python, SQL) | with skill | 9 / 9 | 3 / 3 | 197k | 12.6 min |
| | without | 9 / 9 | 0 / 3 | 107k | 4.7 min |

## What this says

**The skill did not find more defects.** Without it, the model found every
planted defect in both cases, refuted the same defended paths and judged the
same tests as misleading. It also found real defects nobody had planted
(stale reaper writes in `job-leases`; a refused event landing on a
resubmission and a `connect()` that cannot reopen a database in
`approvals`), which is why the answer keys now allow them and
`test_adversarial_fixtures.py` executes each one. On fixtures this small,
detection is not where the skill earns its cost.

**What the skill run had and the other did not:**

- Every citation checked against the file by the validator (`OK all` in both
  runs), where the other report cites functions, scenarios and some lines
  that nothing verified.
- One coverage level per invariant (15 in each case) with the assertion that
  justifies it, and every finding classified against the suite: in
  `job-leases`, one `detected`, one `enshrined`, seven `undetected`.
- Fixed labels and severities, and a workspace that makes the next run a
  re-audit.
- Unanswered specification questions kept apart as AMBIGUITY rather than
  mixed into the defects.

**What the other run had and the skill run did not:**

- It ran things. It executed the suite, wrote reproduction scripts and ran a
  mutation check (28 mutants in `job-leases`, 29 in `approvals`), which
  showed that about half of the injected breakages pass the suite. The skill
  forbids running the suite, so it can say that a test would fail but not
  show it. Since then the skill can do this too, but only when the user
  allows it (`references/execution.md`); these runs were read-only.
- It cost about half the tokens and a third of the time.

**One disagreement on severity.** In `approvals` the skill run rated the
drifting `pending_count` `high`; the run without it rated it `medium`. The
skill run pointed at two texts that disagree: the rubric in `SKILL.md` puts
any incorrect behavior a user can observe at `high`, while
`references/checks.md` (check 10) says `medium` when the derived value is
presentation-only, which is what the fixture's README declares. The
assertion accepts `high` with a stated reason, so it passes. The conflict
between the two texts was real. It was resolved afterwards in the general
rule, not against this case: both now say that a wrong value which is only
displayed, which nothing decides on and which can be recomputed is
`medium`. The table above is the run before that change.

**Case 25 again, after the change.** One more run with the skill, on the
same fixture: the drift is rated `medium`, citing the display-only clause,
with the note that it becomes `high` if anything decides on the count;
12 / 12 assertions, `systemic_check.py all` passes, no gate failed (203k
tokens, 12.9 min). It also ran nothing: `execution: read_only`, where the
first run had executed three traces before the skill said whether it could.

## Limits of this measurement

- One run per cell, graded by the author of the change under test.
- The independent verifier of F4 was **not exercised**: the runs were
  themselves subagents, which cannot spawn another, so every finding is
  `verification: self`.
- Token and time figures are whole-run totals reported by the harness, and
  include reading the skill.
- The fixtures are small (four or five files). A larger scope, a re-audit or
  a resumed run is where a recorded workspace should matter more, and none
  of that is measured here.

## Regression runs on dev cases

The same change moved text out of `SKILL.md` into references, so three dev
cases that depend on the moved text were re-run with the new skill. All
three ended `complete` with `systemic_check.py all` passing.

| Eval | Depends on | Outcome |
|---|---|---|
| 1 orders | `references/dedup.md`, the `hash` and `counts` helpers | All nine expected defects; the missing guards are one check-3 finding with each operator as a manifestation; no gate failed |
| 9 re-audit | `references/reaudit.md` | The antecedent is `not verified` and outside the severity totals; counts `new: 1 · persisting: 0 · resolved: 0 · not verified: 1`. It also reported one new `low` finding in the façade's own validation, which the case's "does not invent a new concrete defect" assertion may or may not allow |
| 21 resume | `references/run-protocol.md` | Logged `resumed`, ran `all`, logged the failure under F1, returned to F1 with the reason, rebuilt F1–F8; no finding says a shipped order can be canceled |

## The execution capability (eval 26)

Added after the runs above, and run once with the skill. The request allowed
running the code and the tests.

| Eval | Outcome | Tokens | Time |
|---|---|---|---|
| 26 `stock-reservations`, execution allowed | 11 / 11 assertions; `systemic_check.py all` passes; no gate failed. `execution: allowed` with an explicit source; nine finding traces, the suite and thirteen mutated copies executed; scripts kept under `traces/`; every fixture file byte for byte unchanged, no cache left behind. The snapshot, mock and fake-concurrency tests are green and still not credited | 227k | 16.7 min |

## Trigger evals

`trigger-evals.json` against the description in `SKILL.md`, measured with the
trigger evaluation of Anthropic's `skill-creator` (`scripts/run_eval.py`,
which registers the description as a skill in an empty project and watches
whether a headless `claude -p` invokes it first). Three runs per query.

| Queries | Expected | Result |
|---|---|---|
| 10 that should trigger | invoked | 10 / 10, each 3 of 3 runs |
| 10 that should not | not invoked | 10 / 10, each 0 of 3 runs |

The description was left as it is: there was nothing to optimize.

**A measurement trap.** The first attempt scored 10 / 20, with every
should-trigger query failing. The description was not at fault. With
`--num-workers` above 1, each worker registers its own copy of the skill
under a different name in the same project; the model sees several
identical skills, invokes any one of them, and each worker counts only its
own copy. Run it with `--num-workers 1`, and for parallelism use separate
project directories:

```sh
mkdir -p /tmp/trigger-1/.claude && cd /tmp/trigger-1
PYTHONPATH=<skill-creator> python3 -m scripts.run_eval \
  --eval-set <skill>/evals/trigger-evals.json --skill-path <skill> \
  --runs-per-query 1 --num-workers 1 --timeout 90 --verbose
```

What this does not measure: the queries name files that do not exist in the
empty project, so only the decision to invoke the skill is tested, not what
it does next; and the other skills installed on the machine compete for the
same requests, so the result depends on that set.

## How to reproduce

1. Copy `SKILL.md`, `references/`, `scripts/` and only the case's fixture to
   an isolated directory. Leave out `evals.json`, `COVERAGE.md` and the
   test files: they contain the answers.
2. With the skill: give the case's prompt, with the copy's path for
   `<SKILL_DIR>`, from an empty working directory.
3. Without it: copy the fixture alone to another directory and give the same
   request with that path, with no mention of the skill.
4. Grade both against the case's assertions; run `systemic_check.py all` on
   the skill run's workspace.
