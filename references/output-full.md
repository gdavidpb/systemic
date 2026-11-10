# Full output

Retain the detailed systemic format, with functional impact as well as the
theoretical diagnosis. Translate headings and prose into the report's language;
honesty labels and severities remain the shared fixed keywords.

Render it from `findings.json`, `checks.json`, `model.json` and, on a
re-audit, `reaudit.json`, never from memory. Gate G6 checks the result
against those records; see `references/run-contracts.md`.

```markdown
# Systemic analysis — <scope>

## Executive summary
<3-6 sentences: what was modeled and the most serious finding, plus the
count line, whose keywords stay in English in every language:>
critical: N · high: N · medium: N · low: N
<For a re-audit, also:>
new: N · persisting: N · resolved: N · not verified: N

## Systems identified
| System | Objective | Elements | Operators |

## Conceptual machines
<Per machine in model.json: a mermaid stateDiagram-v2 (declared + built;
mark hole transitions) and, when it has <=8 states, the state x operator
matrix from checks.json.>

## Findings
<Ordered by severity. Each one:>
### [severity] [LABEL] <title, exactly as recorded in findings.json>
- **Check**: <which of the 12>
- **Evidence**: <relative file:line or document section + a short quote>
- **Systemic diagnosis**: <in GST vocabulary: which property is violated>
- **Impact and confidence**: <functional consequence; demonstrated effect,
  conditions and impact not verified; confidence high/medium/low with its basis>
- **Recommendation**: <concrete action>

<For a re-audit, include the resolved and not-verified antecedent tables
defined in SKILL.md, even if one is empty.>

<When findings.json has rejected candidates, include a compact table:
candidate + evidence that refuted it. Omit it when there are none.>

## Missing pieces
<Supported architectural recommendations; omit speculative recommendations.>

## Limits and not-verified
<A coverage table with all 12 checks, none silently skipped:>
| # | Check | Verdict | Evidence / why |

<One row per check 1-12, in this column order. The Verdict cell starts with
the fixed keyword from checks.json: findings (identify them), clean (what was
verified), or not verifiable (missing material). Never blur clean and not
verifiable. Then describe declared
and implicit limits.>
```
