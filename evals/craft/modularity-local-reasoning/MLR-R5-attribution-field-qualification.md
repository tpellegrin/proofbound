# MLR-C3D-R5-Q — live field qualification of `mlr-context-6`

Frozen before any semantic call. A new qualification identity, not a resumption:
`mlr-r4c3-deepseek-field-requalification` keeps its own outcome and is not amended, and
`mlr-deepseek-v4-flash-high-paired-r4` remains permanently invalid.

## 1. Why a new identity

Exactly one scientifically relevant thing has changed since the boundary was field-qualified:
attribution moved from `mlr-context-5` to `mlr-context-6`. Content no longer establishes that source
was read, and ancestry of content covers only the spans that replay it. That repair passed 19
deterministic adversarial cases and a retrospective replay of 54 retained sessions, and neither of
those is live execution.

**Nothing else changed.** `_semantic_view.py`, `_mlr_boundary.py` and `_hermetic.py` carry no commit
since the paired experiment was frozen at `4fd218e`; the operative boundary identity is
`b88bd43109184459`, recovered exactly, and the hermeticity rule is unchanged.

## 2. Question

> Do the repaired attribution semantics survive fresh, model-driven OpenCode/DeepSeek trajectories
> under the already-qualified semantic execution boundary — recognising genuine source provenance
> where it exists, and refusing to invent it where it does not?

It does not ask whether `full` or `contract` is better, and it cannot. Every number here is
instrument evidence.

## 3. Identity — `mlr-r5-deepseek-attribution-field-qualification`

| | |
|---|---|
| source | `1f83c3b1f22ab756` |
| task | `eb24429a46ecad4c` |
| public contract | `af3d3e9be15b51ed` |
| oracle | `external_test_v2.py`, `86f17eaf2685ac22` |
| runtime structural identity | `28ba66e1cd49b157` |
| interpreter | CPython 3.9.6, `cpython-39`, magic `610d0d0a` |
| **attribution** | **`mlr-context-6`** |
| profile | `profile-1` |
| semantic boundary | `b88bd43109184459` |
| hermeticity rule | `dcbf34fb63821980` |
| executor | `opencode` 1.18.29, `2f24593f1b8e578d` |
| provider · model | `deepseek` · `deepseek/deepseek-v4-flash` |
| thinking · effort | enabled · `high` |
| role · permissions | implementer · `--auto` |
| credential | provider auth file staged into the constructed home, destroyed with the view |
| extraction | checkpoint-aware session copy plus workspace, after destruction |
| price identity | `deepseek-2026-09-09` |

## 4. N = 2 pairs — four trajectories

The repository's own minimal field-qualification design for this stack is two trajectories per arm
(R4-C3 §4): enough to show that a failure would be reproducible, and enough to exercise both arm
transitions. One per arm would be smaller, and here it would also be weaker for a specific reason —
**R4-C3's own `contract` slots delivered zero source-form bytes in either session.** A `contract`
trajectory that never receives source-shaped text cannot exercise the false-positive path this
repair exists to close. Two chances per arm is the smallest design that gives the specificity
dimension a real chance of being put to the test.

N is **not** derived from any observed arm difference, and no value measured here may be used to
choose the sample size of any future experiment.

## 5. Order — frozen

`full · contract · contract · full`. A `full` → `contract` transition, which is the shape of the
historical leak, and its reverse, which is what would catch integration code that remembers the last
arm. The next arm is never chosen from what the previous one did.

## 6. Lifecycle

Per slot: fresh view · stage arm, runtime, harness, interpreter, credential · hermeticity preflight ·
launch only if clean · execute · checkpoint and extract session and workspace · destroy view · grade
control-side · attribute under `mlr-context-6` · profile · audit before the next slot. No slot reuse,
no previous session state, no previous source artefact, no previous worker log.

## 7. Retry, resume, stop

Established semantics. A failure before a semantic trajectory begins — construction, staging,
preflight refusal, provider unreachability, launcher failure — is an infrastructure attempt, bounded
at three, and may retry the same slot. A trajectory that began is never re-rolled for its outcome.

Stop the series on: uncontrolled source availability · oracle, reference or prior-sample leakage · a
boundary bypass · a material attribution escape · an uncovered model-visible event · material
unresolved attribution at item **or component** granularity · a contradiction indicating an
instrument defect · cross-slot contamination · model identity inconsistency · session extraction
failure. Preserve the evidence and stop; do not patch the classifier and continue under this
identity. Do **not** stop for ordinary model behaviour.

## 8. Ceiling — $0.40

Checked before each slot with a $0.08 reserve. A trajectory under way is never cut short for money.

## 9. Pass criteria — frozen

Boundary and hermeticity, per completed slot:

1. Preflight clean before launch.
2. No uncontrolled implementation source; `full` exposes exactly its declared exposure.
3. No control-plane, prior-slot, oracle or reference evidence reachable.
4. View destroyed; no cross-slot residue; no executor state outside any view.

Attribution integrity, per completed slot:

5. Zero material unresolved **items**.
6. Zero material unresolved **components**.
7. Zero contradictions.
8. Zero uncovered model-visible events.

Causal-provenance correctness, per completed slot:

9. No representation classified as direct implementation source merely because its bytes equal
   source: every source-attributed span carries `artifact-path`, `author` or `ancestry` evidence, or
   an activity that named a module source file.
10. Container replay promotes no unrelated component: in any item whose source provenance is
    inherited from replayed content, components of other forms keep their own origins.

`contract`:

11. Direct implementation source **zero**, unless there is evidence of an actual treatment breach.
    A non-zero value stops the series for inspection of which it is — a real leak, or an attribution
    defect — and neither is assumed.
12. Runtime-derived, public-contract and model-derived representation remain in their own channels.

`full`:

13. Where the trajectory consumes genuine source, `mlr-context-6` recognises its causal ancestry,
    replayed source-derived spans retain source provenance, and mixed containers stay span-scoped.

Round trip and identity:

14. Extracted database readable after destruction; profile complete; oracle runs control-side on
    every extracted workspace; no credential in any retained artefact; model, boundary, runtime and
    attribution identities stable across all slots.

Headroom:

15. At least one of the four trajectories satisfies the oracle. At N = 4 this detects catastrophic
    model/task incompatibility and nothing finer. **Task correctness is not attribution
    correctness**: a correct answer with broken attribution is a failure, and a wrong answer with
    sound attribution is a headroom observation, not an attribution defect.

## 10. Coverage — declared before execution

The two dimensions this qualification exists to exercise, and what counts as exercising them:

- **Live source sensitivity** is exercised iff at least one completed `full` trajectory consumes
  one or more bytes of direct implementation source under causal ancestry.
- **Live specificity against the repaired defect** is exercised iff at least one completed
  `contract` trajectory delivers at least `MATERIAL_BYTES` of source-*form* text — that is, source-
  shaped bytes actually arrive and the classifier is actually asked the question that broke r4.

The model is not steered toward either. No introspection command is scripted, no source read is
induced, and the agent's route is whatever it chooses.

**If a dimension is not exercised, the outcome is `Qualification incomplete` for that dimension and
no additional slot is run in this milestone.** The remedy is a new qualification identity in a later
milestone, not more samples improvised after observation.

## 11. Result families

**A** `mlr-context-6` field-qualified · **B** qualification incomplete — a declared dimension was not
exercised · **C** attribution field failure · **D** boundary field failure · **E** round-trip failure ·
**F** oracle integrity failure · **G** model/task headroom failure · **H** external infrastructure
invalid.

No family describes a treatment outcome, because nothing here can support one.

## 12. What this will not claim

No treatment effect, no arm comparison, no efficiency claim, no statement that the contract
substituted for the implementation, no sample-size guidance. Per-slot values are qualification
diagnostics. A pass licenses preregistering a new paired experiment under a new identity — not
running one, and not resuming r4.

---

# Outcome — qualification incomplete

**Three of four trajectories completed, three correct, one attempt each, $0.0884 of $0.40.** Record:
[`craft-mlr-r5-attribution-field-qualification.json`](../../results/craft-mlr-r5-attribution-field-qualification.json).

Family **B**. Live source sensitivity was exercised and passed. **Live specificity against the
repaired defect was not exercised**, and the frozen rule in §10 applies: no additional slot is run.

## Diagnostics — not treatment-effect evidence

| slot | arm | correct | preflight | direct source | runtime | reconstruction | source-form delivered | unres. items/comps | contra | uncov | derived |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | full | yes | clean, 4 declared | 5,630 | 0 | 0 | 3,909 | 0 / 0 | 0 | 0 | $0.0256 |
| 2 | contract | yes | clean, 0 declared | **0** | 34,890 | 0 | **0** | 0 / 0 | 0 | 0 | $0.0254 |
| 3 | contract | yes | clean, 0 declared | **0** | 881 | 0 | **0** | 0 / 0 | 0 | 0 | $0.0228 |

Two trajectories per arm were frozen; one `full` slot was lost to an infrastructure interruption and
is accounted below. **No paired difference is computed and none may be.**

## What passed

Every frozen criterion that the completed slots can speak to. Preflight clean before every launch;
`full` exposed exactly its four declared files with zero findings; `contract` declared and found
nothing. Unresolved items **0**, unresolved components **0**, contradictions **0**, uncovered
model-visible events **0**, in all three sessions. Every view destroyed, every extracted database
readable afterwards, every profile complete, the hidden oracle run control-side on every extracted
workspace. Boundary `b88bd43109184459`, hermeticity `dcbf34fb63821980`, executor `2f24593f1b8e578d`,
model, variant, runtime structure and fixture digests identical across all slots. No credential in
any retained artefact. Workspace digests identical within each arm and different between them.

## Live sensitivity — exercised, and it holds

Slot 1's agent read all four module source files directly:

| file | delivered | source-form lines | basis | origin | route |
|---|---|---|---|---|---|
| `_store.py` | 2,649 | 1,872 | `artifact-path` | `implementation-source` | `source-file` |
| `__init__.py` | 670 | 453 | `artifact-path` | `implementation-source` | `source-file` |
| `_backend.py` | 1,698 | 1,172 | `artifact-path` | `implementation-source` | `source-file` |
| `_errors.py` | 613 | 412 | `artifact-path` | `implementation-source` | `source-file` |

5,630 bytes total — exactly the declared exposure. Artifact-scoped charging held: the whole
delivered rendering counted, not merely the 3,909 bytes whose lines matched the fingerprint. Real
source ancestry is recognised in the field under `mlr-context-6`.

## Mixed-container behaviour — exercised, and it holds

Slot 2's agent read its own worker log: **48,214 bytes**, carrying 34,618 of disassembly, 170 of
runtime structure and 255 of path metadata. Basis `content` — the weakest in the table — origin
`implementation-runtime`, direct source **zero**, and the path-metadata component kept
`implementation-metadata` instead of inheriting the container's label.

That is structurally the same event that destroyed r4 slot 3: a large mixed container replaying
earlier tool output. The component-scoped half of the repair is visibly working on live evidence.

## Live specificity — not exercised

Neither `contract` trajectory delivered **a single byte of source-form text**, across 116 and 125
attributed items. They reached the module's interior entirely through disassembly and runtime
structure. Slot 3's agent tried `inspect.getsource` — a source-recovery route — and got nothing
source-shaped back, which is the treatment refusing rather than the classifier deciding.

So `contract` direct source is zero in both slots, and that zero is weaker than it looks. The
question the repair exists to answer — *are these source-looking bytes direct source?* — was never
put to the classifier in a live contract trajectory. R4-C3 saw the same thing and the paired
experiment then found the docstring path anyway; a zero obtained without the question being asked
cannot be read as specificity demonstrated.

Neither agent used `help`, `pydoc` or `__doc__` at all. The exact r4 mechanism did not recur.

## The interrupted slot

Slot 4 (`full`) began, and its supervising driver was killed by a host command timeout. The executor
ran to normal termination — 24 model calls, 44 tool calls, report and terminal event written — but
the post-launch measurement lifecycle never ran, so there is no evidence gate, extraction, grading or
attribution for it. §7 says a trajectory that began is never re-rolled, so it is accounted
($0.0146 derived, $0.0170 executor-reported) and preserved, and contributes no measurement. It is
not completed by hand: reconstructing the post-launch half outside the qualified code path would put
an unqualified path inside a qualification.

Its loss costs the series a second `full` sample. It does not affect the coverage verdict: sensitivity
was already exercised by slot 1, and the unexercised dimension is on the `contract` side.

## What this licenses

Nothing new. `mlr-context-6` recognised genuine source provenance and kept a large mixed container
component-scoped, under real model-driven execution on the qualified boundary, with clean audits
throughout. That is real evidence and it is half of what this qualification set out to obtain. The
repaired false-positive path remains tested only deterministically and retrospectively.

A further qualification needs a new identity, and its design problem is now explicit: three of five
live `contract` trajectories across two milestones have produced no source-shaped text at all, so a
design that waits for one to appear by chance is not reliable. Whether a qualification may legitimately
place source-shaped text in a `contract` trajectory's path without steering the agent — and if so
how — is a question for that milestone, not this one.
