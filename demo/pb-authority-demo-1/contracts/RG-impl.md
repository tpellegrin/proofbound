# Task RG-impl — implement the accepted specification
Contract revision: r0001

## Review purpose
- implementation-review

## Proofbound candidate
- <CANDIDATE>

## Objective
Implement the change specified in `spec.md` at the project root, against the accepted candidate
named above. `intent.md` is the authority behind it.

Add `retry_after(key)` to `RateGuard` in `rateguard/__init__.py`.

The existing suite in `tests/` must keep passing **unedited**. Do not modify, delete or add tests:
they are not yours to change, and a change there is a scope violation, not a repair.

## Independent review
A later attempt by an independent reviewer judges the implementation against `spec.md`, from the
code and the specification — not from the implementer's reasoning or its own assessment. It should
consider whether `retry_after` matches every specified behaviour, whether it affects later calls,
its behaviour for an unseen key and at the refill boundary, whether `allow` still means what it
did, and whether anything outside the permitted file changed. Finding no defect is a legitimate
outcome; so is finding one.

## Allowed source changes
- `rateguard/__init__.py`

## Acceptance criteria
- AC-001 — `RateGuard.retry_after(key)` exists and behaves as `spec.md` specifies.
- AC-002 — `python3 -m unittest discover -s tests -t tests` passes with `PYTHONPATH` at the project
  root, with no file under `tests/` modified.
- AC-003 — no file other than `rateguard/__init__.py` is modified.
