# Task RG-spec — specify the change the accepted intent asks for
Contract revision: r0001

## Review purpose
- specification-reflection

## Objective
Read `intent.md` at the project root and the existing `rateguard` package, then write `spec.md` at
the project root: a specification of the change the intent asks for, precise enough that someone
who has not read the intent could implement it and someone else could judge the result.

Specify observable behaviour. The intent's six numbered requirements are the authority: restate
them as a specification, resolve anything they leave ambiguous, and say explicitly what is not
changing. The intent's remark about the refill arithmetic is advice; carry it across as advice.

Do not implement anything. Do not modify `rateguard/` or `tests/`.

## Independent review
A later attempt by an independent reflector judges, from `intent.md` and `spec.md` alone, whether
the specification is an adequate and faithful specification of the accepted intent. The reflector
is not asked to agree with the author and is given no reasoning beyond the author's report. It
should consider whether every numbered requirement is addressed, whether the specification
contradicts the intent or invents requirements, whether it is precise enough to implement and to
judge, and whether it keeps requirements distinct from advice. Finding no defect is a legitimate
outcome.

## Allowed source changes
- `spec.md`

## Acceptance criteria
- AC-001 — `spec.md` exists at the project root and specifies `retry_after(key)`'s observable
  behaviour: its return type, when it returns `0.0`, whether it affects later calls, its behaviour
  for a key never seen before, and its behaviour as the clock advances.
- AC-002 — `spec.md` states what must not change.
- AC-003 — no file other than `spec.md` is modified.
