# Full output

Retain the detailed systemic format, with functional impact as well as the
theoretical diagnosis. Translate headings and prose into the report's language;
honesty labels and severities remain the shared fixed keywords.

```markdown
# Systemic analysis — <scope>

## Executive summary
<3-6 sentences: what was modeled, findings per severity, the most serious one.
For a re-audit, also state new / persisting / resolved / not verified counts.>

## Systems identified
| System | Objective | Elements | Operators |

## Conceptual machines
<Per machine: a mermaid stateDiagram-v2 (declared + built; mark hole
transitions) and, when it has <=8 states, the state x operator matrix.>

## Findings
<Ordered by severity. Each one:>
### [SEVERITY] [LABEL] Short title
- **Check**: <which of the 12>
- **Evidence**: <relative file:line or document section + a short quote>
- **Systemic diagnosis**: <in GST vocabulary: which property is violated>
- **Impact and confidence**: <functional consequence; demonstrated effect,
  conditions and impact not verified; confidence high/medium/low with its basis>
- **Recommendation**: <concrete action>

<For a re-audit, include the resolved and not-verified antecedent tables
defined in SKILL.md, even if one is empty.>

<When seriously considered candidates were rejected, include a compact table:
candidate + evidence that refuted it. Omit when none were seriously considered.>

## Missing pieces
<Supported architectural recommendations; omit speculative recommendations.>

## Limits and not-verified
<A coverage table with all 12 checks, none silently skipped:>
| # | Check | Verdict | Evidence / why |

<Verdict: findings (identify them), clean (what was verified), or not verifiable
(missing material). Never blur clean and not verifiable. Then describe declared
and implicit limits.>
```
