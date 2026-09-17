# DSD Spec Reflector report — RG-spec (attempt spec-reflector-3)

Status: COMPLETE. Verdict: **not accepted** — one blocking finding. The candidate specification is
not sound enough to build on as written: it mandates an answer that contradicts intent requirement 4
in a reachable state.

## Task and posture
- Role: `dsd-spec-reflector`, contract `runs/r1/contracts/RG-spec.md` (rev r0001), review purpose
  `specification-reflection`.
- Candidate artifact: `spec.md` at project root, sha256
  `a543a782a02dc7fa9aff51c9b00d5de34e8a1d2648e5d96fb52d9d5e12104757` (8234 bytes).
- Author report (exact input): `attempts/spec-author-3/report.md`, sha256
  `d725b0d1c663d16882a7ec3cbdc6338f2cd00b40f5a140e855a1b79311d228d4` (recomputed by me; matches
  the handoff).
- Project-read-only. I modified no project file. Scratch scripts live under
  `/var/folders/k3/4xs3wtdd6vdfkvf4d272775c0000gn/T/opencode/rg-spec-reflector-3/`; the real
  `rateguard` package was imported read-only.

## Input identities (recomputed by me)
- `intent.md` sha256 = `a7e16b87c8dc8131edd027f289bb5bdcd80bc0fcca02e0827a88646280b70a04` — equals the
  contract's accepted authority. Verified.
- `spec.md` = `a543a782...` — equals the scope-baseline and the author's post-state. Verified.
- `change-graph.json` = `c520b40f...`; `rateguard/__pycache__/__init__.cpython-314.pyc` =
  `b98a03ae...`; `git diff` empty; project tree unchanged from the attempt scope-baseline. Verified.

## Conclusion
The spec's §5 reads intent 7 as firing when **no finite `w` satisfies the whole of requirement 1**
(clause (a) *and* clause (b)). Under that reading, §3 *mandates* a finite positive delay at any
instant where such a `w` exists, while §5 mandates `math.inf` at any later instant where none exists.
I found a reachable bucket state and two instants `now_A < now_B`, 1e-7 s apart, where the spec's
own predicate flips from "a finite valid `w` exists" to "none exists". The spec therefore mandates
`finite -> math.inf` as the clock advances, which **increases**, contradicting §4 and intent
requirement 4. The author report's monotonicity claim ("the finite/inf decision is a property of the
bucket state, not of `now` ... never an increase") is false; it held only for the single witness the
author sampled.

This is not a formatting or wording objection. Either the spec's requirement-7 predicate must be
clause-(a)-only (matching intent 7's own gloss, "no wait I can express will get you admitted"), with
§3(b) stated as a best-effort bound for the states where it is unsatisfiable; or the parent must rule
that intent 1(b), 4 and 7 conflict — an authority decision. The current artifact does neither and
asserts consistency it does not have.

## What I actually checked (and found true)
All computations below were done against the real `rateguard.RateGuard.allow` arithmetic, using exact
`fractions.Fraction` for the excess comparison (float arithmetic is lossy at this scale). Scripts:
`check_witness.py`, `check_exact.py`, `check_monotone.py`, `check_search2.py`, `verify_clean.py`.

1. **Intent's measured counterexamples reproduce.**
   - cap=2, refill=1.3, clock 1000.0, two admissions: exact wait `0.7692307692307692` refuses;
     `math.nextafter(w, inf)=0.7692307692307693` reaches the *same* instant `1000.7692307692307`
     and also refuses. Least admitting delay `0.7692307692307737`, excess `4.51e-15` <=
     `4*ulp=4.55e-13`. Matches intent.
   - cap=1, refill=0.09, clock 0.0, one admission: exact wait `11.11111111111111` refuses. Least
     admitting delay `11.111111111111112`, excess `9.70e-16` <= `7.11e-15`. Matches intent.
2. **The author's §5 reachability witness is true.** cap=2, refill=0.5189678343212376, clock from
   -1.9412437153089475, two admissions, advance +0.9221153803261514: exact `w* = 1.0047863154367631`
   (Fraction `10576298551527075838333051637875/10525918186823378652560992763904`), least admitting
   `w = 1.0047863154367631`, reached `x = -0.01434201954603287`, exact excess
   `1.0719964476435644e-16` vs `4*ulp(x) = 6.938893903907228e-18` — ratio 61.8, bound violated.
   So the (b)-only inf state is genuinely reachable, as §5 asserts.
3. **The (a)-only overflow instance is true.** cap=1, refill=5e-324, one admission, clock 1000.0:
   `(1-tokens)/refill` overflows to `inf`; no finite delay admits.
4. **Requirement-3 agreement and §2 restatement are consistent** with the real `allow` predicate in
   every state I sampled (admission at the reached instant verified with the real package).

## Blocking finding — §5/§3 mandate a non-monotone answer (contradicts §4 / intent 4)

**Reachable state.** `RateGuard(capacity=2, refill_per_second=0.10978710655568508, clock=...)`,
inject a clock reading `-7.155015362133442`, call `allow("a")` twice (both admitted). Stored bucket:
`tokens = 0.0`, `last = -7.155015362133442`. The constructor accepts this; the injected clock's
domain is unrestricted (the spec itself says so in §5).

Take two instants 1e-7 s apart (both refused by `allow`):

- `now_A = -7.155009762133426`
  - least admitting delay `w_A = 9.108532108777203`; reached `x_A = now_A + w_A = 1.9535223466437763`
    (verified: real `allow` at `x_A` admits).
  - exact real `w*_A = 2535299641733509378336650836351/278343383045269533029977554944`.
  - exact excess `w_A - w*_A = 784551047605119/1113373532181078132119910219776 = 7.046611266824333e-16`.
  - `4*ulp(x_A) = 1/1125899906842624 = 8.881784197001252e-16`. **Within bound.** A finite `w`
    satisfying requirement 1 exists, so §3 mandates a finite positive delay.
- `now_B = -7.155009862133427` (1e-7 later)
  - least admitting delay `w_B = 9.108532208777204`; reached `x_B = 1.9535223466437772`
    (real `allow` at `x_B` admits).
  - exact real `w*_B = 20282397356542782087358457487151/2226747064362156264239820439552`.
  - exact excess `w_B - w*_B = 3546850783907311/2226747064362156264239820439552 = 1.5928395463825586e-15`.
  - `4*ulp(x_B) = 8.881784197001252e-16`. **Bound violated.** No finite `w` satisfies requirement 1:
    `excess(w) - 4*ulp(now+w)` increases with `w` (slope `1 - ~4*2^-52`), so if the least admitting
    delay exceeds the bound, every larger delay does too; I additionally scanned 5,000,000
    `nextafter` steps upward and found none. §5 mandates `math.inf`.

`allow` refuses at both instants. So with no intervening calls, the spec-mandated value goes from a
finite positive delay at `now_A` to `math.inf` at `now_B` — an increase, violating §4 ("the returned
value never increases as the clock advances") and intent requirement 4. The predicate oscillates
`finite/inf` at nearly every 1e-7 step across this region; a dense forward scan
(`verify_nonmonotone.py`) shows dozens of `finite -> inf` transitions.

**Root cause.** §5 includes clause (b) in its predicate. Clause (b) is a comparison of an exact real
excess against `4*ulp(now+w)`, which is sensitive to floating-point rounding in the refill product
and in `w` itself; that sensitivity makes "exists a finite `w` satisfying (a) and (b)" non-monotone
in `now`, even though "exists a finite `w` satisfying (a)" is monotone (the admitting instant is
fixed by the bucket state). Including (b) is exactly what creates the contradiction.

**Scope of the state.** The violation needs the admitting instant near zero while `last` is far from
it, which here means a negative absolute clock reading. The intent does not restrict the clock's
domain, and §5 explicitly declares such instants legitimate; so the defect is inside the domain the
spec claims. If the parent were to rule negative clock readings out of scope, §5's (b) predicate
would be vacuous on the remaining domain — but that is an authority change, not something the spec
may assume silently.

**Actionable resolution (a reviser can act on this).** One of:
- (Preferred, matches intent 7's gloss) Make §5 fire only when **no finite delay reaches an admitting
  instant at all** (clause (a) unsatisfiable). Then state §3(b) as a bound that is honoured whenever
  it can be — in the states where the least admitting delay exceeds it, the least admitting delay is
  returned rather than `math.inf`. This restores monotonicity and keeps requirement 4. It does mean
  requirement 1(b) is not literally met in those states, so the spec must say so plainly instead of
  claiming requirement 1 is fully satisfied everywhere.
- Or, if the parent holds that requirement 7's "no finite delay can satisfy requirement 1" includes
  clause (b) and is normative, then requirements 1(b), 4 and 7 are mutually inconsistent for
  reachable states, and the correct worker action is a bounded `DECISION_REQUIRED` to the parent —
  not a spec that asserts requirement 4 is preserved.

Either way, the author's stated resolution ("requirement 4 is not broken by the fix") cannot stand.

## Non-blocking observations
- The author report's monotonicity argument checked only the single witness configuration, where the
  transition happens to be `inf -> finite -> 0`. A single config is not enough; the oscillation above
  is config-dependent.
- §1's "creates no bucket for an unseen key" is stronger than intent 2 requires (intent 2 only
  forbids changing later observable results) and is not observable. Harmless, but it is an internal
  constraint presented in a behaviour spec.
- Requirement map, signature/return-type, unseen-key, purity, "what must not change", and the advice
  separation all read faithfully against intent. The intent's factoring note is carried as advice in
  §7, correctly.

## Decisive evidence
- Candidate: `spec.md` sha256 `a543a782a02dc7fa9aff51c9b00d5de34e8a1d2648e5d96fb52d9d5e12104757`.
- Reproduction (scratch): `verify_clean.py` prints the two instants, exact excesses, bounds, and the
  5,000,000-step upward scan finding no valid `w`; `verify_nonmonotone.py` prints the dense forward
  `finite <-> inf` transitions; `check_exact.py` reproduces the author witness; `check_witness.py`
  reproduces the intent counterexamples. All under
  `/var/folders/k3/4xs3wtdd6vdfkvf4d272775c0000gn/T/opencode/rg-spec-reflector-3/`.
- Scope baseline unchanged: `spec.md`/`change-graph.json`/pyc hashes identical to
  `attempts/spec-reflector-3/scope-baseline.json`; `git diff` empty.

## Uncertainty / what remains
- I did not attempt to determine which resolution the parent will prefer; that is the authority
  question the finding turns on.
- I verified the two instants and the oscillation region by direct computation and by a randomized
  sweep (4000 configs, 240,000 points, all `finite -> inf` transitions concentrated in the
  near-zero-admitting-instant regime). I did not prove the impossibility of any monotone
  interpretation of the (a)&(b) predicate; the evidence shows the spec's own predicate is
  non-monotone, which is sufficient for the finding.
- Fresh reflection on a revised `spec.md` is required before this task can be treated as accepted.
