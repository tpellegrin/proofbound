# DSD Spec Author report — RG-spec (attempt spec-author-2)

Status: COMPLETE.

## Task
- Role: `dsd-spec-author`. Contract: `runs/r1/contracts/RG-spec.md` (rev r0001).
- Allowed source change (hard boundary): `spec.md` at the project root only. No implementation, no
  edits to `rateguard/` or `tests/`.
- Authority: `intent.md` at the project root. I recomputed its sha256 and it equals the contract's
  accepted authority `a7e16b87c8dc8131edd027f289bb5bdcd80bc0fcca02e0827a88646280b70a04` (measured with
  `shasum -a 256 intent.md`).

## Conclusion
Wrote `/Users/thiago/.proofbound/demo2/live/project/spec.md`: a specification of the observable
behaviour of `RateGuard.retry_after(key)` covering all seven numbered intent requirements, resolving
their ambiguity, keeping requirements distinct from advice, and stating explicitly what does not
change. Nothing else in the project was modified. No `DECISION_REQUIRED`: the contract and intent
were sufficient and consistent.

## What the artifact specifies (decisive choices)
- Requirement 1 is carried as the intent phrases it: a promise about the instant the clock actually
  reaches (`x = now + w`, a single float addition), **not** about a real-valued formula. The exact
  real wait `w* = max(0, (last + (1 - tokens)/refill_per_second) - now)` appears only as the
  reference for the excess bound `w - w* <= 4*math.ulp(now + w)`, never as the required return.
- The 0.0 case, the "query not a call" purity, agreement with `allow`, monotonicity in the clock,
  unseen-key behaviour, the `math.inf` exceptional case, and the "must not change" list are each
  stated as observable behaviour.
- The intent's refill-arithmetic remark is carried in a clearly non-normative "Advice" section, as
  advice, and the spec says an implementation is acceptable whether or not it shares the arithmetic.

## Verification actually performed
- Read `intent.md`, `rateguard/__init__.py`, `tests/test_rateguard.py`, `PLAN.md`,
  `change-graph.json`, and the prior attempt's evidence.
- Measured both of the intent's counterexamples against the existing `allow` semantics (scratch
  scripts in the OS temp dir, not project artifacts):
  - `capacity=2, refill_per_second=1.3, clock 1000.0`, drained: exact real wait
    `0.7692307692307692` refuses at `1000.7692307692307`; `nextafter(wait, inf)` gives the same
    instant and also refuses. The smallest admitting instant is `1000.7692307692308`, one ULP above
    the exact target, reached by delay `0.7692307692308304`.
  - `capacity=1, refill_per_second=0.09, clock 0.0`, one admission: exact wait
    `11.11111111111111` refuses; smallest admitting instant `11.111111111111112`, one ULP above.
- Randomised check of the construction "smallest non-negative `w` whose reached instant admits",
  against the exact rational target: over 40,000 random states the admitting instant exceeded the
  exact target by at most ~1.25 ULP of the resulting instant (allowance is 4). This supports the
  claim that the four-ULP bound is satisfiable.
- Exceptional case confirmed: for `refill_per_second` at or below the finite-float threshold
  (`(1 - tokens)/refill_per_second` overflowing to `+inf`, e.g. `5e-324`, `1e-320`, `1e-310`) no
  finite admitting delay exists, so the answer is `math.inf`; `1e-300` still yields a finite delay.

## Defects / uncertainty / boundaries
- The spec is a behavioural specification, not an implementation; it does not prescribe a
  computation, so there is no formula whose exact-boundary properties could be false. The only
  formula stated (`w*`) is defined as a reference quantity, and the spec explicitly says the promise
  is about the instant, not the formula.
- Out of scope / left unspecified: behaviour when the injected clock goes backwards; performance of
  the implementation. The intent does not constrain these.
- No unresolved authority or product decision. Independent reflection is still required; I do not
  approve my own artifact.

## What remains
- Nothing for this attempt. The deliverable `spec.md` is in place and this report is current.
