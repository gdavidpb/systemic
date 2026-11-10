# Run contracts — the files every phase writes

A run keeps its state in a workspace next to the report:

```
systemic-out/
├── <slug>.md           the report (F6)
└── <slug>/             the run workspace
    ├── run.json        F0, updated by every phase
    ├── sources.json    F1
    ├── model.json      F2
    ├── checks.json     F3
    ├── findings.json   F4
    ├── reaudit.json    F5, only when a previous report exists
    ├── prior/          F0, only on a re-audit: report.md (+ findings.json)
    └── 00-scope.md … 05-reaudit.md   phase logs (profile standard)
        or work.md                    single log (profile quick)
```

The JSON files are the source of truth. The report is rendered from them and
must not add, drop or re-rate anything they contain. `scripts/systemic_check.py`
enforces every rule marked **[gate]** below. Read this file in F0 and write
each file to this shape.

Conventions:

- **IDs** are stable within a run: `D-n` declared claim, `S-n` system,
  `E-n` element, `O-n` operator, `M-n` machine, `T-n` transition,
  `V-n` divergence, `C-n` candidate.
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
| `schema` | `"systemic.run/1"` |
| `slug` | kebab-case scope name; the report is `systemic-out/<slug>.md` **[gate]** |
| `scope` *(text)* | what is analyzed, in one sentence |
| `mode`, `mode_source` | `functional`\|`full`; `explicit`\|`default`. `full` requires `explicit` **[gate]** |
| `language`, `language_source` | e.g. `"es"`; `explicit`\|`conversation` |
| `profile`, `profile_source` | `quick`\|`standard`; `explicit`\|`auto` |
| `source_root` | directory the citations are relative to; absolute, or relative to the project root |
| `targets` | files or directories under `source_root`; each must exist **[gate]** |
| `report_path`, `report_path_source` | relative to the project root, no `..`, never inside `node_modules`, `vendor`, `.git`, `fixtures`, a virtualenv **[gate]**; `default`\|`user` |
| `prior_report` | `null`, or `{"path", "format": "json"\|"md-legacy"}`; see Re-audit below |
| `source_ref` | `{"commit": <sha or null>, "dirty": <bool or null>}` |
| `validation` | `script` when the validator ran; `manual` when it could not |
| `phase` | the phase in progress, `F0`…`F7` |
| `status` | `in_progress`, `needs_scope`, `complete`, `incomplete` |
| `scope_proposal` *(text)* | required when `status` is `needs_scope` **[gate]** |
| `incomplete_reason` *(text)* | required when `status` is `incomplete` **[gate]** |
| `log` | `[{"phase", "event": "gate_passed"\|"gate_failed"\|"returned_to"\|"skipped", "detail"}]`; `skipped` records F5 when there is no previous report |

**Re-audit setup.** When `systemic-out/<slug>.md` already exists and is a
systemic report of the same scope, F0 archives it before anything is
overwritten. The report goes to `<slug>/prior/report.md`. A previous
`<slug>/findings.json`, if there is one, goes to `<slug>/prior/findings.json`;
in that case `format` is `json`, otherwise `md-legacy` **[gate]**. Discard the
rest of the previous workspace, including any older `prior/`.

## `sources.json` — F1

```json
{
  "files":   [{"path": "operations.py", "sha256": "…", "lines": 55, "read": "full"}],
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
  "claims_satisfied": ["D-7"]
}
```

- `states` is the built figure: declared states plus any state the code
  writes. Every declared state is in it **[gate]**.
- `from: "*"` means the operator writes the target state from any state
  (no guard).
- Every transition names a modeled operator and states of its machine **[gate]**.
- An `implicit` machine (co-varying flags and nullable fields) lists `fields` **[gate]**.
- Every claim is either in `claims_satisfied` or linked to a divergence **[gate]**.

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
  - `hole`: the operator proceeds without considering this state, including
    a write the declared rules forbid.
  Every `hole` has a note naming a candidate or explaining it **[gate]**.
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

## `reaudit.json` — F5

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

## The report — F6

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
  table **[gate]**.
- No HTML tags outside code blocks **[gate]**.
- When `status` is `incomplete`, the report must exist and its first section
  states the reason. The finding checks are skipped.

## Running the validator

```sh
python3 <skill-dir>/scripts/systemic_check.py G3 systemic-out/<slug>
python3 <skill-dir>/scripts/systemic_check.py all systemic-out/<slug>
```

The project root defaults to two levels above the workspace; pass
`--project-root DIR` otherwise. Exit `0` passes, `1` lists one violation per
line (`G4 findings.json confirmed[0].evidence[0]: quote not found at
operations.py:40±2`), and `2` means the workspace could not be read. `all`
validates every finished phase, so it can be run mid-run.
