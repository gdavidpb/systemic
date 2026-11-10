# One finding per root cause — grouping in F4 (4c)

Read this in F4, step 4c, whenever two or more candidates touch the same
machine, the same operator or the same field. It decides whether they are one
finding or several.

## The test: what would a single fix repair?

The dedup key is the underlying defect — what a single fix would repair — not
the check that surfaced it. A missing guard can appear as a completeness hole
(check 3), an illegal representable state (check 5) and a declared-vs-built
divergence at once. Keep it ONCE, under the check that explains it best, list
the other manifestations inside it, and record the others in `merged`.

Group only when correcting one shared point removes all the manifestations.
Similar recommendations, or the same repair pattern in independent
implementations, do not establish a shared root cause. When uncertain, try
the repairs in isolation: if fixing one leaves the other reproducible, keep
separate findings and explain their relationship.

## Missing guards on one machine

The most common case of the test above, and the one most often split by
mistake.

**When it applies.** Several operators write the same machine's state without
checking the current one, and the allowed transitions are declared in one
place (a README, a spec, an enum with documented rules).

**Why it is one finding.** The root cause is that the declared machine is
enforced nowhere. One transition function over the declared table removes
every hole at once, so this is the isolated-repair test applied to a machine:
the shared repair is the transition function. That is why it wins over
keeping each operator separate.

**How to record it.**

- Report ONE finding, under check 3.
- Name each operator and its worst consequence as a manifestation, and list
  the other checks that surfaced it among the manifestations.
- Rate it by the worst manifestation.

**What stays separate.** Keep a separate finding when a guard concerns:

- a different machine;
- a rule outside the transition table (an amount check, an ownership check);
- a defect that remains after the table exists — writing an undeclared state
  is closure, not a missing guard.

**Holes that need a missing operator.** A hole that needs an operator that
does not exist (a review step nothing performs) belongs to the finding about
that missing operator, recorded under that finding's own check (usually 4,
reachability), not under 3.

**The gate.** A second check-3 finding on the same machine needs
`separate_because`: the rule or defect that the transition table would not
fix **[gate]**.
