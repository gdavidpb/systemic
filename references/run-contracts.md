# Run contracts — the files every phase writes

A run keeps its state in a workspace next to the report:

```
systemic-out/
├── <slug>.md           the report (F7)
└── <slug>/             the run workspace
    ├── run.json        F0, updated by every phase
    ├── sources.json    F1
    ├── model.json      F2
    ├── checks.json     F3
    ├── findings.json   F4
    ├── tests.json      F5
    ├── reaudit.json    F6, only when a previous report exists
    ├── prior/          F0, only on a re-audit: report.md (+ findings.json)
    └── 00-scope.md … 06-reaudit.md   phase logs (profile standard)
        or work.md                    single log (profile quick), one
                                      `## F<n>` section per finished phase **[gate]**
```

The JSON files are the source of truth. The report is rendered from them and
must not add, drop or re-rate anything they contain. `scripts/systemic_check.py`
enforces every rule marked **[gate]** below. Read this file in F0 and write
each file to this shape.

Conventions:

- **IDs** are stable within a run: `D-n` declared claim, `S-n` system,
  `E-n` element, `O-n` operator, `M-n` machine, `T-n` transition,
  `V-n` divergence, `I-n` invariant, `C-n` candidate, `X-n` test.
- **Citation**: `{"file": "<path>", "line": <n>, "quote": "<text>"}`.
  `file` is exactly a `path` recorded in `sources.json` (relative to
  `source_root`). `quote` is copied from the file and must appear within
  `line ± 2` after whitespace normalization **[gate]**. `quote` is optional in
  `model.json` and in claims, and required for candidates, findings,
  rejections and resolutions **[gate]**.
- **Substantive text**: fields marked *(text)* must be at least 12 characters and
  must not be filler such as `ok`, `n/a`, `none`, `todo` **[gate]**.
- Human-readable text (titles, claims, diagnoses) is written in the report's
  language. Enum values, labels, severities and keys stay in English.

## `run.json` — F0

| Field | Value |
|---|---|
| `schema` | `"systemic.run/2"` |
| `slug` | kebab-case scope name; the report is `systemic-out/<slug>.md` **[gate]** |
| `scope` *(text)* | what is analyzed, in one sentence |
| `mode`, `mode_source` | `functional`\|`full`; `explicit`\|`default`. `full` requires `explicit` **[gate]** |
| `language`, `language_source` | e.g. `"es"`; `explicit`\|`conversation` |
| `profile`, `profile_source` | `quick`\|`standard`; `explicit`\|`auto` |
| `source_root` | directory the citations are relative to; absolute, or relative to the project root |
| `targets` | files or directories under `source_root`, including the test files of the scope unless the user excluded them (excluded tests go in `sources.json.excluded` with the user's reason, never in `targets`); each must exist **[gate]** |
| `report_path`, `report_path_source` | relative to the project root, no `..`, never inside `node_modules`, `vendor`, `.git`, `fixtures`, a virtualenv **[gate]**; `default`\|`user` |
| `prior_report` | `null`, or `{"path", "format": "json"\|"md-legacy"}`; see Re-audit below |
| `source_ref` | `{"commit": <sha or null>, "dirty": <bool or null>}` |
| `validation` | `script` when the validator ran; `manual` when it could not |
| `graph_informed` | `true` when `graphify-out/graph.json` informed the scope; omitted or `false` otherwise |
| `phase` | the phase in progress, `F0`…`F8` |
| `status` | `in_progress`, `needs_scope`, `complete`, `incomplete` |
| `scope_proposal` *(text)* | required when `status` is `needs_scope` **[gate]** |
| `incomplete_reason` *(text)* | required when `status` is `incomplete` **[gate]** |
| `log` | `[{"phase", "event": "gate_passed"\|"gate_failed"\|"returned_to"\|"skipped", "detail"}]`; `skipped` records F6 when there is no previous report |

**Re-audit setup.** When `systemic-out/<slug>.md` already exists and is a
systemic report of the same scope, F0 archives it before anything is
overwritten. The report goes to `<slug>/prior/report.md`. A previous
`<slug>/findings.json`, if there is one, goes to `<slug>/prior/findings.json`;
in that case `format` is `json`, otherwise `md-legacy` **[gate]**. Discard the
rest of the previous workspace, including any older `prior/`.

## `sources.json` — F1

```json
{
  "files":   [{"path": "operations.py", "sha256": "…", "lines": 55, "read": "full"},
              {"path": "tests/test_orders.py", "sha256": "…", "lines": 70, "read": "full", "role": "test"}],
  "excluded": [{"path": "legacy/", "reason": "generated client, no state"}],
  "claims":  [{"id": "D-2", "text": "Only draft or pending_payment orders can be canceled",
               "file": "README.md", "line": 11}]
}
```

- `sha256` and `lines` describe the file as read **[gate]**. If a later phase
  finds a different hash, the source changed during the run: return to F1.
- `read: "partial"` requires `ranges: [[start, end], …]`. A citation outside
  those ranges is rejected **[gate]**, so a partially read file cannot support
  a claim about what was not read.
- Every target is read or excluded with a reason **[gate]**.
- `claims` are the *silhouette*: what README, docstrings, specs, comments
  and declared constants promise.
- `role` is `source` (the default) or `test` **[gate]**. Test files are read
  in F1 like any other file; F5 cites only files recorded with `role: test`
  as evidence that a test asserts something. A test's assertions are not
  claims: what the suite asserts is audited in F5, not promised in F1.

## `model.json` — F2

```json
{
  "systems":   [{"id": "S-1", "name": "Orders", "objective": "…", "elements": ["E-1"], "operators": ["O-1"]}],
  "elements":  [{"id": "E-1", "name": "Order", "representation": "…", "evidence": [cite]}],
  "operators": [{"id": "O-7", "name": "refund", "acts_on": ["E-1"], "result": "…",
                 "preconditions": "…", "evidence": [cite]}],
  "machines":  [{"id": "M-1", "name": "Order status", "kind": "explicit", "element": "E-1",
                 "fields": ["status"], "declared_states": ["draft", "…"], "declared_in": cite,
                 "states": ["draft", "…", "refund_pending"], "initial": "draft",
                 "terminal": ["delivered", "canceled"],
                 "transitions": [{"id": "T-5", "from": "*", "to": "refund_pending",
                                  "operator": "O-7", "evidence": [cite]}]}],
  "divergences": [{"id": "V-1", "claims": ["D-2"], "description": "…", "evidence": [cite]}],
  "claims_satisfied": ["D-7"],
  "invariants": [{"id": "I-6", "category": "repetition",
                  "statement": "Redelivering a payment event leaves total_paid unchanged",
                  "machine": null, "operators": ["O-10"], "source": "declared",
                  "claims": ["D-6"], "evidence": [cite]}]
}
```

- `states` is the built figure: declared states plus any state the code
  writes. Every declared state is in it **[gate]**.
- `from: "*"` means the operator writes the target state from any state
  (no guard).
- Every transition names a modeled operator and states of its machine **[gate]**.
- An `implicit` machine (co-varying flags and nullable fields) lists `fields` **[gate]**.
- Every claim is either in `claims_satisfied` or linked to a divergence **[gate]**.
- `invariants` is the catalog of `references/invariants.md`. Each has a
  unique `I-n`, a `category` among `state`, `transition`, `logical`,
  `temporal`, `repetition`, `concurrency`, `atomicity`, `algebraic`, a
  `statement` *(text)* and at least one citation; `machine` and `operators`
  are modeled ids **[gate]**.
- `source` is `declared` (it names the claims `D-n` that declare it) or
  `inferred` from the model **[gate]**.
- Every machine is referenced by at least one invariant **[gate]**.

## `checks.json` — F3

```json
{
  "checks": [
    {"id": 1, "name": "closure", "verdict": "findings", "candidates": ["C-1"]},
    {"id": 8, "name": "concurrency", "verdict": "not_verifiable", "missing": "…"},
    {"id": 12, "name": "feedback loops", "verdict": "clean", "verified": "…", "evidence": [cite]}
  ],
  "matrices": [{"machine": "M-1", "operators": ["O-3", "O-5"],
                "rows": {"draft": ["defined", "defined"], "shipped": ["hole", "hole"]},
                "notes": {"shipped/O-5": {"candidate": "C-3"}, "shipped/O-3": {"note": "…"}}}],
  "candidates": [{"id": "C-1", "check": 1, "label": "INCONSISTENCY", "claim": "…",
                  "evidence": [cite], "refs": ["T-5"], "condition": null, "question": null}]
}
```

- Exactly twelve checks, ids 1–12 **[gate]**.
- `clean` needs `verified` *(text)* and at least one citation; `not_verifiable`
  needs `missing` *(text)*; `findings` needs at least one candidate of that
  check **[gate]**. Missing evidence is `not_verifiable`, never `clean`.
- Every candidate is listed under its own check **[gate]**.
- `RISK` candidates need `condition` *(text)*; `AMBIGUITY` candidates need
  `question` *(text)* **[gate]**.
- Every machine with ≤ 8 declared states (built states when none are
  declared) has a matrix unless check 3 is `not_verifiable` **[gate]**. It has
  a row for every built state and one cell per operator **[gate]**:
  - `defined`: the operator performs a transition the declared rules allow
    from this state.
  - `guarded`: the operator refuses this state with an explicit check.
    An operator that deliberately leaves this state untouched (a sweep that
    filters it out, an idempotent no-op) is also `guarded`, with a note.
  - `hole`: the operator proceeds without considering this state, including
    a write the declared rules forbid.
  Every `hole` has a note naming a candidate or explaining it **[gate]**.
- `refs` names the model ids a candidate rests on: transitions `T-n`, and
  the invariants `I-n` it breaks, so F5 can ask whether a test would catch it.
- Candidates are hypotheses. They become findings only in F4.

## `findings.json` — F4

```json
{
  "confirmed": [{
    "fingerprint": "operations.py:refund:closure:undeclared-state",
    "candidate": "C-1",
    "title": "refund() writes a status outside the system",
    "label": "INCONSISTENCY", "severity": "high", "check": 1,
    "root_cause": "…",
    "manifestations": ["C-9: refund_pending is absorbing (check 4)"],
    "evidence": [cite],
    "condition": null, "question": null,
    "impact": {"demonstrated": "…", "conditional": null, "not_verified": null},
    "confidence": {"level": "high", "basis": "…"},
    "recommendation": "…"
  }],
  "rejected": [{"candidate": "C-10", "reason": "…", "evidence": [cite]}],
  "merged":   [{"candidate": "C-9", "into": "operations.py:refund:closure:undeclared-state"}]
}
```

- Every candidate ends in exactly one of `confirmed` (as its `candidate`),
  `rejected` or `merged` **[gate]**.
- `fingerprint`: `<file>:<operator or field>:<property>:<defect>`, lowercase,
  `[a-z0-9._:/-]` **[gate]**. Derive it from the root cause, not from the
  title or the wording, so the same defect gets the same fingerprint on the
  next run. Unique within the run **[gate]**.
- `root_cause`, `recommendation`, `impact.demonstrated` and `confidence.basis`
  are *(text)* **[gate]**.
- `critical` requires `impact.scope` and `impact.unrecoverable_because`
  *(text)* **[gate]**: the rubric's amount or scope, and why recovery cannot
  contain it.
- Labels are `INCONSISTENCY`, `RISK`, `AMBIGUITY`; severities `critical`,
  `high`, `medium`, `low`; confidence `high`, `medium`, `low` **[gate]**.
- `title` is the exact heading text used in the report.

## `tests.json` — F5

```json
{
  "suite": {"status": "in_scope", "files": ["tests/test_orders.py"],
            "searched": "test_*.py and tests/ under the module root", "reason": null},
  "tests": [{"id": "X-6", "name": "test_full_payment_marks_the_order_paid",
             "technique": "example", "operators": ["O-10"], "evidence": [cite]}],
  "coverage": [
    {"invariant": "I-3", "level": "asserted", "tests": ["X-4"], "evidence": [cite],
     "reason": null, "finding": null},
    {"invariant": "I-6", "level": "weak", "tests": ["X-6"], "evidence": [],
     "reason": "each event is delivered once", "finding": null},
    {"invariant": "I-1", "level": "contradicted", "tests": ["X-5"], "evidence": [cite],
     "reason": "…", "finding": "operations.py:refund:closure:undeclared-state"}
  ],
  "cells_tested": [{"machine": "M-1", "cell": "pending_payment/O-9", "tests": ["X-4"]}],
  "finding_gaps": [
    {"finding": "operations.py:refund:closure:undeclared-state", "status": "enshrined",
     "tests": ["X-5"], "evidence": [cite], "note": "…"},
    {"finding": "webhook.py:handle_payment_webhook:idempotency:no-dedup",
     "status": "undetected", "tests": [], "evidence": [], "note": "…"}
  ],
  "by_category": {"state": {"total": 1, "asserted": 0, "weak": 0, "contradicted": 1,
                            "uncovered": 0, "not_verifiable": 0}}
}
```

- `suite.status` **[gate]**:
  - `in_scope`: `files` are recorded in `sources.json` with `role: test`, and
    `tests` lists at least one test.
  - `absent`: `searched` *(text)* says where tests were looked for; no file
    has `role: test`; every invariant is `uncovered` and every finding
    `undetected`.
  - `out_of_scope`: `reason` *(text)*; no file has `role: test`; every
    invariant is `not_verifiable` and every finding `not_assessed`.
- `tests`: unique `X-n`, a `name`, a `technique` among `example`,
  `sequence`, `property`, `stateful`, `repetition`, `concurrency`,
  `fault_injection`, `metamorphic`, modeled `operators`, and a quoted
  citation in a `role: test` file **[gate]**.
- `coverage`: exactly one entry per invariant **[gate]**, with a `level`:
  - `asserted`: at least one test and a quoted citation of the assertion in a
    `role: test` file **[gate]**. For `temporal`, `repetition`,
    `concurrency`, `atomicity` and `algebraic`, at least one of those tests
    uses a technique that can catch the category (the table in
    `references/invariants.md`); otherwise the level is `weak` **[gate]**.
  - `weak`: at least one test and `reason` *(text)* **[gate]**.
  - `contradicted`: at least one test, a quoted citation of the assertion,
    and either `finding` (a confirmed fingerprint) or `reason` *(text)*
    **[gate]**.
  - `uncovered`, `not_verifiable`: `reason` *(text)* **[gate]**.
- `cells_tested`: cells of a matrix in `checks.json` that are `defined` or
  `guarded`, never a `hole`, each with at least one test **[gate]**. A
  `guarded` cell counts only when the test expects the refusal. A test that
  drives a hole is recorded in `tests[].operators`; holes are not tested
  cells.
- `finding_gaps`: every confirmed finding exactly once, `detected`,
  `undetected`, `enshrined`, or `not_assessed` (only, and always, when the
  suite is `out_of_scope`); `detected` and `enshrined` need tests and a
  quoted citation **[gate]**. A finding named by a `contradicted` coverage
  entry is `enshrined` **[gate]**.
- `by_category` has the eight categories and equals the count the validator
  recomputes from `invariants` and `coverage` **[gate]**. Never write it by
  hand: write `{}`, run G5 and copy the JSON it prints.

## `reaudit.json` — F6

```json
{
  "prior": {"path": "systemic-out/orders-module/prior/report.md", "format": "json"},
  "prior_findings": [
    {"key": "operations.py:refund:closure:undeclared-state", "title": "…",
     "status": "persisting", "current": "operations.py:refund:closure:undeclared-state"},
    {"key": "operations.py:deliver:completeness:no-guard", "title": "…",
     "status": "resolved", "resolution": "…", "evidence": [cite]},
    {"key": "…", "title": "…", "status": "not_verified",
     "last_evidence": "…", "changed": "…", "needed": "…"}
  ],
  "new": ["operations.py:hold:symmetry:no-resume"],
  "counts": {"new": 1, "persisting": 1, "resolved": 1, "not_verified": 1}
}
```

- `key` is the previous fingerprint (`json`) or the previous heading title
  (`md-legacy`). With `json`, the keys are exactly the previous
  fingerprints. With `md-legacy`, there is one entry per previous
  `### [severity] [LABEL]` heading **[gate]**.
- `persisting` points to the current fingerprint that continues it. A current
  finding is either `new` or the continuation of exactly one previous
  finding **[gate]**.
- `resolved` needs `resolution` *(text)* and quoted evidence of the
  correction or the contract change **[gate]**. A moved file or a stale
  citation is not a resolution.
- `not_verified` needs `last_evidence`, `changed` and `needed` *(text)* **[gate]**.
  It is not counted in the current severity totals.
- `counts` match the entries **[gate]**.

## The report — F7

The validator reads the rendered Markdown and checks it against the records:

- One heading per confirmed finding, `### [severity] [LABEL] <title>`, with
  the recorded severity and label **[gate]**.
- Before the first finding heading, a count line with the fixed keywords:
  `critical: N · high: N · medium: N · low: N` **[gate]**. On a re-audit,
  also `new: N · persisting: N · resolved: N · not verified: N` **[gate]**.
  Like labels and severities, these keywords are not translated.
- `full`: a coverage table with one row per check 1–12. Its third column
  starts with `findings`, `clean` or `not verifiable`, matching
  `checks.json` **[gate]**.
- `functional`: no mermaid block, no `**Check**` lines, no twelve-check
  table, and no internal ids such as `I-3`, `X-4`, `C-2`, `M-1`, `O-5` or
  `T-1` **[gate]**.
- Both modes: an invariant coverage table with one row per category,
  `| state | total | asserted | weak | contradicted | uncovered | not verifiable |`,
  whose numbers equal `tests.json.by_category` **[gate]**. Category names and
  levels are fixed keywords, not translated; the header row is translated.
- `full`: for every machine with a matrix, the line
  `<machine id> cells tested: N/M`, where M counts the `defined` and
  `guarded` cells and N those in `cells_tested` **[gate]**.
- Coverage gaps never add a `### [severity] [LABEL]` heading and never change
  the count line.
- No HTML tags outside code blocks **[gate]**.
- When `graph_informed` is true, a `full` report says that graphify informed
  the scope, and a `functional` report does not mention graphify **[gate]**.
- When `status` is `incomplete`, the report must exist and its first section
  states the reason. The finding checks are skipped.

## Running the validator

```sh
python3 <skill-dir>/scripts/systemic_check.py G5 systemic-out/<slug>
python3 <skill-dir>/scripts/systemic_check.py all systemic-out/<slug>
```

The project root defaults to two levels above the workspace; pass
`--project-root DIR` otherwise. Exit `0` passes, `1` lists one violation per
line (`G4 findings.json confirmed[0].evidence[0]: quote not found at
operations.py:40±2`), and `2` means the workspace could not be read. `all`
validates every finished phase, so it can be run mid-run.
