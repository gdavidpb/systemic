# systemic

*[Léelo en español](README.es.md)*

**A Claude Code skill that audits software the way General Systems Theory
audits a system — and reports the properties it violates, not the lines it
got wrong.**

Most serious bugs are not typos. They are violations of systemic properties:
an operation that produces a state the system cannot represent, an operator
with no inverse, a value that is both stored and derived, a lifecycle whose
declared rules the code contradicts. `systemic` models your solution as a
system — elements, operators, conceptual state machines — and verifies twelve
consistency properties against it.

It works on code, on design documents, or on both.

```
/systemic analyze the order lifecycle in src/orders
```

---

## The idea

A system is *a set of components that relate to each other with a single
objective*. Not just the pieces — the pieces **and their capacity to join**.
Two categories:

- **Elements** — the concrete: your models, entities, records.
- **Operators** — the abstract that relates them: your use cases, endpoints,
  jobs, handlers.

A system is **consistent** when it is free of contradictions, and the star
test is **closure**: every operation on the system's elements must produce an
element of the system. The integers are not closed under division — `1/2 =
0.5`, and `0.5` does not exist there. Two legitimate elements, one legitimate
operator, and a result the system has no way to represent.

That failure has an exact analogue in software, and `systemic` is built to
find it:

```python
STATUS = {"draft", "pending_payment", "paid", "shipped", "delivered", ...}

def refund(order):
    order.status = "refund_pending"   # ← not in STATUS. 1/2 = 0.5.
```

The order is now outside every operation the system defines. Not terminal, so
nothing archives it. Not declared, so nothing reads it. A linter sees a string
assignment. `systemic` sees a closure violation and says so.

## Install

The folder name must match the skill name, so clone it as `systemic`:

```bash
git clone https://github.com/gdavidpb/systemic ~/.claude/skills/systemic
```

That's it — Claude Code picks it up from `~/.claude/skills/`. For a
project-scoped install, clone into `.claude/skills/systemic` inside the repo
instead.

## Use

Ask for it by name, or just describe the problem — the skill triggers on the
intent, not the keyword:

```
/systemic audit the subscription lifecycle in billing/
```
```
Is this design consistent? [paste or point at a design doc]
```
```
Find contradictions between what the README promises and what the code does.
```
```
Review my state machine — I think there are transitions nobody handles.
```

Point it at a path, a design document, or both. For a large repo with no
focus, it will propose narrowing to the subsystem with the most state — that
is where the analysis pays off.

## What it checks

Twelve properties. Four come straight from the systems framework; the rest
apply the same principle — consistency — to software that has queues, retries
and concurrency.

| # | Check | The question it asks |
|---|---|---|
| 1 | **Closure** | Does every operation produce a state the system can represent? |
| 2 | **Operator ambiguity** | Does any operation admit two reasonable interpretations? |
| 3 | **Transition completeness** | For every (state, operator) pair: defined, forbidden, or a **hole**? |
| 4 | **Reachability** | States nothing produces; states nothing exits; dead transitions. |
| 5 | **Illegal states representable** | Can the model persist a combination the business forbids? |
| 6 | **Invariants & partial failure** | What breaks if the operator dies halfway, and who repairs it? |
| 7 | **Idempotency** | Closure under repetition: does the retry duplicate the effect? |
| 8 | **Concurrency** | Do two operators on one element commute, serialize, or clobber? |
| 9 | **Symmetry** | Open without close, lock without release, pause without resume. |
| 10 | **Minimal expression** | A value both stored and derived: two sources of truth that drift. |
| 11 | **System limits** | Requirements outside the representable set — the hacks are the evidence. |
| 12 | **Feedback loops** | Retries feeding queues feeding retries, with no damper. |

It applies the ones your material supports honestly, and states which did not
apply and why.

## What you get

A Markdown file on your disk — `systemic-out/<scope>.md`. Never an artifact,
never a page served from localhost.

- **Systems identified** — a table of systems, objectives, elements, operators.
- **Conceptual machines** — mermaid state diagrams of what is *declared* and
  what is *built*, plus a state × operator matrix when the machine is small
  enough. The divergence between the two diagrams is usually the most valuable
  thing in the report.
- **Findings** — ordered by severity, each with the check it came from, the
  evidence, the systemic diagnosis, and a concrete recommendation.
- **Missing pieces** — the components the system needs; where the team is
  carving the requirement out of the board instead of making pieces first.
- **Limits and not-verified** — what the system cannot represent, and which
  checks could not be run with the available material.

### Every finding is labeled for honesty

| Label | Means |
|---|---|
| `INCONSISTENCY` | A contradiction **proven** with evidence. The system does X and also not-X. |
| `RISK` | Breaks under a stated, plausible condition — the condition is written down. |
| `AMBIGUITY` | Underspecified. The skill does **not** guess; it states the question your architect or product owner has to answer. |

Severity is `critical` / `high` / `medium` / `low`, rated by the damage the
finding actually causes.

**The honesty rule is non-negotiable**: no finding without evidence actually
read. Every claim cites `file:line` or a document section. If it cannot be
evidenced, it is not reported.

## A real example

Run against a deliberately broken orders module ([`evals/fixtures/orders/`](evals/fixtures/orders/)),
the report reads the matrix like this:

> Of 56 cells in the state × operator matrix, **one column** is properly
> closed (`deliver`) and **43 are holes**. `add_item` and `apply_discount` are
> absent because they are state-blind: they mutate a `delivered` order exactly
> as they mutate a `draft`.
>
> The function `is_final()` exists and **no operator calls it**. The system
> declares the notion of a final state and never uses it.

And it closes by naming the one missing piece that dissolves nine of the
fourteen findings at once:

> Every operation writes `order.status` directly. That means the state machine
> **is implemented nowhere** — it exists as prose in the README and as a set
> of strings in `models.py`, but no component enforces it. The team is cutting
> the wood: each operator carves its own transition by hand, which is exactly
> why each one can carve it wrong in a different way.

That is the difference from a code review. A review says *a guard is missing
on line 30*. This says *the machine is unimplemented, here is the piece, and
here are the nine findings it makes disappear*.

## What it is not

- **Not a linter.** It reads for meaning, not patterns. It will not find your
  unused imports, and it will find that your README forbids what your code
  permits.
- **Not a security scanner.** Use one; they are complementary.
- **Not free.** Systems thinking is expensive and is not aimed at trivial
  apps. It targets systems with real state — lifecycles, workflows, sagas,
  anything with a `status` column — where an inconsistency costs money. The
  report reflects that judgment and recommends new components only when the
  benefit justifies them.

## Language

The report is written in the language you ask for. Name one and it wins;
otherwise it follows the language you are writing in. Only the honesty labels
and the severities stay as fixed keywords in every language, so reports stay
comparable and greppable across projects.

## Layout

```
SKILL.md                      the skill: phases, report structure, rules
references/
  gst-framework.md            the conceptual vocabulary, loaded before phase 1
  checks.md                   how to detect each of the 12, loaded in phase 2
evals/
  evals.json                  6 evals with assertions
  fixtures/orders/            a code module with 9 seeded defects
  fixtures/rental-doc/        a design document with 7 seeded flaws
  fixtures/booking-saga/      a compensating saga: partial failure and loops
  fixtures/clean-ticket/      a correct lifecycle: the false-positive control
```

## Evals

`evals/evals.json` holds six cases with explicit assertions:

1. **seeded-defects-code** — 9 planted flaws in a Python module, self-contained.
2. **design-doc-only** — a design document with no code; verifies the skill
   cites only document sections and invents no code paths.
3. **real-repo-lifecycle** — a template; supply your own repo and lifecycle.
4. **explicit-report-language** — a Spanish prompt requesting an English
   report; verifies the explicit request wins and the labels stay untranslated.
5. **saga-compensations-and-loops** — a saga with compensations; exercises
   checks 6 and 12, which the other fixtures barely touch.
6. **clean-code-no-false-positives** — a deliberately correct module. Every
   other fixture rewards finding things; this one is graded on what the skill
   does **not** report. A run that "finds more" here is a worse run.

Substitute the skill's absolute path for `<SKILL_DIR>` when running them.

Eval 6 is the one that matters most as the skill changes. A tool that reports
problems is only as useful as its false-positive rate, and every other eval
pushes in the direction of reporting more.

## Contributing

The most useful contributions are **fixtures**: a lifecycle with a defect the
skill misses, plus the assertion that should have caught it. A check that
never fires on any fixture is a check nobody can trust.

## License

MIT — see [LICENSE](LICENSE).
