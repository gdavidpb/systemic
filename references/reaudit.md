# Re-audit — reconciling with the previous report (F6)

Read this in F6, only when `run.json.prior_report` is not null. F0 archived
the previous report under `prior/`; this phase says what happened to each of
its findings. The shape of `reaudit.json` and the rules G6 enforces are in
`references/run-contracts.md`.

## Classify every previous finding

- **persisting**: the old root cause is still evidenced. It passed F4 like
  any other finding (never copied on faith) and points to the current
  fingerprint that continues it.
- **resolved**: current evidence shows the old defect is corrected, or an
  explicit contract change makes the old requirement inapplicable. Cite
  that evidence. A missing file, moved implementation or stale citation
  alone does not prove a fix.
- **not verified**: the old finding cannot be confirmed or resolved with
  the current material or scope, including behavior delegated to an
  unavailable service. Keep its last verified evidence, what changed, and
  what is needed to verify it. Do not present its old severity as a
  current verified finding.

Every current finding without a predecessor is **new**.

## Matching old findings to current ones

- With format `json` (`prior/findings.json` exists), match by fingerprint
  first and confirm by root cause: the same fingerprint over a different
  defect is not a continuation.
- With format `md-legacy` (only `prior/report.md`), match each previous
  `### [severity] [LABEL]` heading by its cited evidence and root cause.

## What the counts mean

The re-audit counts (`new`, `persisting`, `resolved`, `not verified`) track
review status, independently of the honesty labels. Unverified antecedents
are not included in the current findings-per-severity totals. Switching
modes does not reset the history, and an older `full` report does not force
`full` next time.
