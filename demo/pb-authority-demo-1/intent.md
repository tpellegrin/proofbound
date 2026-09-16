# Accepted intent — refusal must carry the wait

`rateguard` tells a caller yes or no. A caller told "no" cannot tell whether to retry in a
millisecond or a minute, so it either hammers the limiter or backs off far longer than necessary.
Refusal should carry the wait.

## What must become true

`RateGuard` gains a query, `retry_after(key)`, returning a `float` number of seconds:

1. **It answers "how long until `allow(key)` would admit".** When a call would be admitted right
   now, the answer is `0.0`. Otherwise it is the time until enough of a token has refilled for
   `allow(key)` to return `True`.
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

## What must not change

- The constructor's signature and validation.
- Per-key independence, the burst allowance up to `capacity`, and the refill rate.
- The injectable clock: the new query must read the same clock and must not call `time.sleep` or
  perform any I/O.

## A note on how, which is advice and not a requirement

The refill arithmetic currently lives inside `allow`. Two places computing it independently is how
this kind of limiter drifts, so sharing it between `allow` and `retry_after` is probably wise. This
is a suggestion about construction, **not** an accepted requirement: any implementation satisfying
the numbered points above is acceptable, and nothing will be rejected for factoring the arithmetic
differently, or for not factoring it at all.

## How acceptance will be judged

By observable behaviour only — the six numbered points, the unedited existing suite, and no I/O or
sleeping in the new query. Not by internal structure, naming beyond the public `retry_after(key)`,
or resemblance to any particular implementation.
