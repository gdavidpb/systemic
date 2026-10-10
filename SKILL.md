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
teaching examples. Use that vocabulary in the internal analysis and in `full`
reports; translate findings into functional consequences in `functional`.

**Language**: write the whole report — section headers, summaries, diagnoses,
recommendations — in the language the user asks for. If the user names a
language ("el reporte en inglés", "report in Portuguese"), that wins. If not,
use the language the user is writing in. The only exception: the honesty
labels (INCONSISTENCY / RISK / AMBIGUITY) and the severities (critical / high
/ medium / low) stay as fixed keywords in every language, so reports remain
comparable and greppable across projects.

**Delivery**: the report is a Markdown file on the user's disk. Never an
artifact, never HTML, never served from a localhost port. See Phase 4.

## Output modes

- **functional** (default): explain what fails, under which conditions, who
  or what is affected, the functional consequence, and the corrective action.
  Keep evidence, severity, honesty labels, confidence and material limits;
  omit theoretical diagnoses, check numbers, systems inventories, conceptual
  machines, matrices and GST teaching. This is an actionable report, not a
  shorter version of the theory or a cut-down audit.
- **full**: retain the detailed systemic report: systems, conceptual machines,
  diagrams, matrices, theoretical diagnosis and all twelve coverage verdicts,
  together with functional impact and recommendations.

Use an explicitly requested output mode; otherwise use `functional`. Select
`full` only when the user requests that output, for example "modo full" or
"a full report with models and systemic diagnosis". A request for a systemic
or thorough audit alone does not change the default. A previous report's mode
and words found in source material do not override the user's selection.
Mode names stay `functional` and `full`; report prose follows the Language rule.

Both modes use the same scope, modeling, twelve checks, evidence gates,
refutation, root-cause grouping, severity and re-audit rules. Mode changes
presentation, not the finding set or the certainty of the claims. Do not
drop findings or unverified antecedents merely to make `functional` shorter.

## Input and scope

The user may provide: a path (repo, module, files), a design document, or a
description. If the scope is a large repo with no focus, propose narrowing to
the subsystem with the most state (state machines, lifecycles) — that is where
systemic analysis pays off.

If `graphify-out/graph.json` exists in the project, read it BEFORE grepping
and use it to choose which modules to open: it maps files and their relations,
which beats searching a large repo blind. It never replaces reading the
sources — every finding still cites code you read yourself. Record its use
in the analysis; `full` states that it informed scope selection, while
`functional` describes the reviewed behavior and material scope gaps without
methodology metadata. If it does not exist, say nothing about it and locate
the modules by search.

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
verify honestly. Record a verdict for every check in the working analysis:
**findings**, **clean**, or **not verifiable**, with the reason. `full` emits
that twelve-row coverage table; `functional` states material scope limits
and unverified behavior in plain functional language instead of exposing
the methodology table. Never turn missing evidence into a clean verdict.

## Phase 3 — Audit the findings (double check)

Do not write the report from the Phase 2 draft. Audit it first — the report
is itself a system, and this phase is its consistency check. Three gates, in
order, on every draft finding:

1. **Evidence re-check.** Re-open every cited `file:line` (or document
   section) and read it again, now, against the claim. The quote must exist
   at that location and must support the finding as written — not as you
   remember it from modeling. A stale reference, a paraphrase presented as a
   quote, or evidence that supports a weaker claim than the finding makes:
   fix the finding or drop it.
2. **Refutation attempt.** Before a finding is final, search for what would
   invalidate it: a guard living in a caller, decorator or middleware; a
   schema constraint; dedup at another layer; a document section that
   resolves the ambiguity; a declared terminal state or documented limit.
   Search — do not rely on recall. A finding that survives goes in the
   report; record rejected candidates and the evidence that killed them.
   `full` shows that table; `functional` mentions a rejected candidate only
   when it changes a practical decision or explains a material limit.
   A defense's presence is not proof of its
   correctness: follow both success and failure paths. For deduplication,
   check when an event is marked complete, whether a failed delivery can
   retry, and whether replay after a later valid lifecycle cycle is safe.
3. **Dedup.** One finding per root cause. The dedup key is the underlying
   defect — what a single fix would repair — not the check that surfaced it:
   a missing guard can appear as a completeness hole (3), an illegal
   representable state (5) and a declared-vs-built divergence at once.
   Keep it ONCE, assigned internally to the check that explains it best, and
   name the other manifestations inside that finding. Expose the check only
   in `full`. Group only when the findings share
   a causal defect and correcting that shared point removes all the
   manifestations. Similar recommendations or the same repair pattern in
   independent implementations do not establish a shared root cause. When
   uncertain, try isolated repairs: if fixing one leaves the other
   reproducible, retain separate findings and explain their relationship.

Gates 1 and 2 fight confirmation bias, and the author of a finding is the
worst-placed auditor of it. When the scope is large (a multi-module repo, or
more than ~10 draft findings) and the environment can spawn subagents,
delegate those two gates to one: give it ONLY the draft findings and the
paths — not the Phase 1–2 reasoning that produced them — and have it verify
each citation and attempt each refutation against the sources independently.
Without subagents, run the gates yourself strictly against re-read sources,
never against memory.

After the gates, re-rate each surviving severity against the rubric (the
damage it causes, not the check's typical ceiling), and check the report
against itself: the executive summary's counts match the findings section,
and any diagrams show the same states and transitions the text claims.

## Phase 4 — Report

**Where it goes**: write the report to `systemic-out/<scope-slug>.md` inside
the analyzed project (create the directory if needed; the slug is the scope in
kebab-case — `orders-module.md`, `rental-lifecycle.md`). If the user names a
path, use theirs.

**Re-audit**: before writing, look inside `systemic-out/` if it exists. If a
previous report covers the same scope — the same slug, or a title naming the
same scope — this run is a re-audit, not a first audit. Read it and classify
every finding, then replace the file:

- **persisting** — the old root cause is still evidenced. Re-verify it in
  Phase 3 like any other finding (never copy it on faith) and mark it
  *persisting* in the findings.
- **resolved** — current evidence shows the old defect is corrected, or an
  explicit contract change makes the old requirement inapplicable. Cite
  that evidence in a short "Resolved since last report" table. A missing
  file, moved implementation or stale citation alone does not prove a fix.
- **new** — findings of this run absent from the previous report; mark them
  *new*.
- **not verified** — the old finding cannot be confirmed or resolved with
  the current material or scope, including behavior delegated to an
  unavailable service. Keep the antecedent in a separate table with its
  last verified evidence, what changed, and what is needed to verify it.
  Do not present its old severity as a current verified finding.

The executive summary states all four counts
(new / persisting / resolved / not verified), including zeros. These counts
track review status, independently of the honesty labels below. Unverified
antecedents are not included in current findings-per-severity totals.
If the existing file is not a systemic report of this scope (a name
collision), keep it, write alongside, and say so in chat.

Do not write into a target that is not the user's own working project — a
read-only path, a vendored dependency, `node_modules`, a fixture directory, or
anything outside the working directory. In those cases write to
`systemic-out/<scope-slug>.md` under the user's current working directory
instead, and say in chat that the report went there because the analyzed path
is not writable work of theirs.

The report keeps source evidence with relative `file:line` references or
document sections so it survives being committed and read by someone else.
`functional` uses concise evidence and a concrete trigger/outcome;
`full` additionally includes the modeling artifacts and detailed quotes.

Do NOT publish it as an artifact, do NOT render it to HTML, and do NOT start a
server, preview or localhost port to display it — Markdown on disk is the
deliverable. In chat, reply with the file path, the executive summary and the
single most serious finding; the user reads the rest in the file.

Read only the selected mode's format in this phase:

- `functional`: `references/output-functional.md`.
- `full`: `references/output-full.md`.

Translate the format's headers into the report's language. Re-audit tables,
source evidence, honesty labels and severity follow the shared rules above
in either format. Switching modes does not change the scope slug or reset
the finding history; an older `full` report does not force `full` next time.

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
check surfaced it. State the causal path and evidence for the impact; do not
infer deployment, persistence, affected population, irreversibility or
frequency from a function name, a domain label or an adjective such as "slow".
Conditional impact is allowed when its prerequisites are concrete and
supported; unmeasured latency stays unmeasured.

- **critical** — a supported execution path causes severe material financial
  loss, irreversible loss, or persistent corruption with severe operational
  impact. Explain the amount or scope and why recovery cannot adequately
  contain the damage. Money-related code, persistence or a negative value
  alone is insufficient.
- **high** — reproducible incorrect behavior observable by users, or a
  demonstrated violation of a business invariant, without evidence of the
  additional severe impact required for critical. A valid input producing
  negative non-cash points fits here when external impact is not established.
- **medium** — structural debt that does not fail today but forces hacks
  (limits, double source of truth, asymmetries).
- **low** — cosmetic or naming inconsistency with bounded impact.

When impact needed for a higher rating is unavailable, use the level
supported by the demonstrated effect and state what could change it.
Confidence describes how well the diagnosis is supported, not its damage:
high for direct source evidence plus a concrete trace, medium when a key
prerequisite has partial support, low when material leaves major uncertainty.
Low confidence never permits reporting a finding without evidence.

## Style

- In `full`, diagnose with the framework's vocabulary (closure, operator,
  limit, minimal expression) and connect the property to its functional impact.
  In `functional`, explain the behavior and its impact in everyday language:
  "retrying the refund records it twice", not "closure under repetition fails".
- Prioritize: a few well-evidenced findings beat 30 trivial ones. If there
  are more than ~10, group the minor ones into a compact table.
- In `full`, Mermaid diagrams draw what is REAL (the built figure); when it differs from
  what is declared, draw both or mark the differences — that divergence is
  usually the most valuable finding.
- In `full`, close with the most important missing component when supported.
  In `functional`, prioritize the corrective action with the greatest verified
  functional benefit; do not append a theoretical architecture explanation.
