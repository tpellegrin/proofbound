# Accepted intent — refusal must carry a wait that actually works

`rateguard` tells a caller yes or no. A caller told "no" cannot tell whether to retry in a
millisecond or a minute, so it either hammers the limiter or backs off far longer than necessary.
Refusal should carry the wait.

## What must become true

`RateGuard` gains a query, `retry_after(key)`, returning a `float` number of seconds:

1. **It answers "how long until `allow(key)` would admit", and the answer is usable.** When a call
   would be admitted at this instant, the answer is `0.0`. Otherwise the answer is a positive delay
   `w` with this guarantee:

   > advancing the injected clock by `w` — a single addition, `now + w`, as ordinary Python
   > floating-point arithmetic performs it — yields an instant at which `allow(key)` admits,
   > provided nothing else changed the key's state in between.

   The delay must not be wastefully large: it may exceed the mathematically exact requirement by no
   more than **four units in the last place of the resulting instant** `now + w`.

2. **It is a query, not a call.** `retry_after` must not consume a token and must not change what
   any later `allow` or `retry_after` returns. Asking twice, or a hundred times, leaves the limiter
   in the state it was already in.

3. **Its answer and `allow`'s answer agree.** `retry_after(key) == 0.0` exactly when `allow(key)`
   would return `True` at that same instant — never `0.0` for a call that would be refused, and
   never positive for a call that would be admitted.

4. **Waiting only helps.** With no intervening calls, the value never increases as the clock
   advances: it decreases toward `0.0` and stays there.

5. **A key never seen before is not rate limited.** Its bucket starts full, so `retry_after` for an
   unseen key is `0.0`.

6. **`allow` keeps exactly the meaning it has today.** Existing callers must not be able to tell
   that anything changed, and the existing suite must keep passing unedited.

## The exceptional case, defined rather than left open

The constructor accepts any `refill_per_second > 0`, including values so small that no usable delay
exists. For those:

7. **When no finite delay can satisfy requirement 1, `retry_after` returns `math.inf`.** That is the
   honest answer — "no wait I can express will get you admitted" — and it is returned, not raised.
   `retry_after` raises nothing for any key `allow` accepts.

Requirement 1's guarantee is therefore scoped to the case where a finite delay exists. It is not a
promise that one always does.

## Why requirement 1 is phrased about the clock and not about arithmetic

Because the obvious phrasings are false, and this was established by measurement before the
requirement was written. Against the predecessor's reference implementation, with `capacity = 2`,
`refill_per_second = 1.3` and a clock starting at `1000.0`, two admissions drain the bucket and the
mathematically exact wait is `0.7692307692307692`. Advancing the clock by exactly that still
refuses. Advancing instead by `math.nextafter(0.7692307692307692, math.inf)` —
`0.7692307692307693`, a strictly larger delay — **also refuses, because both additions produce the
same instant**, `1000.7692307692307`. A correction in delay space need not change the resulting
timestamp at all, so "any strictly greater wait admits" is not a repair.

A clock starting at zero is no exemption either: `capacity = 1`, `refill_per_second = 0.09`, one
admission, and advancing by the returned `11.11111111111111` also refuses.

So the promise is made about the thing a caller can observe — the instant the clock actually reaches
— and the excess is bounded in units of that instant's representable granularity, because nothing
finer than that granularity can be promised.

## What must not change

- The constructor's signature and its existing validation. `refill_per_second > 0` is still the
  whole of it; requirement 7 describes what the new query does with the small values it already
  accepts, and changes nothing about what is accepted.
- `allow`'s behaviour, per-key independence, the burst allowance up to `capacity`, and the refill
  rate.
- The injectable clock. The new query must read the same clock, and must not call `time.sleep` or
  perform any I/O.

## A note on how, which is advice and not a requirement

The refill arithmetic currently lives inside `allow`. Two places computing it independently is how
this kind of limiter drifts, so sharing it between `allow` and `retry_after` is probably wise. This
is a suggestion about construction, **not** an accepted requirement: any implementation satisfying
the numbered points above is acceptable, and nothing will be rejected for factoring the arithmetic
differently, or for not factoring it at all.

## How acceptance will be judged

By observable behaviour only — the seven numbered points, the unedited existing suite, and no I/O or
sleeping in the new query. Not by internal structure, naming beyond the public `retry_after(key)`,
or resemblance to any particular implementation.
