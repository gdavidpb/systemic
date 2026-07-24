---
name: systemic
description: >-
  Systemic analysis of software based on General Systems Theory (GST): models a
  solution as systems (elements, operators, conceptual state machines) and
  verifies their consistency — closure, reachability, transition completeness,
  invariants, operator ambiguity, idempotency, symmetry, minimal expression and
  system limits — producing a local Markdown findings report with evidence,
  severity and recommendations. Use it whenever the user asks for a systemic
  analysis, wants to review the consistency of states or a state machine, find
  inconsistencies or contradictions in a design, flow or operation, audit a
  lifecycle (workflow, saga, state machine), apply systems thinking or GST/TGS,
  or asks "is my design consistent?" — even if they never say the word
  "systemic". Works on code, design documents, or both.
---

# /systemic — Systemic analysis of software (GST)

Applies General Systems Theory (GST) to software: every software solution is a
**system** — a set of components that relate to each other with a single
objective — and most of its serious bugs are violations of systemic
properties, not typos. This skill models the solution as systems and verifies
those properties.

Read `references/gst-framework.md` BEFORE Phase 1 to internalize the
vocabulary (elements, operators, closure, limits, minimal expression) and its
teaching examples — the report is written in that vocabulary.

**Language**: write the whole report — section headers, summaries, diagnoses,
recommendations — in the language the user asks for. If the user names a
language ("el reporte en inglés", "report in Portuguese"), that wins. If not,
use the language the user is writing in. The only exception: the honesty
labels (INCONSISTENCY / RISK / AMBIGUITY) and the severities (critical / high
/ medium / low) stay as fixed keywords in every language, so reports remain
comparable and greppable across projects.

**Delivery**: the report is a Markdown file on the user's disk. Never an
artifact, never HTML, never served from a localhost port. See Phase 3.

## Input and scope

The user may provide: a path (repo, module, files), a design document, or a
description. If the scope is a large repo with no focus, propose narrowing to
the subsystem with the most state (state machines, lifecycles) — that is where
systemic analysis pays off.

If `graphify-out/graph.json` exists in the project, read it BEFORE grepping
and use it to choose which modules to open: it maps files and their relations,
which beats searching a large repo blind. It never replaces reading the
sources — every finding still cites code you read yourself. State in the
report that you used it, so the reader knows how the scope was chosen. If it
does not exist, say nothing about it and locate the modules by search.

**Honesty rule (non-negotiable):** no finding without evidence you actually
read. Before asserting an inconsistency, read the cited code or document and
record `file:line` (or the document section). A finding without evidence is
not reported.

## Phase 1 — Model

Describe the solution as systems, Tangram-style:

1. **Identify the systems** in scope (a module, a layer, a business flow).
   For each: its **single objective** in one sentence.
2. **Inventory components** by category:
   - **Elements**: entities, models, records — the concrete things that get
     transformed (Order, Quote, Account…), with their minimal representation.
   - **Operators**: operations that interact with elements and produce or
     transform elements (business functions, endpoints, tools, jobs). For
     each operator: arity (which elements it acts on), result, and declared
     preconditions.
3. **Extract the conceptual machines** — the lifecycles:
   - **Explicit**: enums/`status` fields, state columns, constants.
   - **Implicit**: combinations of booleans and nullable fields that co-vary
     (`paid_at`, `deleted`, `locked_by`…). A tuple of flags where only some
     combinations are valid IS a state machine, even if nobody declared it.
   - For each machine: states, transitions, and **which operator executes
     each transition**.
4. **Record declared vs built**: what the docstrings/README/specs promise
   (the *silhouette*) versus what the code does (the *built figure*).
   Divergences feed Phase 2.

Intermediate result: a table of systems (system · objective · elements ·
operators) and one conceptual machine per lifecycle found.

## Phase 2 — Verify

Run the checks in `references/checks.md` (read it in this phase; it contains
the "how to detect" for each). Summary of the 12:

1. **Closure** — does every operation produce an element/state the system can
   represent? (the `1/2 = 0.5` problem in the integers).
2. **Operator ambiguity** — does any operator admit multiple interpretations
   depending on context or argument type? (the `A U B` problem).
3. **Transition completeness** — state × operator matrix: is each cell
   *defined*, *forbidden with a guard*, or a **hole**?
4. **Reachability** — unreachable states (nothing produces them), absorbing
   non-terminal states (no exit), dead transitions.
5. **Illegal states representable** — field combinations the business forbids
   but the model allows to be written.
6. **Invariants and partial failure** — which invariants exist, which
   operator maintains each, and what happens if that operator fails halfway
   (compensation).
7. **Idempotency and re-entry** — closure under repetition: does retrying the
   operator (webhook, queue retry) produce the same state, or duplicates?
8. **Concurrency** — two operators on the same element at once: do they
   commute, serialize (lock), or clobber each other (lost update)?
9. **Symmetry/duality** — operators without an inverse: open without close,
   lock without release, pause without resume. A resource that opens and
   never closes is a structural leak.
10. **Minimal expression** — derivable components duplicated as primitives (a
    total both stored AND computed): two sources of truth that drift.
11. **System limits** — requirements outside the representable set (evens +
    addition never produce 7). Signal: hacks, special cases and "wood
    cutting" that reveal missing pieces.
12. **Feedback loops** — retries + queues + timeouts + alerts feeding each
    other and amplifying (retry storms, compensation loops).

Do not force all 12 onto every scope: apply the ones the material lets you
verify honestly, and state which did not apply and why.

## Phase 3 — Report

**Where it goes**: write the report to `systemic-out/<scope-slug>.md` inside
the analyzed project (create the directory if needed; the slug is the scope in
kebab-case — `orders-module.md`, `rental-lifecycle.md`). If the user names a
path, use theirs. If the file already exists, read it before writing and tell
the user whether you replaced it or wrote a new one alongside.

Do not write into a target that is not the user's own working project — a
read-only path, a vendored dependency, `node_modules`, a fixture directory, or
anything outside the working directory. In those cases write to
`systemic-out/<scope-slug>.md` under the user's current working directory
instead, and say in chat that the report went there because the analyzed path
is not writable work of theirs.

All the evidence lives in that file: quotes, `file:line` references, mermaid
diagrams, matrices. Relative paths, so the report survives being committed and
read by someone else.

Do NOT publish it as an artifact, do NOT render it to HTML, and do NOT start a
server, preview or localhost port to display it — Markdown on disk is the
deliverable. In chat, reply with the file path, the executive summary and the
single most serious finding; the user reads the rest in the file.

ALWAYS use this exact structure. The headers below are shown in English
because this file is in English — **translate every one of them** into the
report's language per the Language rule above. Only the honesty labels and the
severities stay untranslated.

```markdown
# Systemic analysis — <scope>

## Executive summary
<3-6 sentences: what was modeled, findings per severity, the most serious one.>

## Systems identified
| System | Objective | Elements | Operators |

## Conceptual machines
<Per machine: a mermaid `stateDiagram-v2` (declared + built; mark hole
transitions) and, when it has ≤8 states, the state × operator matrix.>

## Findings
<Ordered by severity. Each one:>
### [SEVERITY] [LABEL] Short title
- **Check**: <which of the 12>
- **Evidence**: `file:line` (or document section) + a short quote
- **Systemic diagnosis**: <in GST vocabulary: which property is violated and why it matters>
- **Recommendation**: <concrete action>

<Then, when you seriously considered a candidate finding and rejected it, and
a reader might reasonably expect it reported — a declared terminal state that
"has no inverse", an absent feature that is a documented limit, a
two-statement in-memory sequence that is not a partial failure — list them in
a compact table: candidate + why it is not a finding. Naming what you refused
to report is what separates an audit from a fishing expedition. Omit the table
when nothing was seriously considered and rejected.>

## Missing pieces
<Architectural recommendations: components the system needs — where the team
is "cutting the wood" instead of making pieces. Only if the analysis revealed
them.>

## Limits and not-verified
<Declared vs implicit limits of the system, and which checks did not apply or
could not be verified with the available material.>
```

### Honesty labels (mandatory on every finding)

- **INCONSISTENCY** — a contradiction proven with evidence: the system does X
  and also not-X, or produces states it cannot represent.
- **RISK** — breaks under concrete, plausible conditions (retry, concurrency,
  partial failure); the condition must be written down.
- **AMBIGUITY** — underspecified: the material does not define the behavior
  and there are ≥2 reasonable interpretations. Do not guess: state the
  question the architect/product owner must answer.

### Severity

This rubric is authoritative. `references/checks.md` gives per-check severity
guidance for the typical case; when it disagrees with the rubric below, the
rubric wins — rate by the damage the finding actually causes, not by which
check surfaced it. An ambiguous operator that zeroes an invoice is `critical`
even though the check's usual ceiling is `high`.

- **critical** — corrupts data or money, or leaves the system in an
  unrepresentable state in production.
- **high** — incorrect behavior observable by users, or loss of a business
  invariant.
- **medium** — structural debt that does not fail today but forces hacks
  (limits, double source of truth, asymmetries).
- **low** — cosmetic or naming inconsistency with bounded impact.

## Style

- Diagnose with the framework's vocabulary (closure, operator, limit, minimal
  expression) — that is what distinguishes this analysis from a code review:
  do not report "a missing if"; report the violated systemic property, with
  the if as the recommendation.
- Prioritize: a few well-evidenced findings beat 30 trivial ones. If there
  are more than ~10, group the minor ones into a compact table.
- Mermaid diagrams draw what is REAL (the built figure); when it differs from
  what is declared, draw both or mark the differences — that divergence is
  usually the most valuable finding.
- Close with the single most important missing piece: which component would
  make several findings unnecessary at once.
