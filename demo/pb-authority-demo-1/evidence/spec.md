# Specification — `retry_after(key)` on `RateGuard`

This document specifies a change to the `rateguard` package. It is a specification only; it does not
implement the change and does not modify `rateguard/` or `tests/`. It is written so that someone who
has not read `intent.md` can implement it, and someone else can judge the result.

## 1. Summary

`rateguard.RateGuard` gains one new public method, `retry_after(key)`, that reports how long a caller
should wait before `allow(key)` would admit. It is a pure query: it reads the same injectable clock
as `allow` and changes nothing. `allow` itself is unchanged.

## 2. Interface

```python
class RateGuard:
    def retry_after(self, key: str) -> float: ...
```

- `key` is a `str`, the same domain `allow` accepts.
- The return value is a `float` number of seconds.
- The return value is always finite and `>= 0.0`. It is `0.0` exactly when a call would be admitted
  at that instant.
- `retry_after` does not raise for any key that `allow` accepts, including a key never seen before.

## 3. Normative observable behaviour

The six requirements below are the intent's six numbered points, restated as a specification.

Throughout, for a given key at clock instant `now = clock()`:

- `available` is the token count `allow(key)` would use at that instant if it were called now — the
  bucket's stored tokens refilled by `max(0.0, now - last_activity) * refill_per_second` and capped
  at `capacity`. For a key never seen before, `available == capacity`.

### R1 — It answers "how long until `allow(key)` would admit"

If `available >= 1.0`, `retry_after(key)` returns `0.0`. Otherwise it returns
`(1.0 - available) / refill_per_second`, the amount of refill time needed to reach one token.

The returned number is fully determined by the state and the clock. At exactly that many seconds
later, with no intervening state-changing call, `allow(key)` returns `True`; immediately before, it
returns `False`.

### R2 — It is a query, not a call

`retry_after` consumes no token and mutates no state. Calling it any number of times, in any
interleaving with other reads, leaves the limiter in exactly the state it was already in.
Consequently it does not change what any later `allow` or `retry_after` returns.

### R3 — Its answer and `allow`'s answer agree

At any instant and in any state, `retry_after(key) == 0.0` if and only if `allow(key)` would return
`True` if called at that instant. It is never `0.0` for a call that would be refused, and never
positive for a call that would be admitted.

Because `retry_after` is pure (R2), this is observable at a single clock value: read
`retry_after(key)`, then call `allow(key)` without advancing the clock, and the predicate
`retry_after(key) == 0.0` equals the boolean `allow` returned.

### R4 — Waiting only helps

With no intervening state-changing call and no clock rewind, as the clock advances
`retry_after(key)` is non-increasing: it decreases toward `0.0`, and once it is `0.0` it stays `0.0`.

### R5 — A key never seen before is not rate limited

For a key never passed to `allow` or `retry_after`, `retry_after(key)` returns `0.0`. The bucket is
treated as full, consistent with `allow`'s existing behaviour for unseen keys.

### R6 — `allow` keeps exactly the meaning it has today

`allow` keeps its current signature, return type, and semantics. Existing callers cannot observe that
anything changed, and the existing test suite passes unedited.

## 4. Resolved ambiguities

These are choices made where the intent left room; they are consistent with the six requirements.

- **Clock rewind.** `retry_after` applies the same clamp as `allow`: elapsed time is
  `max(0.0, now - last_activity)`, never negative. A backwards clock therefore does not lower
  `available` and cannot make the result negative.
- **Boundary is inclusive.** `available >= 1.0` is admitted and yields `0.0`; a bucket holding
  exactly `1.0` token yields `0.0` and `allow` returns `True`.
- **Unseen keys leave no trace.** `retry_after` must not create observable state for an unseen key;
  a later `allow` for that key behaves exactly as if `retry_after` had never been called.
- **Keys are independent.** `retry_after` for one key never affects the value returned for another.
- **Only one addition.** No new constructor parameters and no other public API changes are part of
  this specification.

## 5. What must not change

- The constructor `RateGuard(capacity, refill_per_second, *, clock=time.monotonic)` and its
  validation (`ValueError` when `capacity < 1` or `refill_per_second <= 0`).
- The public attributes `capacity` and `refill_per_second` and their meaning.
- Per-key independence, the burst allowance up to `capacity`, and the constant refill rate.
- `allow(key)`'s observable behaviour, including token consumption, the full bucket for an unseen
  key, capping at `capacity`, and the non-negative elapsed clamp.
- The injectable clock: `retry_after` reads the same clock and performs no `time.sleep` and no I/O.
- The existing test suite, which must keep passing unedited.
- No module behaviour other than the addition of `retry_after` changes.

## 6. Advice (non-normative)

The intent's note on the refill arithmetic is advice, not a requirement, and is carried across as
such. Because the same arithmetic decides both `allow` and `retry_after`, sharing it between the two
is probably wise to avoid drift. This is a suggestion about construction only: any implementation
satisfying sections 3–5 is acceptable, and nothing is rejected for factoring the arithmetic
differently, or for not factoring it at all.

## 7. How this specification is judged

By observable behaviour only: the six requirements in section 3, the unedited existing suite, and no
I/O or sleeping in `retry_after`. Not by internal structure, naming beyond the public
`retry_after(key)`, or resemblance to any particular implementation.
