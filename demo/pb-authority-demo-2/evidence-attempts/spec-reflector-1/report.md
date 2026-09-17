# DSD Spec Reflector report — RG-spec (attempt spec-reflector-1)

Status: COMPLETE — no blocking findings.

## Task and posture
- Role: `dsd-spec-reflector`. Contract: `runs/r1/contracts/RG-spec.md` (rev r0001).
- Independent adversarial review of one candidate specification artifact against the accepted intent.
  Project-read-only: I changed no project file; scratch checks ran only in the OS temp dir.
- Candidate artifact: `/Users/thiago/.proofbound/demo2/live/project/spec.md`
  sha256 `c0c3eb7a94a5e48977ad99c9e552f5b7e3b7b59fceb74b9183760375f7fdd21e`.
- Authority: `intent.md` sha256 recomputed as
  `a7e16b87c8dc8131edd027f289bb5bdcd80bc0fcca02e0827a88646280b70a04`, equal to the contract's
  accepted authority.
- Exact input `attempts/spec-author-2/report.md` sha256 recomputed as
  `d2c58ff342639c1306a84e9db061bf652e8f72e8dc51bbaef1ed7535f74aa2ab`, equal to the supplied value.

## Conclusion
The specification is a faithful, implementable, and judgeable restatement of the intent's seven
numbered requirements. It keeps the delicate requirement 1 about the reached instant rather than a
formula, carries the refill-arithmetic note as explicitly non-normative advice, states what must not
change, and asserts nothing I found to be false of the arithmetic it references. No `DECISION_REQUIRED`.
I have no blocking findings; the observations in "Defects / uncertainty" are non-blocking.

## Work and findings

### Requirement coverage (intent's seven)
- intent 1 (usable wait, 4-ULP excess bound) → §3. The promise is stated about `x = now + w`, "a
  single Python float addition", and the excess bound is `w - w* <= 4 * math.ulp(x)`. §3 also says
  explicitly that a delay equal to the exact real wait need not admit, and that a formula's result
  must be validated against the reached instant. This is the failure mode the contract warns about;
  the spec avoids it. The exact real wait `w*` appears only as a reference quantity (§0), not as the
  required return.
- intent 2 (query, not a call) → §1. Purity stated: consumes no token, creates no bucket, changes no
  later result; once or a hundred times.
- intent 3 (agreement with `allow`) → §2. "`== 0.0` exactly when `allow(key)` would be admitted",
  both directions spelled out, at the same sampled instant.
- intent 4 (waiting only helps) → §4. Non-increasing as the clock advances, decreasing toward `0.0`
  and staying there; jumps allowed.
- intent 5 (unseen key) → §2. Full bucket, returns `0.0`.
- intent 6 (`allow` unchanged) → §6. `allow`'s behaviour, per-key independence, burst, refill, and
  state writes on refusal all preserved; existing suite must pass unedited.
- intent 7 (exceptional case) → §5. Returns `math.inf`, not raises, when no finite delay exists;
  guarantee scoped accordingly.

### Acceptance-criteria check (contract)
- AC-001 (return type; when `0.0`; what waiting guarantees; excess bound; effect on later calls;
  unseen key; clock advance; exceptional case): all present — §1, §2, §3, §4, §5.
- AC-002 (states what must not change): §6, plus the "What must not change" bullets.
- AC-003 (nothing asserted false): checked below.
- AC-004 (no file other than `spec.md` modified): verified below.

### Arithmetic and repository checks actually performed
- `w*` definition (§0): correct. For a refused key (`tokens < 1 <= capacity`), exact token count
  `tokens + δ*refill` reaches `1` at `δ = (1 - tokens)/refill`; the cap cannot bind before that.
  `w* = max(0, (last + (1 - tokens)/refill) - now)` is therefore the least non-negative real delay.
- Four-ULP bound satisfiability: I independently searched for states where the smallest admitting
  float instant exceeds the exact real target by more than four ULP, using the repository's own
  `allow` arithmetic and exact-rational (`fractions.Fraction`) targets.
  - 200,000 and 300,000 randomised states across capacity `{1,2,3,1e3,1e6,1e12}`, refill
    `1e-308..1`, clocks `{0,1,1000,1e6,1e12}`, including deficits down to `1e-16`: worst observed
    excess ≈ 1.42 ULP; **zero** cases over 4 ULP. The author's independent 40,000-state figure
    (≈1.25 ULP) is consistent.
  - Targeted tiny-deficit / tiny-refill cases (`refill` down to `1e-30`, deficits down to `1e-15`):
    the admitting instant was often *below* the exact real target (negative excess), never above it
    by more than ~1 ULP. So the bound is not merely asserted; I could not falsify it.
- Monotonicity (intent 4) feasibility: for fixed bucket state and strictly increasing clock, the
  "smallest non-negative `w` whose reached instant admits" is non-increasing. 5,000 configurations ×
  300 advancing instants produced **0** violations. So §3 and §4 are jointly satisfiable by a natural
  construction, even though the spec prescribes none.
- Exceptional case (§5): confirmed `1/5e-324`, `1/1e-320`, `1/1e-310` overflow to `+inf` while
  `1/1e-300` is finite, matching the spec's measured instance and scoping.
- Intent's two counterexamples re-derived against `allow` semantics: for `capacity=2`,
  `refill=1.3`, clock `1000.0`, drained, both delay `0.7692307692307692` and its `nextafter` upward
  reach instant `1000.7692307692307` and are refused; for `capacity=1`, `refill=0.09`, clock `0.0`,
  one admission, delay `11.11111111111111` is refused. The spec's claim that the promise is about
  the instant, not the formula, is well-founded.
- Scope (AC-004): `git status --porcelain` shows `spec.md`, `change-graph.json`, and
  `DeepSeekAndDestroy/` as the only untracked additions; `git diff` against the initial commit is
  empty for `rateguard/` and `tests/`. `spec.md` is at the project root. No source file was modified.

## Decisive evidence
- `spec.md` sha256 `c0c3eb7a94a5e48977ad99c9e552f5b7e3b7b59fceb74b9183760375f7fdd21e`; `intent.md`
  sha256 matches the contract.
- Scratch results: worst 4-ULP ratio 1.42 over 500,000 states, zero over-4; zero monotonicity
  violations over 1.5M advancing-clock samples.
- `rateguard/__init__.py` and `tests/test_rateguard.py` unmodified relative to `HEAD`.

## Defects / uncertainty / decision boundaries
Non-blocking observations, recorded for truth rather than as required fixes:
1. §5 scopes the exceptional case to "no finite float `w` satisfies §3(a)". The intent says
   `math.inf` when "no finite delay can satisfy requirement 1", and requirement 1 includes the
   four-ULP bound (b). My searches found no state where (a) is satisfiable but (b) is not, so the two
   readings coincide in everything I could test; still, the strict reading of §5 is slightly narrower
   than the intent. A reviser could align §5 to "§3(a) and §3(b)" at no cost.
2. The universal satisfiability of the four-ULP bound is inherited from the intent and is
   empirically supported but not proved. The missing predicate is: "for every refused reachable
   state in which some finite admitting `w` exists, one exists within four ULP of `w*`." This is not
   a defect introduced by the spec; the spec restates the intent's own bound.
3. Out of scope and left unspecified by both intent and spec: clock going backwards (existing
   `allow` clamps negative elapsed), and performance of the query. The intent does not constrain
   these, so this is acceptable.

## What remains
- Nothing for this attempt. The report and artifact assessment are current; no project state was
  changed by this reflector.
