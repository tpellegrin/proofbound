# DSD Spec Author report — RG-spec (attempt spec-author-3)

Status: COMPLETE.

## Task and posture
- Role: `dsd-spec-author`, contract `runs/r1/contracts/RG-spec.md` (rev r0001), review purpose
  `specification-reflection`.
- Deliverable: `spec.md` at the project root. Allowed source changes: `spec.md` only.
- This is a revision under the same contract, resumed with one exact input: the `spec-reflector-2`
  consistency-reflection report, sha256 `6607ac1c93f5a7fbec554e03dd205c9e0296eeb555564a34122315937f4d5247`
  (recomputed by me; equals the handoff).
- I changed no project file other than `spec.md`. Scratch computation ran in
  `/var/folders/.../T/opencode/rg-spec-author-3/`; the real package was imported read-only.

## Inputs and identities (recomputed by me)
- `intent.md` sha256 = `a7e16b87c8dc8131edd027f289bb5bdcd80bc0fcca02e0827a88646280b70a04` — equals the
  contract's accepted authority. Verified.
- `spec.md` before = `c0c3eb7a94a5e48977ad99c9e552f5b7e3b7b59fceb74b9183760375f7fdd21e` (scope
  baseline). After = `a543a782a02dc7fa9aff51c9b00d5de34e8a1d2648e5d96fb52d9d5e12104757`.
- `rateguard/__init__.py` = `30bb419a...`, `tests/test_rateguard.py` = `858482c1...`, both identical
  to HEAD `bd57018`; `git diff` empty. Existing suite green 5/5
  (`python3 -m unittest discover -s tests`).
- `change-graph.json` still lists only `spec.md`; I did not touch it (outside my boundary).

## Conclusion
The revision closes the one incoherence `spec-reflector-2` found. The exceptional-case predicate in
`spec.md` §5 is now the **whole of requirement 1** — no finite `w` satisfies both §3(a) (the reached
instant admits) and §3(b) (excess `<= 4 * math.ulp(now + w)`) — instead of §3(a) alone. §3, §5 and §7
were adjusted so they remain jointly exhaustive and mutually exclusive, and §0 now states explicitly
that `w*` is the exact real quantity, so §3(b)'s excess is not silently compared against a rounded
floating-point evaluation. No requirement was added, dropped, or re-scoped beyond that. The intent's
factoring remark is still carried as advice in §7.

## What changed, finding by finding

1. **`spec-reflector-2` finding 1 — §5 vs intent 7 predicate mismatch (BLOCKING, now fixed).**
   Intent 7 fires `math.inf` when *no finite delay can satisfy requirement 1*, and requirement 1
   includes both (a) and (b). The old §5 fired only when §3(a) alone was unsatisfiable, so a state
   with (a) satisfiable but (b) unsatisfiable made §3 demand an impossible finite `w` while §5 stayed
   silent. I accepted the reflector's evidence and its one-line fix, and made it coherent:
   - §5 first paragraph: fires iff no finite `w` satisfies requirement 1 (both clauses).
   - §3 opening: returns a delay satisfying **both** (a) and (b) "whenever such a finite `w` exists";
     otherwise §5 applies.
   - §5 explains why the predicate is the whole of requirement 1, not (a) alone, and that the extra
     state is reachable.
   - §7 now says that if even the least admitting delay exceeds the bound, §5 calls for `math.inf`.
2. **`spec-reflector-2` finding 3 — inherited 4-ULP unsatisfiability (root cause).** Not treated as a
   spec defect (the bound is the intent's authority), but it is exactly what makes finding 1 real, so
   the revised §5 now handles it explicitly. The intent's bound is preserved verbatim in §3(b).
3. **`spec-reflector-2` finding 2 — candidate hash `cb93bdf0...` not reproduced.** Outside my allowed
   changes (`spec.md` only); it concerns `change-graph.json`/candidate identity. I did not touch it.
   Noted here for the parent, unchanged.
4. **`spec-reflector-2` finding 4 — out-of-scope items** (backwards clock, query performance, internal
   factoring). No action; they remain out of scope and are not requirements.

## Verification actually performed

- **Recomputed all input hashes**; intent hash equals the accepted authority.
- **Independently reproduced the reflector's witness** with exact rational arithmetic (not the
  reflector's text), using the real `RateGuard` arithmetic:
  - config `capacity=2, refill=0.5189678343212376`, clock from `-1.9412437153089475`; two admissions
    drain the bucket; advance `+0.9221153803261514` → `now = -1.019128334982796`, `tokens = 0.0`,
    `last = -1.9412437153089475`; `allow` refuses.
  - exact real target `t* = last + 1/refill = -0.014342019546032977`; exact real `w* = 1.0047863154367631`.
  - least admitting delay `w = 1.0047863154367631`; reached instant `x = -0.01434201954603287`
    (verified admitted by the real refill arithmetic); excess `w - w* = 1.0719964476435644e-16`;
    `math.ulp(x) = 1.734723475976807e-18`; ratio **61.8**, far above 4.
  - scanning 200,000 `nextafter` steps of larger `w` found **none** that satisfies both (a) and (b),
    so in this reachable state no finite `w` satisfies requirement 1 — §5 must fire.
- **Confirmed the (a)-only overflow instance in §5**: `capacity=1, refill=5e-324`, one admission,
  clock `1000.0` → `(1 - tokens)/refill = inf`, no finite delay admits. True.
- **Confirmed requirement 4 is not broken by the fix**: in the witness configuration the reached
  admitting instant (and hence the finite/inf decision) is a property of the bucket state, not of
  `now`; as `now` advances the answer is `inf` until `now >= t*`, then `0.0` — never an increase.
- **Confirmed scope**: `git diff` empty; only `spec.md` differs from the baseline. I removed the
  `tests/__pycache__/` directory my test run created, restoring the tree to baseline except for the
  allowed `spec.md`.
- **Re-ran the existing suite**: 5/5 `OK` (source unchanged).

## Decisive evidence
- Revised artifact: `spec.md` sha256 `a543a782a02dc7fa9aff51c9b00d5de34e8a1d2648e5d96fb52d9d5e12104757`.
- Witness + exact-rational excess (above); scratch scripts under
  `/var/folders/k3/4xs3wtdd6vdfkvf4d272775c0000gn/T/opencode/rg-spec-author-3/`.
- Scope baseline: `attempts/spec-author-3/scope-baseline.json` (spec `c0c3eb7a...`).

## Decision boundaries / uncertainty
- **Interpretation I resolved (not escalated).** Intent 7's gloss "no wait I can express will get you
  admitted" reads as clause-(a)-only, but its normative sentence ("no finite delay can satisfy
  requirement 1") and its closing line ("requirement 1's guarantee is scoped to the case where a
  finite delay exists") make requirement 1 — (a) **and** (b) — the controlling predicate. I followed
  the normative text, which is also `spec-reflector-2`'s recommended fix. No `DECISION_REQUIRED`:
  the accepted intent dictates the resolution. Residual risk: a later reflector could weigh the gloss
  differently; if the parent prefers the (a)-only predicate, that is an authority change to
  `intent.md`, not a spec fix, and would reintroduce the unsatisfiable §3 state.
- The divergent state needs an admitting instant near zero with `last` far from it (here, a negative
  injected clock). Neither document restricts the clock's domain, so the state is legitimate; if the
  parent were to rule negative clocks out of scope, the §5 predicate would be vacuously equivalent to
  (a)-only on the remaining domain. I did not invent such a restriction.

## What remains
Nothing for this attempt. The report and `spec.md` are current and self-contained. Fresh independent
reflection is required before this revision can be treated as accepted.
