# MLR-C3D-R4-C3 — clean-route field requalification

Frozen before any semantic call, after the provider route was verified through the exact executor
path. A new qualification, not a resumption: `mlr-r4c-deepseek-field-qualification` and
`mlr-r4c2-deepseek-field-qualification` remain frozen with their own outcomes, and neither is
amended.

## 1. Why a new identity

Two things changed since those freezes. The infrastructure condition changed — an outbound firewall
on the host that was interrupting the executor's provider connection has been configured to permit
it, and the route has been verified working. And the held implementation changed: extraction now
checkpoints the executor's write-ahead log, usage is recorded whenever a session exists, and the
file-change allowance introduced while chasing the hang has been dropped.

## 2. Question

> Can the complete MLR measurement path survive real DeepSeek-driven OpenCode execution under the
> held semantic boundary — with the intended treatment-controlled evidence availability, complete
> attribution, independent oracle grading, coherent evidence extraction, and enough task headroom
> for a later paired experiment?

It does not ask whether `full` or `contract` is better, whether source hiding saves context, or
whether runtime introspection substitutes for source. Every observation here is instrument evidence.

## 3. Identity — `mlr-r4c3-deepseek-field-requalification`

| | |
|---|---|
| source | `1f83c3b1f22ab756` |
| task | `eb24429a46ecad4c` |
| public contract | `af3d3e9be15b51ed` |
| oracle | `external_test_v2.py`, `86f17eaf2685ac22` |
| runtime structural identity | `28ba66e1cd49b157` |
| interpreter | CPython 3.9.6, `cpython-39`, magic `610d0d0a` |
| attribution | `mlr-context-5` |
| profile | `profile-1` |
| **semantic boundary** | **`b88bd43109184459`** |
| hermeticity rule | `dcbf34fb63821980` |
| executor | `opencode` 1.18.29, `2f24593f1b8e578d` |
| provider · model | `deepseek` · `deepseek/deepseek-v4-flash` |
| thinking · effort | enabled · `high` |
| role · permissions | implementer · `--auto` |
| price identity | `deepseek-2026-09-09` |

**Boundary rationale.** The selected policy carries no file-change allowance. Two real trajectories
completed under a boundary enforcing exactly this profile text; nothing in the evidence shows the
allowance was ever required. Its digest differs from that historical value only because the rule's
payload gained a field that is off.

## 4. N = 2 pairs — four trajectories

Two independent trajectories per arm exercise the field path repeatedly, including both arm
transitions, at the smallest spend that shows a failure would be reproducible. R4-C3 is instrument
qualification, not effect estimation, so a larger N would buy effect information before the stack
that would measure it is qualified. N is **not** derived from any observed arm difference, and the
previous series produced no completed slot to derive anything from.

## 5. Order — frozen

`full` · `contract` · `contract` · `full`. This gives a `full` → `contract` transition, which is the
shape of the historical leak, and its reverse, which is what would catch integration code that
remembers the last arm. The next arm is never chosen from what the previous one did.

## 6. Lifecycle

Per slot: fresh view · stage arm, runtime, harness, interpreter, credential · hermeticity preflight ·
launch only if clean · execute · checkpoint and extract session and workspace · destroy view · grade
control-side · attribute · profile · audit before the next slot.

## 7. Retry, resume, stop

Established semantics. A failure before a semantic trajectory begins — construction, staging,
preflight refusal, provider unreachability, launcher failure — is an infrastructure attempt, bounded
at three, and may retry the same slot. A trajectory that began is never re-rolled for its outcome.

If an attempt shows provider unreachability, a neutral health probe decides whether to retry; if the
route is unhealthy, the series stops rather than spending slots against an external condition.

Stop the series on: uncontrolled source availability · oracle, reference or prior-sample leakage · a
boundary bypass · a material attribution escape · an uncovered model-visible event · material
unresolved attribution · a contradiction indicating an instrument defect · cross-slot contamination ·
model identity inconsistency · session extraction failure. Do **not** stop for ordinary model
behaviour.

## 8. Credentials

The provider credential file, copied into the constructed home and destroyed with the view. Never
committed, never in an identity, never in extracted evidence.

## 9. Ceiling — $0.40

The previous series spent $0.0321 across substantial activity; four trajectories should cost well
under that again. Checked before each slot with a $0.08 reserve. A trajectory under way is never cut
short for money.

## 10. Pass criteria — frozen

1. Every slot's preflight clean before launch.
2. Real model-driven tool activity inside the view in every completed trajectory.
3. `contract` direct implementation source zero, or causally explained with no uncontrolled source.
4. `full` exposes exactly its declared source; no undeclared copy in either arm.
5. Uncovered model-visible events zero in every session.
6. Material unresolved zero.
7. Material contradictions zero.
8. Oracle runs control-side on every extracted workspace.
9. Session extraction coherent and readable after destruction; attribution and profile consume it
   unchanged.
10. Every view destroyed; no cross-slot residue.
11. No executor state outside any view.
12. Model, boundary and runtime identities stable across all slots.
13. No credential in any retained artefact.
14. **Headroom:** at least one of the four trajectories satisfies the oracle. At N = 4 this detects
    catastrophic model/task incompatibility and nothing finer; it is deliberately not a competence
    estimate.

## 11. Result families

**A** complete path field-qualified · **B** boundary field failure · **C** attribution field failure ·
**D** round-trip failure · **E** oracle integrity failure · **F** model/task headroom failure ·
**G** external infrastructure invalid. No family describes a treatment outcome, because nothing here
can support one.

## 12. What a pass licenses

Freezing the measurement stack and preregistering the paired experiment. Not running it.

---

# Outcome — the complete path is field-qualified

**Four slots, four valid trajectories, four correct, one attempt each, $0.0563 of $0.40.** Record:
[`craft-mlr-r4c3-field-requalification.json`](../../results/craft-mlr-r4c3-field-requalification.json).

## Diagnostics — not treatment-effect evidence

| slot | pair | arm | correct | preflight | direct source | reconstruction | runtime | metadata | calls | tools | session | derived | unresolved | contradictions | uncovered |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | full | yes | clean, 4 declared | 5,630 | 0 | 0 | 5 | 22 | 45 | 98 s | $0.0144 | 0 | 0 | 0 |
| 2 | 1 | contract | yes | clean, 0 declared | **0** | 0 | 1,121 | 3 | 25 | 45 | 114 s | $0.0143 | 0 | 0 | 0 |
| 3 | 2 | contract | yes | clean, 0 declared | **0** | 0 | 418 | 4 | 15 | 34 | 82 s | $0.0108 | 0 | 0 | 0 |
| 4 | 2 | full | yes | clean, 4 declared | 5,630 | 0 | 0 | 9 | 25 | 50 | 139 s | $0.0168 | 0 | 0 | 0 |

**This table is qualification diagnostics and not treatment-effect evidence.** Two trajectories per
arm at an N chosen to observe the path, not to measure a difference. No paired difference is
computed, no effect is estimated, and the fact that all four satisfied the oracle says only that the
model retains competence under the stack — not that either arm caused anything.

## The central question, answered

Real model-driven tool activity occurred inside the boundary in **every** slot: `bash`, `read`,
`edit`, `write`, `todowrite` throughout, plus `grep` in slot 1 and `glob` in slot 3 — the search
routes repaired in R3, exercised naturally in the field for the first time and attributed without
incident. 87 model calls and 174 tool calls in total, no failed tool call.

## Availability

`full` consumed 5,630 bytes of direct source in both slots, every byte with `artifact-path` ancestry
on the `source-file` route into `third_party/objectstore-1.4.0/` — its declared exposure and nothing
else. Four declared exposures, zero undeclared findings.

`contract` consumed **zero** direct implementation source in both slots — and more than that, zero
source-*form* bytes anywhere in either session. Not a classification that came out zero: no
source-shaped text arrived at all. It reached the module's interior through runtime introspection
instead, 1,121 and 418 characters, classified as such.

## Attribution, oracle, round trip

Unresolved **0**, contradictions **0**, uncovered model-visible events **0**, in all four sessions
under an unchanged `mlr-context-5`. Every extracted database re-read cleanly after its view was
destroyed — 94, 65, 88 and 103 items — and `profile-1` reported complete for each. The hidden oracle
ran control-side on every extracted workspace; contract, runtime and vendored copy were unchanged in
all four.

## Environment

Every preflight clean before launch. Every view destroyed; zero stale views, zero the substrate could
not remove. **Zero files in the host executor store modified during or after the series** — the
executor built its state inside each slot and left the evaluator's alone. No `auth.json` in any
extracted artefact and no credential bytes anywhere in the retained evidence.

Boundary identity `b88bd43109184459`, runtime structural identity `28ba66e1cd49b157`, contract
`af3d3e9be15b51ed`, observed model `deepseek-v4-flash` and variant `high` — each single-valued across
all four slots.

## Result family

**A — complete path field-qualified.** All fourteen criteria hold.

One measurement note, recorded rather than smoothed: `full` direct source reads 5,630 bytes here
against 5,822 in the paired series. That is a difference between attribution versions — the whole
delivered rendering is counted under `mlr-context-5` as it was under `mlr-context-3`, but the
components it is taken over changed — and not a change in the fixture, whose source digest is
unmoved. It is not used for anything.
