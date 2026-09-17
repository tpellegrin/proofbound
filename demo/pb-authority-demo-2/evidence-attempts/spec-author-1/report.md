# DSD Spec Author report — RG-spec (attempt spec-author-1)

Status: IN PROGRESS (report started before authoring; will be kept current).

## Task
- Role: `dsd-spec-author`. Contract: `runs/r1/contracts/RG-spec.md` (rev r0001).
- Deliverable (allowed source change): `spec.md` at project root only.
- Authority: `intent.md` (project root). Verified its sha256 equals the contract's accepted
  authority: `a7e16b87c8dc8131edd027f289bb5bdcd80bc0fcca02e0827a88646280b70a04` (measured with
  `shasum -a 256`).
- Objective: specify the observable behaviour of a new `RateGuard.retry_after(key)` from the
  intent's seven numbered requirements, resolving ambiguity, keeping requirements distinct from
  advice, and saying what must not change. No implementation, no edits to `rateguard/` or `tests/`.

## Work so far
- Read WORKER_RULES.md, COMMON.md, role SKILL.md, contract, `intent.md`, `rateguard/__init__.py`,
  `tests/test_rateguard.py`, `PLAN.md`, `change-graph.json`.
- Measured the arithmetic in the intent's two counterexamples and validated a construction in a
  scratch script (temp dir, not project). Results below.

## Decisive evidence (measured, scratch scripts in temp dir; not project artifacts)
- Existing `allow` refill: `elapsed = max(0, now-last)`, `tokens = min(capacity, tokens +
  elapsed*refill_per_second)`, admit iff `tokens >= 1.0`; state is written even on refusal.
- Intent example 1 reproduced: `capacity=2, r=1.3, now=1000.0`, drained bucket. Exact real delay
  `0.7692307692307692`; `now+d` refuses; `nextafter(d, inf)` gives the *same* instant
  `1000.7692307692307`, also refuses. Confirms the intent's warning.
- Intent example 2 reproduced: `capacity=1, r=0.09, now=0.0`, one admission. Exact delay
  `11.11111111111111` refuses at `now+d`.
- A construction that starts from the exact real requirement and then steps by `math.nextafter`
  to the first float delay at which a faithful re-evaluation of `allow`'s admit test is true:
  returns an admitting delay for both examples; over 200k randomized states the delay excess was
  at most 2.0 ULP of the resulting instant (allowance is 4), and the value was non-increasing as
  the clock advanced by one ULP. Tiny `refill_per_second` (5e-324, 1e-320) yields no finite
  admitting delay, matching requirement 7's `math.inf` case.

## Pending
- Write `spec.md`, re-verify against repository, finalize this report.
