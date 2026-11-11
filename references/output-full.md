# Full output

Retain the detailed systemic format, with functional impact as well as the
theoretical diagnosis. Translate headings and prose into the report's language;
honesty labels and severities remain the shared fixed keywords.

Render it from `findings.json`, `checks.json`, `model.json`, `tests.json`
and, on a re-audit, `reaudit.json`, never from memory. Gate G7 checks the result
against those records; see `references/run-contracts.md`.

```markdown
# Systemic analysis — <scope>

## Executive summary
<3-6 sentences: the scope reviewed (and, when they apply, that graphify
informed it or that the gates were checked manually), what was modeled and
the most serious finding, plus the
count line, whose keywords stay in English in every language:>
critical: N · high: N · medium: N · low: N
<For a re-audit, also:>
new: N · persisting: N · resolved: N · not verified: N

## Systems identified
| System | Objective | Elements | Operators |

## Conceptual machines
<Per machine in model.json: a mermaid stateDiagram-v2 (declared + built;
mark hole transitions) and, when it has <=8 declared states, the state x
operator matrix from checks.json.>

## Findings
<Ordered by severity. Each one:>
### [severity] [LABEL] <title, exactly as recorded in findings.json>
- **Check**: <which of the 12>
- **Evidence**: <relative file:line or document section + a short quote>
- **Systemic diagnosis**: <in GST vocabulary: which property is violated>
- **Condition** (RISK) or **Question** (AMBIGUITY): <as recorded; omit the
  line for an INCONSISTENCY>
- **Impact and confidence**: <functional consequence; demonstrated effect,
  conditions and impact not verified; confidence high/medium/low with its basis>
- **Recommendation**: <concrete action>

<For a re-audit, include the two tables defined in SKILL.md F7, even if
one is empty: Resolved since last report | previous finding | evidence of
the fix |, and Not verified | previous finding | last verified evidence |
what changed | what is needed |.>

<When findings.json has rejected candidates, include a compact table:
candidate + evidence that refuted it. Omit it when there are none.>

## Invariant coverage by tests
<State whether the suite is in scope, absent or out of scope, and that it was
read, not run — or, when execution was allowed, which tests were run and
what that confirmed. Then the category table; the header row is translated, the
category names and the order are fixed:>
| Category | Invariants | asserted | weak | contradicted | uncovered | not verifiable |
|---|---|---|---|---|---|---|
| state | N | N | N | N | N | N |
<… transition, logical, temporal, repetition, concurrency, atomicity, algebraic>

<For every machine with a matrix, one line with the counts the validator
computes from cells_tested, followed by which cells they are:>
M-1 cells tested: N/M

<A per-invariant table: invariant · level · the cited assertion or why
(searched for what, which technique was missing).>

<A findings-against-the-suite table: finding title · detected, undetected or
enshrined, with the test that enshrines or detects it.>

## Missing pieces
<Supported architectural recommendations; omit speculative recommendations.>

## Limits and not-verified
<A coverage table with all 12 checks, none silently skipped:>
| # | Check | Verdict | Evidence / why |

<One row per check 1-12, in this column order. The Verdict cell starts with
the fixed keyword from checks.json: findings (identify them), clean (what was
verified), or not verifiable (missing material). Never blur clean and not
verifiable. Then describe declared
and implicit limits, the claims in `model.json.claims_unverified` with what
is missing for each, and, when execution was allowed, what was executed and
what was left as reasoned.>
```

## Style

- Diagnose with the framework's vocabulary (closure, operator, limit, minimal
  expression) and connect the property to its functional impact.
- Prioritize: a few well-evidenced findings beat 30 trivial ones. If there
  are more than ~10, keep the minor ones brief: their heading plus one line
  each for evidence and action.
- Mermaid diagrams draw what is REAL (the built figure); when it differs from
  what is declared, draw both or mark the differences — that divergence is
  usually the most valuable finding.
- Close with the most important missing component when supported.
