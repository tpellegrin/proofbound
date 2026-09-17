# Task RG-spec — specify the change the accepted intent asks for
Contract revision: r0001
Accepted authority: `intent.md`, sha256 `a7e16b87c8dc8131edd027f289bb5bdcd80bc0fcca02e0827a88646280b70a04`
  (external to the ledger; recompute and compare before relying on this contract)

## Review purpose
- specification-reflection

## Objective
Read `intent.md` at the project root and the existing `rateguard` package, then write `spec.md` at
the project root: a specification of the change the intent asks for, precise enough that someone
who has not read the intent could implement it and someone else could judge the result.

The intent's **seven** numbered requirements are the authority. Restate them as a specification of
observable behaviour, resolve anything they leave ambiguous, and say explicitly what is not
changing.

Requirement 1 is the delicate one and the intent explains why: it is a promise about the instant the
clock actually reaches, not about real-valued arithmetic. Do not replace it with a formula and then
assert an exact-boundary property the formula does not have — the predecessor specification did
exactly that and was rejected for it. If you state a formula, state it as one way to compute a
delay that satisfies the promise, not as the promise.

The intent's remark about the refill arithmetic is advice; carry it across as advice.

Do not implement anything. Do not modify `rateguard/` or `tests/`.

## Independent review
A later attempt by an independent reflector judges, from `intent.md` and `spec.md` alone, whether
the specification is an adequate and faithful specification of the accepted intent. The reflector is
given the author's report as an exact input and nothing else of the author's; it is not asked to
agree. It should consider whether every numbered requirement is addressed, whether the specification
contradicts the intent or invents requirements the intent does not support, whether it is precise
enough to implement and to judge, whether anything it asserts is actually true of the arithmetic it
mandates, and whether it keeps requirements distinct from advice. Finding no defect is a legitimate
outcome.

## Allowed source changes
- `spec.md`

## Acceptance criteria
- AC-001 — `spec.md` exists at the project root and specifies `retry_after(key)`'s observable
  behaviour: its return type, when it returns `0.0`, what waiting the returned delay guarantees,
  the bound on excess delay, whether it affects later calls, its behaviour for a key never seen
  before, its behaviour as the clock advances, and the exceptional case.
- AC-002 — `spec.md` states what must not change.
- AC-003 — nothing `spec.md` asserts is false of the computation it prescribes.
- AC-004 — no file other than `spec.md` is modified.
