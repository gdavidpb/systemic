# Conceptual framework — GST applied to software engineering

This file distills General Systems Theory as applied to software design; the
skill's report is written in this vocabulary. The concepts are
language-independent — keep them, and translate the prose into whatever
language the report is being written in.

## Definition

**System** (Bertalanffy, GST): "a set of components that relate to each other
with a single objective". Lineage: Bertalanffy (*General System Theory*) →
Churchman (*The Systems Approach*) → Checkland (*Systems Thinking, Systems
Practice*). Bertalanffy used the theory to **describe** systems; software
engineering uses it to **create** them.

## Component categories

- **Elements** — the concrete: the Tangram pieces, the numbers of the numeric
  system, the models/entities of an app (User, Account, Transaction).
- **Operators** — the abstract that relates: Tangram's union `U` and rotation
  `R`, addition in the numeric system, repositories (Data layer), use cases
  (Domain layer), user actions (Presentation layer).

The system is not just the pieces: **it is the pieces and their capacity to
join**. Omitting the operators leaves the system half-described.

## Zero ambiguity (the `A U B` problem)

"A joined-with B" admits multiple interpretations (which side? what rotation?)
→ the system is **not fully described**; components are missing (the rotation
operator, the top/bottom/left/right sides). In software: an operator whose
effect depends on implicit interpretation (a parameter that changes meaning, an
operation that behaves differently depending on the caller) is an
underspecified system. The cure: a formal language — symbols bound to
unambiguous ideas.

## System limits

Not every figure is buildable: there are no circles in Tangram. **Canonical
example**: in a system with only even numbers and addition, 7 is
unrepresentable — and that is not "impossible", it means **components are
missing** (an odd number). Knowing the limits = knowing what can be built and
what demands new pieces. Three sets:

1. **Figures** — the unbounded space of the imaginable (the Mona Lisa).
2. **Possible figures** — buildable with the components, but invalid per the
   rules (a 2-piece figure when the game requires all 7).
3. **Valid figures** — possible AND rule-conforming.

In software: requirements outside the representable set are recognized by the
hacks they force ("cutting the wood").

## Consistency and closure

A system is **consistent** when it is free of contradictions. The star test is
**closure**: every operation on the system's elements must produce an element
of the system. **Canonical example**: the integers are NOT closed under
division — `1/2 = 0.5` and `0.5` does not exist in the system. It is a serious
problem: two legitimate elements, one legitimate operator, and a result the
system **has no way to represent**. In software: an operation that leaves a
record in a state no enum declares, or a field combination no flow accounts
for.

## Minimal expression

Primitive vs derivable components: the Tangram square is reducible —
`D = (B R +225) left U (B R +45) right`. Identifying the minimal expression
avoids redundancy. In software: when a component is derivable from others but
is ALSO materialized as a primitive (a total stored AND computed), there are
two sources of truth that can drift apart.

## Diagnostic table

| Symptom | Systemic diagnosis |
|---|---|
| "My application is a monolith" | The system has a single component; all responsibility falls on it |
| "Something simple is very costly" | Insufficient, deficient or ill-defined components |
| "Something simple cannot be done" | Excessive limits; components built without a clear objective |
| "Many errors, unexpected behavior, poor traceability" | Inconsistent system: the effect of operations is unknown |

In general, software problems appear through the absence of patterns and
principles — which are nothing more than general representations of the
components an application should be made of.

## Wood vs pieces (the key idea)

Patterns and good practices **are not the pieces: they are the wood** the
pieces are made of. Do not use good practices to build the requirement
directly (that is carving the figure straight out of the wooden board); use
them to craft the pieces with which you then build **all** the requirements.
That is the architect's job: first build the system (a domain framework of
your own) whose pieces can generate every figure the business needs —
movable, without carving, with a guarantee of no inconsistency.

The systems-vision questions:
1. What are the components of my system?
2. What is their most atomic representation?
3. How do they interact?
4. Are there limits?
5. Is that interaction consistent?

## The bank exercise (worked example)

A banking app on Clean Architecture: each layer (Data, Domain, Presentation)
is a system with its elements (per-layer model forms) and operators
(repositories / use cases / user actions). Presentation is built from Domain
components; Domain from Data components. And GST begins where implementation
usually ends: defining the **transversal components** — a "Step" system (bank
features run in steps) and "Flow" (a set of steps), with optional input/output
and a "Continue" operator that advances **only after validating that the
current step is in a consistent state**. That is a well-designed conceptual
machine.

## Cost

Systems thinking is expensive and is not aimed at trivial apps: it targets
large systems where time-to-market and efficiency matter. Like everything in
architecture: a price is paid and a benefit is obtained. The report must
reflect that judgment — recommend new pieces only when the benefit justifies
them.
