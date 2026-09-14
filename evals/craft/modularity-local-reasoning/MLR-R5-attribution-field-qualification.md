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
