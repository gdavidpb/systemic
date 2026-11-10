# Functional output (default)

This format presents the same verified findings as `full` for practical
decision-making. Describe the failed behavior, its trigger and its consequence
without GST terminology, check numbers, diagrams, state matrices, inventories
or theoretical architecture explanations. Concise does not mean incomplete:
retain independent findings, severity, honesty labels, evidence, conditions,
confidence and unverified antecedents.

Render it from `findings.json`, `tests.json` (and `reaudit.json` on a
re-audit), never from memory. Gate G7 checks the result against those records; see
`references/run-contracts.md`.

Use this structure, translating headings and prose into the report's language:

```markdown
# Functional findings — <scope>

## Summary
<What was reviewed and the most consequential effect, plus the count line,
whose keywords stay in English in every language:>
critical: N · high: N · medium: N · low: N
<For re-audits, also:>
new: N · persisting: N · resolved: N · not verified: N

## Findings
<Order by severity. For each finding:>
### [severity] [LABEL] <title, exactly as recorded in findings.json>
- **What happens and when**: <expected behavior versus actual behavior;
  concrete trigger or plausible condition, without inventing incidence>
- **Functional impact**: <who or what is affected, blocked or incorrect;
  separate demonstrated consequences from conditional or unverified effects>
- **Evidence and confidence**: <relative file:line or document section;
  concise observation/trace; confidence high/medium/low with its basis>
- **Recommended action**: <concrete correction or business decision;
  for AMBIGUITY, state the question that determines the correct behavior>

<For re-audits: resolved and not-verified antecedent tables with the shared
evidence requirements. Describe the changes and missing verification in
functional language; do not copy an old theoretical diagnosis.>

## What your tests protect
<One or two sentences: whether a suite was found, that it was read and not
run, and the gap that matters most — an enshrined finding first ("the test
suite asserts the duplicated charge as correct, so fixing it turns a test
red"), then a category with nothing asserted.>

<The invariant coverage table. Translate the header row; the category names
in the first column stay in English, in this order:>
| Category | Invariants | Asserted | Weak | Contradicted | Uncovered | Not verifiable |
|---|---|---|---|---|---|---|
| state | N | N | N | N | N | N |
<… one row each for transition, logical, temporal, repetition, concurrency,
atomicity, algebraic>

<Then, in everyday language, the findings the suite does not protect:
"No test would notice that a redelivered payment is counted twice." List
enshrined findings first, then undetected ones. Do not mention invariant ids,
techniques or matrix cells.>

## Scope and pending verification
<Scope actually reviewed; functional behavior that could not be verified;
material missing evidence; deliberate product limits relevant to a decision.
No twelve-check coverage table or theoretical limits discussion.>
```

Each confirmed finding gets exactly one such heading, with its recorded
severity and label. Test gaps never get a heading of their own: they
live in the tests section and never change the count line. Do not add a `**Check**` line, a mermaid block or a
twelve-row coverage table; G7 rejects them in this mode.

If there are no verified findings, say so, identify the behavior checked and
keep the pending-verification section. Never invent findings or a
recommendation merely to fill the template. Do not include a `full` appendix,
theoretical explanation or methodology recap unless the user changes the mode.

For example, describe a failed retry as: "A payment that fails on its first
delivery remains unapplied even when the same payment is retried after the
invoice is issued." The consequence is an unpaid invoice despite the retry;
it is not evidence by itself of external monetary loss or production frequency.
