---
name: systemic
description: >-
  Systemic analysis of software based on General Systems Theory (GST): models a
  solution as systems (elements, operators, conceptual state machines) and
  verifies their consistency — closure, reachability, transition completeness,
  invariants, operator ambiguity, idempotency, symmetry, minimal expression and
  system limits — and audits how well the test suite protects the machine's
  invariants, with coverage per invariant category (state, transition,
  logical, temporal, repetition, concurrency, atomicity, algebraic). It
  produces a local Markdown findings report with evidence, severity and
  recommendations, backed by a validated run workspace. Use it
  whenever the user asks for a systemic analysis, wants to review the
  consistency of states or a state machine, find inconsistencies or
  contradictions in a design, flow or operation, audit a lifecycle (workflow,
  saga, state machine), apply systems thinking or GST/TGS, asks "is my
  design consistent?", or asks whether their tests really cover the
  invariants of a lifecycle — even if they never say the word "systemic".
  Works on code, design documents, or both.
---

# /systemic — Systemic analysis of software (GST)

Applies General Systems Theory (GST) to software: every software solution is a
**system** — a set of components that relate to each other with a single
objective — and most of its serious bugs are violations of systemic
properties, not typos. This skill models the solution as systems and verifies
those properties.

The analysis runs as nine phases, F0–F8. Each phase reads the files the
previous one wrote, writes its own, and passes a deterministic gate before
the next phase starts. The files are specified in
`references/run-contracts.md`. The gates are checked by
`scripts/systemic_check.py`. This file defines what each phase does; the
contracts file defines the exact shape of what it writes.

## Shared rules

**Vocabulary.** Read `references/gst-framework.md` before F2 to internalize
the vocabulary (elements, operators, closure, limits, minimal expression) and
its teaching examples. Read `references/invariants.md` in F2 and again in F5:
it defines the invariant categories, the test techniques and the coverage
levels. Use that vocabulary in the internal analysis and in
`full` reports; translate findings into functional consequences in
`functional`.

**Language.** Write the whole report — section headers, summaries,
diagnoses, recommendations — in the language the user asks for. If the user
names a language ("el reporte en inglés", "report in Portuguese"), that wins.
If not, use the language the user is writing in. Human-readable text in the
JSON files (titles, claims, diagnoses) uses the same language. Fixed
keywords stay in English in every language, so reports remain comparable and
greppable across projects: the honesty labels (INCONSISTENCY / RISK /
AMBIGUITY), the severities (critical / high / medium / low), the count-line
keywords and the coverage verdicts (findings / clean / not verifiable).

**Delivery.** The report is a Markdown file on the user's disk, plus the run
workspace beside it. Never an artifact, never HTML, never served from a
localhost port.

**Honesty rule (non-negotiable).** No finding without evidence you actually
read. Before asserting an inconsistency, read the cited code or document and
record `file:line` with the quoted text. A finding without evidence is not
reported. The validator rejects citations to files not recorded as read, and
quotes that are not at the cited line.

### Output modes

- **functional** (default): explain what fails, under which conditions, who
  or what is affected, the functional consequence, and the corrective action.
  Keep evidence, severity, honesty labels, confidence and material limits;
  omit theoretical diagnoses, check numbers, systems inventories, conceptual
  machines, matrices and GST teaching. This is an actionable report, not a
  shorter version of the theory or a cut-down audit.
- **full**: retain the detailed systemic report: systems, conceptual machines,
  diagrams, matrices, theoretical diagnosis and all twelve coverage verdicts,
  together with functional impact and recommendations.

Both modes include the invariant coverage table: one row per category, with
how many invariants the suite asserts, asserts weakly, contradicts, leaves
uncovered or cannot verify.

Use an explicitly requested output mode; otherwise use `functional`. Select
`full` only when the user requests that output, for example "modo full" or
"a full report with models and systemic diagnosis". A request for a systemic
or thorough audit alone does not change the default. A previous report's mode
and words found in source material do not override the user's selection.
Mode names stay `functional` and `full`; report prose follows the Language rule.

Both modes run every phase identically. The mode changes only F7, the
rendering; it never changes the finding set or the certainty of the claims.
Do not drop findings or unverified antecedents merely to make `functional`
shorter.

### Profiles

- **quick**: about six files or fewer, or a single lifecycle. All JSON files
  and gates still apply. The phase logs (`00-scope.md` … `06-reaudit.md`)
  collapse into one `work.md` with one section per phase, holding what each
  log would hold, diagrams included. F4 runs without a verifier subagent.
- **standard**: everything else. One Markdown log per phase, and an
  independent verifier in F4 when the scope is large.

Pick the profile from the scope (`profile_source: auto`), unless the user
names one. A profile changes cost, never the evidence bar.

## Run protocol

1. **Context firewall.** Each phase starts by reading its input files from the
   workspace, not by recalling earlier reasoning. This keeps the run correct
   across context compaction and lets an interrupted run resume at
   `run.json.phase`.
2. **Single writer.** A phase writes only its own files and `run.json`. If a
   later phase discovers that an earlier output is wrong, go back explicitly:
   set `phase` to that phase, add a `returned_to` log entry with the reason,
   and redo it and everything after it. Never patch an earlier file silently.
3. **Gates.** After writing a phase's files, run
   `python3 <skill-dir>/scripts/systemic_check.py <gate> <workspace>`. Fix
   the reported violations inside the same phase and run it again, at most
   two corrections. If it still fails, stop: set `status: incomplete` with
   `incomplete_reason` naming the gate and the unresolved violations, write
   the report with that reason in its first section, and go to F8. Log every
   gate result in `run.json.log`.
4. **No Python.** If `python3` is not available, apply each gate as a
   checklist against `references/run-contracts.md`, set
   `validation: "manual"`, and state in the report's scope section that the
   gates were checked manually.
5. **Terminal states.** A run ends `complete` or `incomplete`. `needs_scope`
   is a pause: ask the user and continue F0 with the answer. Never stop in
   the middle of a phase.

## F0 — Scope

Fix what is analyzed, how, and where it is delivered, before reading code.

- **Inputs**: the user's request; the paths or document named;
  `graphify-out/graph.json` if it exists; the contents of `systemic-out/`.
- **Work**:
  1. If the scope is a large repo with no focus, propose narrowing to the
     subsystem with the most state (state machines, lifecycles), set
     `status: needs_scope` with a `scope_proposal`, and ask. That is where
     systemic analysis pays off.
  2. If `graphify-out/graph.json` exists, read it BEFORE searching and use it
     to choose which modules to open: it maps files and their relations,
     which beats searching a large repo blind. It never replaces reading the
     sources. Note in `00-scope.md` that it informed the scope; `full` says so
     in its report, `functional` does not mention it. If it does not exist,
     say nothing about it and locate the modules by search.
  3. Resolve mode, language and profile with their sources, and the slug
     (scope in kebab-case: `orders-module`, `rental-lifecycle`).
  4. Resolve `report_path`: `systemic-out/<slug>.md` inside the analyzed
     project, or the user's path if they name one. Do not write into a target
     that is not the user's own working project — a read-only path, a
     vendored dependency, `node_modules`, a fixture directory, or anything
     outside the working directory. In those cases use
     `systemic-out/<slug>.md` under the user's current working directory and
     say in chat why. The workspace is the report path without `.md`.
  5. **Test discovery.** Look for the tests of the scope: `tests/`, `test/`,
     `__tests__/`, `spec/`, and files named `test_*`, `*_test.*`, `*.test.*`,
     `*.spec.*`, plus the test directories the build configuration declares.
     Add the ones that exercise the scope to `targets`. If none exist, say in
     `00-scope.md` where you looked; F5 then records the suite as absent.
     If the user excludes the tests, F5 records them as out of scope.
  6. **Re-audit detection.** If a previous report covers the same scope (the
     same slug, or a title naming the same scope), archive it as the
     contracts file describes (`prior/report.md`, plus `prior/findings.json`
     when the previous workspace has one) and record `prior_report`. If an
     existing file at that path is not a systemic report of this scope (a
     name collision), keep it, choose a different slug, write alongside, and
     say so in chat.
- **Outputs**: `run.json`, `00-scope.md`.
- **Invariants**: the mode is `full` only if the user asked for it. A previous
  report does not set the mode.
- **Gate G0.**

## F1 — Silhouette

Read the sources and record what the system promises.

- **Inputs**: `run.json`.
- **Work**: read every target. Record each file read with its hash and line
  count, and whether it was read in full or in which ranges. Record test
  files with `role: test`; their assertions are audited in F5 and are not
  declared claims. Extract the
  declared claims `D-n` — what README, docstrings, specs, comments and
  declared constants promise — each with its location. Exclude a target only
  with a reason.
- **Outputs**: `sources.json`, `01-sources.md` (what was read, what was left
  out and why).
- **Invariants**: only files recorded here can be cited later. A partially
  read file cannot support a claim about what was not read.
- **Gate G1.**

## F2 — Model

Describe the built figure, Tangram-style.

- **Inputs**: `sources.json`, `references/gst-framework.md`.
- **Work**:
  1. **Identify the systems** in scope (a module, a layer, a business flow).
     For each, its **single objective** in one sentence.
  2. **Inventory components** by category:
     - **Elements**: entities, models, records — the concrete things that get
       transformed (Order, Quote, Account…), with their minimal representation.
     - **Operators**: operations that interact with elements and produce or
       transform elements (business functions, endpoints, tools, jobs). For
       each, its arity (which elements it acts on), result, and declared
       preconditions.
  3. **Extract the conceptual machines** — the lifecycles:
     - **Explicit**: enums/`status` fields, state columns, constants.
     - **Implicit**: combinations of booleans and nullable fields that co-vary
       (`paid_at`, `deleted`, `locked_by`…). A tuple of flags where only some
       combinations are valid IS a state machine, even if nobody declared it.
     - For each machine: declared states, built states, transitions, and
       **which operator executes each transition**.
  4. **Declared vs built**: link every claim from F1 either to
     `claims_satisfied` or to a divergence describing how the code departs
     from it. Divergences feed F3.
  5. **Invariant catalog**: list the invariants `I-n` the system must keep,
     each with one of the eight categories of `references/invariants.md`:
     declared ones linked to their claims, inferred ones derived from the
     model (state sets, guards, terminal states, re-invokable entry points,
     multi-write operators, dual operators). Every machine has at least one.
     Catalog an invariant even when the code violates it: it is what the
     tests should defend. Leave a category empty when nothing in scope
     supports it.
- **Outputs**: `model.json`; `02-model.md` with the systems table, one
  `stateDiagram-v2` per machine drawing what is REAL, marking where it
  differs from what is declared, and the invariant catalog.
- **Gate G2.**

## F3 — Verify

Run the twelve checks and produce candidates, not findings.

- **Inputs**: `model.json`, `sources.json`, `references/checks.md` (read it
  in this phase; it contains the "how to detect" for each check).
- **The twelve checks**:
  1. **Closure**: does every operation produce an element/state the system
     can represent? (the `1/2 = 0.5` problem in the integers).
  2. **Operator ambiguity**: does any operator admit multiple interpretations
     depending on context or argument type? (the `A U B` problem).
  3. **Transition completeness**: state × operator matrix: is each cell
     *defined*, *forbidden with a guard*, or a **hole**?
  4. **Reachability**: unreachable states (nothing produces them), absorbing
     non-terminal states (no exit), dead transitions.
  5. **Illegal states representable**: field combinations the business
     forbids but the model allows to be written.
  6. **Invariants and partial failure**: which invariants exist, which
     operator maintains each, and what happens if that operator fails halfway
     (compensation).
  7. **Idempotency and re-entry**: closure under repetition: does retrying
     the operator (webhook, queue retry) produce the same state, or
     duplicates?
  8. **Concurrency**: two operators on the same element at once: do they
     commute, serialize (lock), or clobber each other (lost update)?
  9. **Symmetry/duality**: operators without an inverse: open without close,
     lock without release, pause without resume. A resource that opens and
     never closes is a structural leak.
  10. **Minimal expression**: derivable components duplicated as primitives
      (a total both stored AND computed): two sources of truth that drift.
  11. **System limits**: requirements outside the representable set (evens +
      addition never produce 7). Signal: hacks, special cases and "wood
      cutting" that reveal missing pieces.
  12. **Feedback loops**: retries + queues + timeouts + alerts feeding each
      other and amplifying (retry storms, compensation loops).
- **Work**: record a verdict for every check — **findings**, **clean** (say
  what was verified, with evidence) or **not verifiable** (say what was
  missing). Apply only what the material lets you verify honestly; never turn
  missing evidence into a clean verdict. Build the state × operator matrix
  for every machine with ≤ 8 declared states (built states when nothing is
declared); an undeclared state the code writes adds a row, it does not lift
the requirement. Write each suspected defect as a
  candidate `C-n` with quoted evidence, the condition for a RISK and the
  question for an AMBIGUITY. A candidate that breaks a catalogued invariant
  lists its `I-n` in `refs`.
- **Outputs**: `checks.json`, `03-checks.md` (the reasoning per check).
- **Gate G3.**

## F4 — Audit the findings

Do not report the F3 candidates as they are. Audit them first: the report is
itself a system, and this phase is its consistency check.

- **Inputs**: only `checks.json` (the candidates) and `sources.json`.
- **Work**, in order, on every candidate:
  - **4a Evidence re-check.** Re-open every cited `file:line` and read it
    again, now, against the claim. The quote must exist at that location and
    must support the candidate as written, not as you remember it from
    modeling. A stale reference, a paraphrase presented as a quote, or
    evidence that supports a weaker claim: fix it or reject it.
  - **4b Refutation attempt.** Search for what would invalidate it: a guard
    living in a caller, decorator or middleware; a schema constraint; dedup
    at another layer; a document section that resolves the ambiguity; a
    declared terminal state or documented limit. Search — do not rely on
    recall. A defense's presence is not proof of its correctness: follow both
    success and failure paths. For deduplication, check when an event is
    marked complete, whether a failed delivery can retry, and whether replay
    after a later valid lifecycle cycle is safe. A refuted candidate goes to
    `rejected` with the evidence that killed it.
  - **4c Dedup.** One finding per root cause. The dedup key is the
    underlying defect — what a single fix would repair — not the check that
    surfaced it: a missing guard can appear as a completeness hole (3), an
    illegal representable state (5) and a declared-vs-built divergence at
    once. Keep it ONCE, under the check that explains it best, list the other
    manifestations inside it, and record the others in `merged`. Group only
    when correcting one shared point removes all the manifestations. Similar
    recommendations or the same repair pattern in independent
    implementations do not establish a shared root cause. When uncertain, try
    isolated repairs: if fixing one leaves the other reproducible, keep
    separate findings and explain their relationship.
  - **4d Severity and confidence.** Rate each surviving finding against the
    rubric below (the damage it causes, not the check's typical ceiling) and
    give it a fingerprint derived from its root cause.
- **Independent verifier.** 4a and 4b fight confirmation bias, and the author
  of a finding is the worst-placed auditor of it. In profile `standard`, when
  the scope is large (a multi-module repo, or more than ~10 candidates) and
  the environment can spawn subagents, delegate 4a and 4b. Give the subagent
  ONLY `checks.json`, `sources.json`, the source paths and the instructions
  of 4a–4b, not the F1–F3 reasoning. It returns, per `C-n`, confirmed or
  rejected with the evidence it read. Otherwise run the gates yourself,
  strictly against re-read sources, never against memory.
- **Outputs**: `findings.json`; `04-audit.md` with the log of every gate.
- **Gate G4.**

## F5 — Test audit

Ask of the suite what F3 asked of the code: which invariants does it defend?
A test protects an invariant only if one of its assertions would fail when
the invariant is violated. Running code is not asserting it.

- **Inputs**: `model.json` (the invariant catalog), `checks.json` (the
  matrices), `findings.json`, `sources.json`, `references/invariants.md`.
- **Work**:
  1. **Suite status.** `in_scope` when F1 recorded test files; `absent` when
     F0 searched and found none (say where); `out_of_scope` when tests exist
     but were excluded (say why). With `absent`, every invariant is
     `uncovered` and every finding `undetected`; with `out_of_scope`, every
     invariant is `not_verifiable`.
  2. **Inventory the tests** `X-n`: name, the operators each one drives, and
     its technique, judged from the body, not the name.
  3. **Coverage per invariant.** Re-open the test files and, for each
     invariant, look for the assertion that would fail if it were violated.
     Cite that assertion. Apply the technique fit: a repetition, temporal,
     concurrency, atomicity or algebraic invariant asserted only by a test
     that cannot reach it is `weak`. A test that asserts the opposite is
     `contradicted`, naming the finding it enshrines. Rule out the traps in
     `references/invariants.md` before calling anything `asserted`.
  4. **Refute every `uncovered`.** Search helpers, fixtures,
     parametrizations, base classes and shared test utilities before
     concluding that nothing covers it, and write down what you searched.
  5. **Matrix cells.** For every matrix in `checks.json`, list the `defined`
     and `guarded` cells some test drives (a guarded cell needs a test that
     expects the refusal).
  6. **Findings against the suite.** Classify every confirmed finding as
     `detected`, `undetected` or `enshrined`.
  7. **Counts.** Leave `by_category` to the validator: run G5, copy the
     expected value it reports, run it again.
- **Never run the suite.** The audit reads assertions. A green suite proves
  that its assertions hold, not that they assert the invariants.
- **Outputs**: `tests.json`, `05-tests.md` (the reasoning per invariant).
- **Invariants**: coverage gaps are not findings. They never add a finding,
  change a severity or alter the count line; the report shows them in their
  own section.
- **Gate G5.**

## F6 — Reconcile with the previous report (re-audit only)

Skip this phase when `run.json.prior_report` is null.

- **Inputs**: `findings.json`; `prior/findings.json` (format `json`) or
  `prior/report.md` (format `md-legacy`).
- **Work**: classify every previous finding:
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
  - Every current finding without a predecessor is **new**.
  With `json`, match by fingerprint first and confirm by root cause. With
  `md-legacy`, match each previous heading by its cited evidence and root
  cause.
- **Outputs**: `reaudit.json`, `06-reaudit.md`.
- **Invariants**: these counts track review status, independently of the
  honesty labels. Unverified antecedents are not included in current
  findings-per-severity totals. Switching modes does not reset the history;
  an older `full` report does not force `full` next time.
- **Gate G6.**

## F7 — Report

Render the selected mode from the records, not from memory.

- **Inputs**: `run.json`, `findings.json`, `checks.json`, `tests.json`,
  `model.json`, `reaudit.json` if present. Read only the selected mode's
  format: `references/output-functional.md` or `references/output-full.md`.
- **Work**: write `report_path`, replacing a previous report of this scope.
  Translate the format's headers into the report's language. Each confirmed
  finding becomes one `### [severity] [LABEL] <title>` heading with its
  recorded title. The summary carries the fixed-keyword count line. On a
  re-audit it also carries the re-audit count line, and the report adds two
  tables, present even when empty: **Resolved since last report** (previous
  finding · evidence of the fix) and **Not verified** (previous finding ·
  last verified evidence · what changed · what is needed to verify it). Both
  modes carry the invariant coverage table from `tests.json.by_category` and
  say which findings the suite leaves undetected or enshrines; `full` adds
  the per-invariant detail and the cells tested of each matrix. The
  report's scope statement says what was reviewed and any material limit;
  it also notes manual gate checks (`validation: manual`) and, in `full`
  only, that graphify informed the scope. Evidence uses relative `file:line` references or document
  sections, so the report survives being committed and read by someone else.
- **Invariants**: the report adds no finding, severity or citation that is not
  in the records, and drops none that is.
- **Gate G7.**

## F8 — Close

- Set `phase: F8` and `status: complete` (or `incomplete` with its reason),
  then run `systemic_check.py all <workspace>`. If it fails, fix the
  reported phase as the run protocol says.
- In chat, reply with the report path, the executive summary and the single
  most serious finding, plus the most serious test gap when there is one (an
  enshrined finding first, then an important category with nothing
  asserted); the user reads the rest in the file. For an
  incomplete run, lead with what is missing and how to unblock it. Do not
  publish the report as an artifact, render it to HTML, or start a server,
  preview or localhost port to display it.

## Honesty labels (mandatory on every finding)

- **INCONSISTENCY** — a contradiction proven with evidence: the system does X
  and also not-X, or produces states it cannot represent.
- **RISK** — breaks under concrete, plausible conditions (retry, concurrency,
  partial failure); the condition must be written down.
- **AMBIGUITY** — underspecified: the material does not define the behavior
  and there are ≥2 reasonable interpretations. Do not guess: state the
  question the architect/product owner must answer.

## Severity

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
  limit, minimal expression) and connect the property to its functional
  impact. In `functional`, explain the behavior and its impact in everyday
  language: "retrying the refund records it twice", not "closure under
  repetition fails".
- Prioritize: a few well-evidenced findings beat 30 trivial ones. If there
  are more than ~10, keep the minor ones brief: their heading plus one line
  each for evidence and action.
- In `full`, Mermaid diagrams draw what is REAL (the built figure); when it
  differs from what is declared, draw both or mark the differences — that
  divergence is usually the most valuable finding.
- In `full`, close with the most important missing component when supported.
  In `functional`, prioritize the corrective action with the greatest verified
  functional benefit; do not append a theoretical architecture explanation.
