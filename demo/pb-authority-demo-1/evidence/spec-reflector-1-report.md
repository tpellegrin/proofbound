# RG-spec specification-reflection report (attempt 1)

Role: `dsd-spec-reflector` (project-read-only). Contract: `RG-spec` r0001.
Artifact under review: `/Users/thiago/.proofbound/demo/live/project/spec.md`
sha256 `b7891057f4b88e1c4aaf0b53d86dbe2ac4155450a792dcf655d24bba63069335`.
Authority read: `intent.md` (sha256 `3f8edd357fba05e21b468b4d065abc57fcbddfeaf187a03d107b07f80276fa67`),
`rateguard/__init__.py`, `tests/test_rateguard.py`, contract `RG-spec.md`, `PLAN.md`,
`change-graph.json`. Input report `spec-author-1/report.md` hash verified equal to the supplied
`4172be96…268`. No project files were modified by this attempt.

## Conclusion

**FAIL — one blocking finding.** The specification is faithful and well-resolved almost everywhere,
but normative requirement **R1 contains a self-contradiction** between the formula it mandates and
the exact-boundary behaviour it asserts. A spec-faithful implementation, combined with the immutable
`allow`, does *not* admit at exactly `retry_after` seconds later in a large fraction of ordinary
parameter/clock configurations. This makes R1 not precisely implementable and not reliably
judgeable as written. One minor over-claim (`always finite`) is also noted. R2–R6, the
"what must not change" section, the advice handling, and AC-001/002/003 otherwise check out.

## Decisive evidence

### Blocking: R1 exact-boundary claim is false under the mandated formula

`spec.md` §3 R1 says, normatively: the method returns `(1.0 - available) / refill_per_second`, and
"At exactly that many seconds later, with no intervening state-changing call, `allow(key)` returns
`True`; immediately before, it returns `False`."

I implemented `retry_after` exactly as §2–§4 prescribe (same refill arithmetic and clamp as
`allow`, pure, no mutation) as a subclass of the real `RateGuard`, and used the project's own
`FakeClock` convention (base `1000.0`, as in `tests/test_rateguard.py:11`). Then I advanced the
clock by exactly the returned value and called the real `allow`:

```
cap=2 rate=1.3 after 2 allows: retry_after = 0.7692307692307692
  clock.now        = 1000.7692307692307
  elapsed by allow = 0.7692307692307168   # (now + w) - now  !=  w
  allow avail      = 0.9999999999999318   # < 1.0
  allow("k")       = False                # R1 says it must be True
```

The cause is floating-point precision loss in the clock arithmetic the spec itself requires
`allow` to use (`elapsed = now - last`). Advancing the clock by `w` from a non-zero base does not
reproduce `w` as `elapsed`; the shortfall here is `5.24e-14`, far larger than one ULP of `w`, so
even `math.nextafter(w, +inf)` still refuses. A grid sweep over `capacity` 1–5 × rates
{0.1, 0.3, 0.7, 1.0, 1.3, 2.0, 3.0, 7.0, 1000.0} × drained depths produced **45 of 135**
exact-advance cases where `allow` returns `False` after waiting exactly `retry_after`.

Why it matters: the entire purpose of the intent is "refusal should carry the wait" — the returned
number is supposed to be sufficient. A judge testing observable behaviour (which the contract says
is the standard) can advance exactly `retry_after` and observe refusal, rejecting a correct
implementation; an implementer can be pushed toward an impossible exact-equality guarantee. The
same run showed R3's own single-instant test, R4 monotonicity, and R5 unseen-key behaviour all
hold, so the defect is isolated to this boundary sentence.

The boundary only holds when the clock base is exactly `0.0` (verified); it fails for any non-zero
offset, which includes real `time.monotonic()` and the project's existing test clock.

### Minor: `finite` is not guaranteed by the mandated formula

`spec.md` §2 claims the return value is "always finite". For a positive but subnormal
`refill_per_second` the mandated `(1.0 - available) / refill_per_second` overflows:
`refill_per_second = 1e-310` → `retry_after = inf`. The constructor (`rateguard/__init__.py:20`)
only requires `refill_per_second > 0`, so this is reachable. `finite` is an invented constraint
(not in `intent.md`) and is inconsistent with the spec's own formula. Low severity, but it should
be dropped or bounded.

## Actionable guidance for a reviser

1. Resolve the boundary explicitly in §4 and align R1's prose. Two workable options:
   - **Limit/supremum wording (recommended):** state that `retry_after` is the infimum of waits
     after which `allow` admits; any wait *strictly greater* than the returned value admits, and
     admission at exact equality is not required (floating-point boundary). Delete the "At exactly
     that many seconds later … returns `True`" sentence or qualify it as the mathematical limit.
   - **Sufficiency requirement:** require the returned value to be rounded up enough that advancing
     the same clock by it guarantees `allow` returns `True`; then keep the exact-boundary claim but
     state it as a testable implementation obligation.
2. Either remove "always finite" from §2 or replace it with an accurate bound (e.g. "finite for any
   `refill_per_second` not subnormal", or simply `>= 0.0`).

## What checked out (no finding)

- Every one of the intent's six numbered requirements is addressed and restated: R1–R6 in §3 map
  one-to-one to intent points 1–6, in the same order and with the same meaning.
- **R2 purity / no effect on later calls:** candidate leaves `_tokens`/`_last` unchanged across
  repeated calls; no failures in 20,000 randomized trials.
- **R3 agreement:** `retry_after == 0.0` iff `allow` returns `True` at the same instant held in all
  trials; the inclusive `available >= 1.0` boundary is stated and correct.
- **R4 waiting only helps:** non-increasing under clock advance held in all trials; the added
  "no clock rewind" qualifier is consistent with the intent's "as the clock advances".
- **R5 unseen key:** returns `0.0` and leaves no observable trace; verified no state mutation.
- **Clock rewind:** resolving it to the same `max(0.0, now - last)` clamp as `allow` is the choice
  that makes R3 and non-negativity hold, and it is consistent with `rateguard/__init__.py:37-38`.
- **Advice vs requirement:** the refill-sharing note is carried across in a clearly labelled
  non-normative section (§6), exactly as the contract requires; no advice is promoted to a
  requirement.
- **"What must not change" (§5):** constructor signature/validation, `capacity` and
  `refill_per_second`, per-key independence, burst/cap, constant refill, `allow` semantics, the
  injectable clock with no sleep/I/O, and the unedited suite are all enumerated. Matches the
  current implementation.
- **Scope / AC-003:** `git status --short` shows `spec.md` as the only project-source addition;
  `git diff` under `rateguard/` and `tests/` is empty; `state.json` and `attempts/` are DSD harness
  files outside the allowed-source boundary and not authored by the spec author. `spec.md` exists
  at the project root. AC-001's listed behaviours (return type, when `0.0`, effect on later calls,
  unseen key, clock advance) are all present in the spec.
- Existing suite still passes unedited against the unchanged package:
  `PYTHONPATH=. python3 -m unittest tests.test_rateguard -v` → `Ran 5 tests ... OK`.

## Verification actually performed

- Read `intent.md`, `spec.md`, `rateguard/__init__.py`, `tests/test_rateguard.py`, contract, rules,
  `PLAN.md`, `change-graph.json`; verified the supplied report hash and both artifact hashes.
- `git status --short`; `git diff --stat -- rateguard tests` (empty).
- Ran the existing suite (5 tests, OK).
- Wrote a throwaway spec-faithful `retry_after` subclass in the temp dir
  (`/var/folders/.../opencode/rgreflect/`) and exercised it against the real `RateGuard`/`allow`:
  20,000 randomized trials for R2/R3/R4/R5/purity, a 135-case grid for exact-advance admission,
  a minimal trace, `nextafter` check, clock-base-0 control, and subnormal-rate finiteness checks.
  No project files were written or modified.

## Remaining / boundary

- The defect is in the specification, not in `intent.md` or the package; it is fixable by editing
  `spec.md` alone (allowed source change). No `DECISION_REQUIRED`.
- Predicate left unestablished: none. Whether the reviser adopts limit wording or a
  sufficiency/round-up rule is an ordinary engineering choice; either satisfies the intent, but the
  current wording does not.
