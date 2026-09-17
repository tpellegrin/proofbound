# Specification — `RateGuard.retry_after(key)`

Authority: `intent.md` (sha256 `a7e16b87c8dc8131edd027f289bb5bdcd80bc0fcca02e0827a88646280b70a04`),
whose seven numbered requirements are the requirements below. This document specifies observable
behaviour only. It does not implement anything, and it prescribes no internal structure. Section 7 is
advice, not requirement.

Requirement map: intent 1 → §3; intent 2 → §1; intent 3 → §2; intent 4 → §4; intent 5 → §2;
intent 6 → §6; intent 7 → §5.

## 0. Vocabulary

- **Instant** — a value returned by the injected clock. `now` is the instant a `retry_after` call
  samples.
- **Bucket** — the per-key state `allow` already keeps: a token count and the instant of the last
  update. A key never touched by `allow` has a full bucket (`capacity` tokens). `capacity` and
  `refill_per_second` are the constructor's values.
- **Admitted at `t`** — `allow(key)`, invoked at instant `t` with the key's bucket unchanged by any
  other call, returns `True`.
- **Exact real delay** — for a key refused at `now`, let `tokens` and `last` be its bucket's token
  count and last-update instant. Then

  `w* = max(0, (last + (1 - tokens) / refill_per_second) - now)`.

  This is the least non-negative real `δ` for which the mathematically exact token count at instant
  `now + δ` reaches `1`. It is the "mathematically exact requirement" that §3(b) measures excess
  against; it is **not** the definition of what `retry_after` must return.

  `w*` is an exact real quantity: the displayed expression denotes it in exact real arithmetic.
  Evaluating that expression in floating point returns a nearby `float` and is only an approximation
  of it, so §3(b)'s excess is measured against the real value `w*`, not against a floating-point
  evaluation of the expression.

## 1. Signature, return type, purity

`retry_after(key) -> float` is a method on `RateGuard`, taking the same kind of key as `allow`. It
returns a Python `float`:

- `0.0` exactly when `allow(key)` would be admitted at `now` (§2);
- otherwise a positive finite delay `w` satisfying §3, or `math.inf` in the exceptional case of §5.

It never raises for any key `allow` accepts, never sleeps, and performs no I/O.

**It is a query, not a call.** Calling it — once or a hundred times — changes nothing observable: it
consumes no token, creates no bucket for an unseen key, and does not change what any later `allow`
or `retry_after` returns. Asking twice leaves the limiter exactly as it already was.

## 2. Agreement with `allow`; unseen keys (intent 1, 3, 5)

`retry_after(key) == 0.0` **exactly when** `allow(key)` would be admitted at `now`. In particular:

- never `0.0` for a call that would be refused;
- never positive for a call that would be admitted;
- `0.0` for a key never seen before, whose bucket starts full.

The comparison is at the same sampled instant: `retry_after` samples the injected clock once and
answers for that instant.

## 3. The promise when refused (intent 1)

When the key would be refused at `now`, `retry_after` returns a positive delay `w` satisfying **both**
(a) and (b) below, whenever such a finite `w` exists. When no finite `w` satisfies both, §5 applies
instead.

**(a) The wait works.** Let `x = now + w`, evaluated as a single Python float addition — the instant
the clock reaches when advanced by exactly `w`. At instant `x`, `allow(key)` is admitted, provided
nothing else changed the key's bucket in between.

**(b) The wait is not wastefully large.** With `w*` the exact real delay of §0, the returned delay
satisfies `w - w* <= 4 * math.ulp(x)`: it may exceed the mathematically exact requirement by no more
than four units in the last place of the resulting instant `x = now + w`. (The bound is one-sided;
returning a delay at or below `w*` is allowed.)

The promise is about the instant the clock actually reaches, **not** about a real-valued formula. A
delay equal to the exact real wait need not reach an admitting instant — `intent.md` records two
measured counterexamples — and such a delay fails (a). If a formula is used to compute `w`, its
result must be validated against the reached instant, never assumed sufficient.

## 4. As the clock advances (intent 4)

With no intervening calls for the key, the returned value never increases as the clock advances: it
decreases toward `0.0` and, once it is `0.0`, stays `0.0`. It may decrease in jumps; continuity is
not required.

## 5. The exceptional case (intent 7)

If **no finite `float` `w` satisfies requirement 1 at `now`** — that is, no finite `w` both reaches
an admitting instant (§3(a)) and stays within the excess bound (§3(b)) — `retry_after` returns
`math.inf`. It is returned, not raised. §3's guarantee is scoped to the case where such a finite
delay exists; it is not a promise that one always does.

The predicate is the whole of requirement 1, not clause (a) alone. A finite delay can reach an
admitting instant while every delay that does so exceeds the four-ULP bound; in that state the answer
is `math.inf` too, because no finite delay satisfies requirement 1. This is reachable: when the
admitting instant is near zero while the bucket's last update is far from it, `math.ulp` at the
admitting instant is far finer than the unavoidable rounding in the refill product, so the least
admitting delay can exceed `4 * math.ulp(now + w)`. (Both documents leave the injected clock's domain
unrestricted, so such instants are legitimate.)

The `refill_per_second` case is the simpler, clause-(a)-only instance: a value small enough that no
finite delay reaches an admitting instant at all. Measured instance: `capacity=1`,
`refill_per_second=5e-324`, one admission, clock `1000.0` — the deficit divided by the refill rate
overflows the finite float range and no finite delay admits. Either way this is a property of a
constructor configuration the constructor already accepts, not an error. `allow` itself keeps working
normally; only the new query answers `math.inf`.

## 6. What must not change (intent 2, 6, and "What must not change")

- **Constructor.** The signature `RateGuard(capacity, refill_per_second, *, clock=time.monotonic)`
  and its validation (`capacity >= 1`; `refill_per_second > 0`) are unchanged. §5 describes what the
  new query returns for small values the constructor already accepts; it changes nothing about what
  is accepted.
- **`allow`.** Its behaviour, return value, token consumption, per-key independence, burst up to
  `capacity`, refill rate, and the fact that it writes bucket state even on refusal are all
  unchanged. Existing callers must not be able to tell the new query exists.
- **The clock.** The query reads the same injected clock; it must not call `time.sleep` or perform
  any I/O.
- **The existing suite.** `tests/test_rateguard.py` must keep passing, unedited.

Nothing beyond these is fixed. In particular, no internal structure, no naming beyond the public
`retry_after(key)`, and no resemblance to any particular implementation is required. Acceptance is
judged by observable behaviour only.

## 7. Advice, not requirement (intent's "note on how")

The refill arithmetic currently lives inside `allow`. Sharing it between `allow` and `retry_after`,
rather than computing it independently in two places, is probably wise to avoid drift. This is a
suggestion about construction, **not** an accepted requirement: any implementation satisfying
§§1–6 is acceptable, and nothing is rejected for factoring the arithmetic differently, or for not
factoring it at all.

If a formula is used, the exact real target instant is `last + (1 - tokens) / refill_per_second`.
One way to stay inside §3(b) is to return the smallest non-negative `w` whose reached instant
`now + w` is admitted, which requires checking the reached instant rather than assuming the exact
real wait suffices. If even that smallest admitting delay exceeds the four-ULP bound, no finite delay
satisfies requirement 1 and §5 calls for `math.inf`. The four-ULP allowance in §3(b) exists to absorb
the fact that the admitting instant can sit a few representable steps above the exact target; it is
not a licence to overshoot deliberately.
