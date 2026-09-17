# DSD Spec Reflector report — RG-consistency (attempt spec-reflector-2)

Status: COMPLETE.

## Task and posture
- Role: `dsd-spec-reflector`, contract `runs/r1/contracts/RG-consistency.md` (rev r0001), purpose
  `consistency-reflection`.
- Question: do the accepted external intent (`intent.md`) and the accepted specification
  (`spec.md`), taken together, describe **one** consistent change implementable without
  contradiction? This is a joint judgment, not a re-review of either artifact alone.
- Project-read-only: I changed no project file. All scratch computation ran in the OS temp dir
  (`/var/folders/.../T/opencode/rg-consistency/`); I imported the real package read-only.
- **Single-member caveat (required honesty note):** the contract's candidate
  `cb93bdf09ea2e212fb2cdd8fe7e27edad8fb5bdc9f4ed48afd30fa8c7c2ebf1b` has exactly one member.
  `change-graph.json` lists only `spec.md`. So "coherence" here is only intent↔spec, not coherence
  among several artifacts; a multi-artifact change would raise questions (interface boundaries,
  ordering, shared assumptions) that cannot arise for a single-member candidate.

## Inputs and identities (recomputed by me)
- `intent.md` sha256 = `a7e16b87c8dc8131edd027f289bb5bdcd80bc0fcca02e0827a88646280b70a04` — equals the
  contract's accepted authority. Verified.
- `spec.md` sha256 = `c0c3eb7a94a5e48977ad99c9e552f5b7e3b7b59fceb74b9183760375f7fdd21e`; this is the
  single candidate member per `change-graph.json`
  (`c520b40fd335ddb5bdca67e8b7a558e4d651ff00fdab86d7d6ed58c937fe9698`, artifact `spec.md`).
- `rateguard/__init__.py` and `tests/test_rateguard.py` are unmodified relative to `HEAD`
  (`bd57018`); the only untracked additions are `spec.md`, `change-graph.json`, and
  `DeepSeekAndDestroy/`. The existing suite runs green: 5/5 `OK`.

## Conclusion
The intent and the specification **cohere in substance** and describe one implementable change.
The spec is a faithful, requirement-by-requirement restatement of the intent's seven numbered
points; it adds no requirement the intent does not support, keeps the delicate requirement 1
phrased about the reached instant, and carries the factoring remark as explicitly non-normative
advice. Across the practically relevant clock domain (non-negative clock values) I found **no**
behavioral divergence.

I did find **one narrow but real incoherence**, at the exceptional-case boundary:

> **Intent requirement 7 and spec §5 scope `math.inf` by different predicates.** Intent 7 returns
> `math.inf` when *no finite delay satisfies requirement 1* — and requirement 1 includes both the
> "the wait works" clause (a) and the four-ULP excess bound (b). Spec §5 returns `math.inf` only
> when *no finite `w` satisfies §3(a)* alone. Whenever §3(a) is satisfiable but §3(b) is not, the
> two documents demand different results, and the spec becomes unsatisfiable in that state: §3
> requires a finite `w` satisfying both (a) and (b), while §5 does not fire. This is reachable —
> I exhibit a witness below. **Actionable fix (one line):** make §5 fire when no finite `w`
> satisfies §3(a) **and** §3(b), matching intent 7.

This is not a failure of direction. The direction is right and the spec is otherwise sound; the
defect is a boundary-scoping mismatch a reviser can close exactly. I did **not** issue a
`DECISION_REQUIRED`, because the correct resolution is dictated by the accepted intent.

## What I checked, together, and the evidence

### Joint requirement mapping (intent ↔ spec)
| Intent | Spec | Joint reading |
|---|---|---|
| 1 usable wait; 4-ULP bound | §0, §3(a)(b) | consistent; bound one-sided as in intent |
| 2 query not call | §1 | consistent (no token, no bucket, no later effect) |
| 3 agrees with `allow` | §2 | consistent (same-instant, both directions) |
| 4 waiting only helps | §4 | consistent (non-increasing, jumps allowed) |
| 5 unseen key | §2 | consistent (0.0, full bucket, no bucket created) |
| 6 `allow` unchanged | §6 | consistent (signature, validation, suite unedited) |
| 7 no finite delay → `inf` | §5 | **mismatch** — see below |

The mapping is explicit in `spec.md`'s own header and holds on inspection. I found no place where
the spec invents a requirement, drops one, or contradicts the intent in the non-negative domain.

### The §5 vs intent-7 divergence, demonstrated
A state where §3(a) is satisfiable but §3(b) is not. Reproduce with the real package:

```
clock starts at c0 = -1.9412437153089475
g = RateGuard(capacity=2, refill_per_second=0.5189678343212376, clock=clock)
g.allow("k") -> True   # tokens 2 -> 1
g.allow("k") -> True   # tokens 1 -> 0
advance clock by 0.9221153803261514  -> now = -1.019128334982796
stored state: tokens = 0.0, last = -1.9412437153089475
```

- `allow("k")` at `now` refuses (refilled count `0.9221*0.51897 = 0.4785 < 1`).
- Exact real target `t* = last + 1/refill = -0.014342019546032…`; `w* = t* - now = 1.0047863…`.
- Smallest admitting delay: `w = 1.0047863154367631`; reached instant
  `x = now + w = -0.01434201954603287` admits.
- Excess `w - w* = 1.0719964476435644e-16`; `math.ulp(x) = 1.734723475976807e-18`;
  `excess / ulp(x) = 61.8`, far above the allowed 4.
- The minimal admitting `w` is the best possible (larger `w` only increases the excess, since
  `4*ulp(x)` grows ~`4ε·Δw` while the excess grows `Δw`; smaller `w` does not admit — checked by
  stepping `nextafter` down 5000 times, none admit).

So in this reachable state **no finite `w` satisfies §3(a) and §3(b)**. Intent 7 then says return
`math.inf`; spec §5 does not fire (§3(a) *is* satisfiable), so spec §3 demands an impossible
finite `w`. That is the incoherence.

- The witness needs a **negative** injected clock: the admitting instant crosses zero, where
  `ulp(x)` is smallest, so a sub-`ulp(w)` excess in delay becomes tens of `ulp(x)`. `allow` itself
  handles negative clocks fine (it clamps negative `elapsed`), and neither intent nor spec restricts
  the clock's domain, so the state is legitimate under both documents. I flag the negative-clock
  dependence so the parent can judge scope; if negative clocks are ruled out of scope, the
  divergence becomes vacuous and the two artifacts cohere as-is.
- In the **non-negative** clock domain the predicates coincide in everything I could test: a
  400,000-state randomized search over capacities `{1,2,3,10,1000}`, refills `1e-11…1e4`, clocks
  `{0,0.5,1,2,10,1000,1e6,1e9,1e12}`, deficits to sub-1e-1, checking the *minimal admitting* delay
  (the best case), found worst excess `≈1.48 ULP`, zero over 4. This agrees with the accepted
  `spec-reflector-1` report (worst `≈1.42` over 500k) and the author's `≈1.25` over 40k.

### Cross-checks against real repository state
- The two counterexamples the intent records are reproduced by the real `allow` arithmetic:
  - `capacity=2, refill=1.3, clock=1000.0`, drained: exact `w*=0.7692307692307692` and its upward
    `nextafter` reach `1000.7692307692307` and refuse; smallest admitting delay
    `0.7692307692308304` reaches `1000.7692307692308`.
  - `capacity=1, refill=0.09, clock=0.0`, one admission: delay `11.11111111111111` refuses;
    smallest admitting `11.111111111111112`.
  This confirms the intent's central claim that the promise must be about the reached instant, which
  the spec faithfully preserves.
- Requirement 6 baseline: the unedited suite passes 5/5 against the unchanged source.
- `spec.md` prescribes no internal structure and its §7 repeats the intent's factoring remark as
  advice, not requirement — consistent with intent's "note on how".

## Defects / uncertainty / decision boundaries
1. **The named incoherence above** (spec §5 scope vs intent 7). Blocking only if the parent wants
   exact boundary agreement; the fix is one line and dictated by the intent.
2. **Candidate hash not reproduced.** I could not derive
   `cb93bdf09ea2e212fb2cdd8fe7e27edad8fb5bdc9f4ed48afd30fa8c7c2ebf1b` from `spec.md`,
   `change-graph.json`, `intent.md`, or simple canonical concatenations/serializations. The member
   identity is independently established (`change-graph.json` lists only `spec.md`; its hash is
   stable across all scope baselines), so this does not affect the coherence judgment, but the
   candidate-hash predicate remains unestablished from the artifact side.
3. **Inherited, not spec-introduced:** the intent's own 4-ULP bound is unsatisfiable in the same
   negative-clock states. The spec inherits this; it is the intent's authority, so I did not treat
   it as a spec defect. It is, however, the root cause of the §5 divergence and worth the parent's
   awareness.
4. Out of scope in both documents and therefore not incoherence: backwards clock movement, query
   performance, and any internal factoring choice.

## What remains
Nothing for this attempt. No project state was changed by this reflector; the report is current and
self-contained. If the parent wants strict intent↔spec agreement, revise `spec.md` §5 to fire on
"no finite `w` satisfies §3(a) and §3(b)"; no other change is indicated.
