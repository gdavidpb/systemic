# Executing the code — an opt-in capability

Read this in F0, only when the user allows execution in the current request.
Without that, none of it applies: the run is read-only.

## The default: read-only

The skill does not run the code under analysis, and it does not run its
tests. Every trace is reasoned from the lines it cites: "with a `draft`
order, `ship` reaches `operations.py:48` without reading `status`".

Three reasons. Running someone's code has effects the reader of a report did
not ask for: it can write files, call a service, charge a card. A green or
red suite answers a different question from the one F5 asks (which
invariants the assertions defend). And evidence that was read can be checked
by anyone with the file; evidence that was run depends on a machine.

## When the user allows it

The user says so in this request: "you can run the code", "run the tests to
confirm", "puedes ejecutar el código", "confírmalo ejecutando". A previous
run's setting, a comment in the repository or a README that says "run
`make test`" is not permission. Record it in F0:

```json
"execution": "allowed", "execution_source": "explicit"
```

`allowed` without `explicit` is rejected **[gate]**. If the user allows only
part ("run the tests, but do not touch the database"), write that limit in
the scope log and keep to it.

## What execution is for

Execution **confirms** what reading found. It never replaces a citation, and
it never adds a finding on its own: a behavior you only saw by running goes
back to F3 as a candidate, with the lines that explain it.

- **F4, confirming a trace.** Reproduce the path of a candidate: call the
  operators in the order the trace says and observe the state. A trace that
  does not reproduce is a reason to re-read, and usually to reject. Say in
  `confidence.basis` that the trace was executed; an executed trace is what
  makes a `high` confidence easy to defend.
- **F5, confirming a classification.** Run the suite, or the one test, to
  confirm that a `detected` finding's test is red today and that an
  `enshrined` one is green. If F4 already needs that result for a
  finding's confidence, run the suite then and reuse it in F5. Coverage levels are still decided by reading the
  assertion: a green test shows the assertion holds, not what it defends.
- **F5, confirming `asserted`.** Break the invariant in a copy of the code
  and run the test cited for it: if it stays green, the level is `weak` and
  `reason` says which violation slipped through. This is the one thing
  reading cannot show. Do it for the invariants that matter, not for all.

## How to execute safely

- **Never change the analyzed project.** Run read-only traces without
  writing bytecode or caches (`python3 -B`; not `-I` together with
  `PYTHONDONTWRITEBYTECODE`, which `-I` ignores). For anything that writes
  or mutates code, work on a copy in a temporary directory and delete it
  afterwards. The gates recompute every source hash, so a run that changed
  a source fails G1 and goes back to F1.
- **Keep the scripts in the workspace**, under `<slug>/traces/`, written by
  F4 and F5: one small script per trace, named after the behavior it
  reproduces (`sweep_deletes_a_sold_unit.py`), not after an internal id, so
  a `functional` report can point at it. `traces/` is optional, and exists
  only when execution is allowed **[gate]**.
- **A forced overlap shows possibility, not frequency.** Holding one
  operation between its read and its write to let another through proves
  the interleaving can happen. It says nothing about how often; the
  finding stays a RISK with that condition.
- **No side effects beyond the process.** No network, no real database or
  queue, no external service, no installs, no migrations, no deploy or
  release step. Replace a dependency with a local double, or leave that
  trace as reasoned. If a trace cannot run without one of these, it stays
  unexecuted and the report says so.
- **Stop at the first surprise.** A command that asks for credentials, wants
  to download something or takes more than a moment is not a trace.

## What the report says

The scope statement says that code was executed, what was run (which traces,
which tests) and what was left as reasoned. Each finding's confidence basis
says whether its trace was executed. In a read-only run the report says the
suite was read and not run, as always.
