# RG-spec spec-author report (attempt 1)

Status: COMPLETE — `spec.md` written; scope verified.

## Task
Contract `RG-spec` (r0001): read `intent.md` and the existing `rateguard` package, then write
`spec.md` at the project root specifying the change the accepted intent asks for. Allowed source
change: `spec.md` only. No implementation, no changes to `rateguard/` or `tests/`.

## Artifact written
- `/Users/thiago/.proofbound/demo/live/project/spec.md` (new file; only project source change).

Structure: interface, six normative requirements restated as observable behaviour, resolved
ambiguities, "what must not change", the intent's refill-arithmetic note carried across explicitly
as non-normative advice, and how the specification is judged.

## Inputs read
- `intent.md` — six numbered requirements, "what must not change", non-normative note on refill
  arithmetic.
- `rateguard/__init__.py` — current `RateGuard` / `allow` implementation.
- `tests/test_rateguard.py` — existing suite that must keep passing unedited.
- `PLAN.md`, `change-graph.json`, contract `RG-spec.md`.

## Decisive reasoning
- **Uniqueness of the answer (R1).** The intent asks for the time until `allow(key)` would admit.
  Since `capacity >= 1`, the cap cannot delay reaching one token, so for `available < 1.0` the wait
  is exactly `(1.0 - available) / refill_per_second`; for `available >= 1.0` it is `0.0`. The spec
  states this as the observable value, not as a required internal factoring.
- **R3 needs R2.** `allow` mutates state, so "agreement at the same instant" is only testable if
  `retry_after` is pure. The spec makes purity explicit and describes the single-clock-value
  observation (`retry_after` then `allow`) that a judge can use.
- **Clock rewind is the main ambiguity.** `allow` clamps elapsed to `max(0.0, now - last)`. The spec
  requires `retry_after` to apply the same clamp, otherwise R3 would fail on a backwards clock and
  R1 could return a negative value. Recorded under "Resolved ambiguities".
- **Unseen keys.** `allow` starts unseen keys full, so `retry_after` must return `0.0`; the spec adds
  that `retry_after` leaves no observable trace, consistent with R2 and R5.
- **Advice vs requirement.** The refill-sharing note is placed in a clearly labelled non-normative
  section, per the contract's instruction to carry it across as advice.

## Verification actually performed
- `spec.md` exists at the project root and is the only non-DSD project source change:
  `git status --short` shows `?? spec.md` plus DSD harness files (`state.json`, `attempts/`), which
  are outside the allowed-source boundary and not authored by me.
- Existing suite passes unedited against the unchanged package:
  `PYTHONPATH=. python3 -m unittest tests.test_rateguard -v` → `Ran 5 tests ... OK`.
- No edits made to `rateguard/` or `tests/` (no diff under either path).

## Acceptance criteria check
- AC-001 — `spec.md` specifies `retry_after(key)`'s return type (`float`, finite, `>= 0.0`), when it
  returns `0.0` (R1/R3, inclusive boundary), that it does not affect later calls (R2), unseen-key
  behaviour (R5), and behaviour as the clock advances (R4). Met.
- AC-002 — "What must not change" section covers constructor/validation, per-key independence,
  burst, refill rate, `allow` semantics, injectable clock with no sleep/I/O, and the unedited suite.
  Met.
- AC-003 — only `spec.md` added among project source; `rateguard/` and `tests/` untouched. Met.

## Uncertainties / boundaries
- None requiring authority. The contract's independent reflector judges from `intent.md` and
  `spec.md` alone; this report is not part of that judgement.

## What remains
- Independent specification-reflection review of `spec.md` (not performed by the author, by design).
