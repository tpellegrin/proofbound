# MLR-C3D-R4-C — DeepSeek field qualification of the complete measurement path

Frozen before any provider call. **This is not the modularity experiment.** It buys four semantic
trajectories to observe one thing: whether the complete measurement path behaves as mechanically
predicted when a real model drives the real executor inside the constructed evidence boundary.

## 1. Question

> When DeepSeek drives OpenCode inside the completed semantic boundary, does treatment-controlled
> evidence availability hold, does every model-visible representation remain explainable under
> `mlr-context-5`, does the unchanged hidden oracle judge the result, and does current-slot evidence
> extract and profile?

It does **not** ask whether `contract` is cheaper, whether `full` is better, whether source hiding
reduces context, or what N the real experiment should use. Every result here is instrument
qualification evidence and none of it may be read as treatment-effect evidence.

## 2. The held stack

| | |
|---|---|
| source digest | `1f83c3b1f22ab756` |
| task | `eb24429a46ecad4c` |
| public contract | `af3d3e9be15b51ed` |
| oracle | `external_test_v2.py`, `86f17eaf2685ac22` |
| runtime structural identity | `28ba66e1cd49b157` |
| interpreter | CPython 3.9.6, `cpython-39`, magic `610d0d0a` |
| attribution | `mlr-context-5` |
| profile | `profile-1` |
| semantic-boundary identity | `d8bbe1ce9941d217` |
| hermeticity-rule identity | `dcbf34fb63821980` |
| executor | `opencode` 1.18.29, `2f24593f1b8e578d` |
| provider / model | `deepseek` / `deepseek/deepseek-v4-flash` |
| thinking · effort | enabled · `high` |
| role · permissions | implementer · `--auto` |
| price identity | `deepseek-2026-09-09` |

The fixture *tree* digest has moved since the invalid paired run because derived regression fixtures
were added beneath it. Every identity the arms are built from — source, task, contract, oracle,
runtime — is unchanged, and each is bound above by its own digest rather than by the tree's.

## 3. Qualification identity

`mlr-r4c-deepseek-field-qualification`. New, and not a resumption of anything: not the Nemotron
series, not the invalid DeepSeek paired series, not the R2 or R3 qualifications. The execution
boundary is now part of the qualified configuration, which is why none of those identities can
cover it.

## 4. N = 2 pairs — four trajectories

R4-C qualifies integration and instrumentation rather than estimating a treatment effect. Two
independent trajectories per arm give repeated field execution through both evidence surfaces at the
smallest spend that can show a failure is reproducible rather than a one-off. Any treatment-effect
inference is prohibited, so a larger N would buy effect information before the stack that would
measure it has been field-qualified.

Three pairs were considered and rejected: the routes a third pair might add — search, help, temporary
files, reconstruction — are already covered deterministically by the retained corpus and by R4-B's
regressions, and §86 of this design is explicit that R4-C is not an attempt to hit every mechanism
probabilistically.

**N is not derived from any observed arm difference, here or in any previous series.**

## 5. Order

Generated before execution and frozen:

| slot | pair | arm |
|---|---|---|
| 1 | 1 | `full` |
| 2 | 1 | `contract` |
| 3 | 2 | `contract` |
| 4 | 2 | `full` |

This exercises a `full` → `contract` transition — the shape of the historical failure — and its
reverse. The next arm is never chosen from what the previous one did.

## 6. Slot lifecycle

Per slot, without exception: construct a fresh view · stage the arm, runtime, harness, interpreter
and credential · run the hermeticity preflight · launch only if clean · execute · extract the
workspace and session · destroy the view · grade control-side · attribute · profile.

Fresh per slot: semantic root, `home`, `tmp`, `data`, `session`, workspace, preflight. A previous
clean slot proves nothing about the next one.

## 7. Retry, resume and failure

Established semantics, unchanged. A failure **before** a semantic trajectory begins — view
construction, staging, preflight refusal, provider unavailability, launcher failure — is an
infrastructure attempt and may retry the same slot, bounded at three. A trajectory that **began** is
never re-rolled: not for an incorrect implementation, not for an unexpected tool path, not for token
use, not for how much of anything it read.

## 8. Credentials

The provider credential file, copied into the constructed home at
`.local/share/opencode/auth.json` and destroyed with the view. Nothing else: no host home, no other
provider, no shell environment, no git credential. The secret is never written to a committed
artefact, a result record, an identity or a log. It is readable by the subject inside its own home,
as it must be for the executor to authenticate, and that is stated rather than concealed.

## 9. Cost ceiling — $0.40

Derived from what DeepSeek field runs have actually cost: $0.0124 to $0.0596 per trajectory. Four at
the observed maximum is $0.24; the ceiling is **$0.40**, checked before launching each slot with a
reserve of $0.08 — above the largest single run yet seen. A trajectory already under way is never cut
short for money; the ceiling governs whether the next one starts. The provider health probe is
accounted separately.

## 10. Provider health

One minimal call before the series: same provider, same requested model, same effort, a separate
session, a neutral prompt, no fixture or task or arm information. If it fails, the series does not
begin — no substitution of model, provider or effort, and no slot consumed.

## 11. Pass criteria — frozen

1. Every slot's preflight is clean before launch.
2. Actual model-driven tool activity is observed inside the view in at least one trajectory.
3. `contract` direct implementation-source is zero; if nonzero, causal ancestry shows no
   uncontrolled source reached it.
4. `full` exposes exactly its declared source; no undeclared copy appears in either arm.
5. Uncovered model-visible events: zero in every session.
6. Material unresolved attribution: zero.
7. Material contradictions: zero.
8. The hidden oracle runs control-side on every extracted workspace.
9. Session extraction succeeds and unchanged attribution and profile consume it.
10. Every view is destroyed and no cross-slot residue survives.
11. No OpenCode state is created outside the view.
12. Model identity, boundary identity and runtime structural identity are stable across all slots.
13. No credential appears in any retained artefact.
14. **Headroom:** at least two of the four trajectories satisfy the oracle, with at least one in each
    arm. This is a weak test at N = 4 and is meant to catch collapse, not to measure competence.

## 12. Stop conditions

Stop the series, preserve the evidence, and repair under a new identity, on any of: uncontrolled
source availability · oracle, reference or prior-sample leakage · a boundary bypass · a material
attribution escape · an uncovered model-visible event · material unresolved attribution · a
contradiction indicating an instrument defect · cross-slot contamination · model identity
inconsistency · session extraction corruption.

**Do not stop** for ordinary model behaviour: unexpected commands, `contract` disassembling the
runtime, `full` ignoring its source, helper scripts, inefficiency, an incorrect implementation, or
token use.

## 13. Result families

**A. Field path qualified** — every instrumentation and environment requirement holds and headroom
remains. **B. Boundary field failure.** **C. Attribution field failure.** **D. Evidence round-trip
failure.** **E. Oracle integrity failure.** **F. Model/task headroom failure.** **G. Infrastructure
invalid.**

There is deliberately no family for a treatment outcome. Nothing here can support one.

## 14. What a pass licenses

Exactly one thing: freezing a new full paired experiment under the qualified stack. Not running it.
