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
