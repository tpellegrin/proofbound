# Evaluations by model configuration

An **index, not a home.** Every evaluation still lives with the research question it belongs to —
that is the primary organisation and it is not changing, because the scientific question is primary
and the model is one of its experimental conditions. This page exists so a second question is also
cheap to answer: *what evidence exists for model X, and which models have exercised experiment Y?*

It **links and never duplicates** (`P3`). Nothing here is a result; every number lives in the record
it was measured into, and this page is a routing table over those records.

**This is not a leaderboard.** No model here is approved, certified, recommended or ranked. Two
models appear because two models were used, and the evidence under each was gathered to answer a
question *within* that model, not to compare one against the other. Choosing a model is an
engineering decision a person makes; evidence informs it and never makes it (`P5`).

## Why a model axis at all

Because a pipeline treatment may not behave the same way under different models. A bounded context
might help a weaker model and be ignored by a stronger one; hiding an implementation might reduce
distraction for one and provoke reconstruction in another. Proofbound cannot test that yet, and will
not be able to until the same treatment has run under more than one model configuration. Keeping the
model visible as an axis is the smallest step towards being able to ask.

## What counts as one configuration

A model name is not a configuration. These are **different** entries, never pooled:

- a different provider or requested model;
- a different thinking mode, or a different reasoning effort;
- a documented model version that changed under a moving alias.

Where the provider exposes only an alias, the entry records the alias, the documented version at the
time, and the identity the provider actually returned — separately, because an alias that moves later
must not silently reinterpret evidence gathered before it moved.

---

## DeepSeek V4 Flash · thinking · effort `high`

| | |
|---|---|
| provider | `deepseek` (OpenCode native integration) |
| requested model | `deepseek/deepseek-v4-flash` |
| documented version | `DeepSeek-V4-Flash-0731` (docs read 2026-09-09) |
| provider-observed identity | `deepseek-v4-flash` / provider `deepseek` |
| thinking | enabled (provider default, set explicitly) |
| reasoning effort | `high`, passed as `--variant high` and confirmed in session telemetry |
| attribution | `mlr-context-5` — one normalised inbound boundary, causal precedence, material components (`mlr-context-4` for the R2 qualification, `mlr-context-3` for the paired run and everything before it) |
| sampling | **not controllable** — the provider documents that thinking mode ignores `temperature`, `top_p`, `presence_penalty` and `frequency_penalty` |
| context | 1M documented |
| pricing identity | `deepseek-2026-09-09` |

**Evidence**

- Compatibility qualification and headroom pre-registration:
  [`MLR-C3D-headroom-preregistration.md`](../craft/modularity-local-reasoning/MLR-C3D-headroom-preregistration.md)
- MLR headroom qualification — 5/5 correct, strong source headroom, **attribution required
  revision**: [`MLR-C3D.md`](../craft/modularity-local-reasoning/MLR-C3D.md),
  [record](../results/craft-mlr-deepseek-v4-flash-high-headroom.json)
- Repaired-instrument requalification — 3/3 correct, zero attribution escapes, **requalified**:
  [`MLR-C3D-R.md`](../craft/modularity-local-reasoning/MLR-C3D-R.md),
  [record](../results/craft-mlr-deepseek-v4-flash-high-requalification.json)
- Paired experiment pre-registration:
  [`MLR-deepseek-paired-preregistration.md`](../craft/modularity-local-reasoning/MLR-deepseek-paired-preregistration.md)
- MLR paired calibration — 12/12 slots correct, treatment held, **invalid**: a `contract` run
  laundered 29,499 bytes of runtime disassembly through a temporary file and the attribution
  classified it as `other`:
  [`MLR-deepseek-paired-run.md`](../craft/modularity-local-reasoning/MLR-deepseek-paired-run.md),
  [record](../results/craft-mlr-deepseek-v4-flash-high-paired.json)
- Attribution repair — causal provenance, representation form and delivery route separated:
  [`MLR-C3D-R2.md`](../craft/modularity-local-reasoning/MLR-C3D-R2.md), with the invalid run
  re-read for diagnosis under the repaired instrument
  ([retrospective](../results/craft-mlr-deepseek-v4-flash-high-paired-retrospective.json) — a
  diagnostic, not that experiment's result)
- R2 field qualification — 6/6 correct, **does not pass**: the search route was never brought under
  the causal model, and a `contract` agent found a stray `full` workspace on the host filesystem:
  [prereg](../craft/modularity-local-reasoning/MLR-R2-qualification-preregistration.md),
  [`MLR-R2-qualification.md`](../craft/modularity-local-reasoning/MLR-R2-qualification.md),
  [record](../results/craft-mlr-deepseek-v4-flash-high-paired-r2-qualification.json)
- Attribution and environment repair — one inbound boundary for every transport, material minority
  components, and a hermeticity preflight the environment does not currently pass:
  [`MLR-C3D-R3.md`](../craft/modularity-local-reasoning/MLR-C3D-R3.md),
  [18-session retrospective](../results/craft-mlr-eighteen-session-retrospective.json),
  [preflight before cleanup](../results/craft-mlr-hermeticity-preflight-contaminated.json),
  [after cleanup](../results/craft-mlr-hermeticity-preflight-after-cleanup.json)
- Execution-boundary design check — a per-slot constructed view selected, **not implemented**:
  [`MLR-C3D-R4-execution-boundary.md`](../craft/modularity-local-reasoning/MLR-C3D-R4-execution-boundary.md),
  [feasibility probes](../results/craft-mlr-boundary-feasibility-probes.json)
- Execution-boundary substrate — constructed per-slot views, implemented and proven locally, **not
  yet integrated with the worker**:
  [`_semantic_view.py`](../_semantic_view.py),
  [substrate probes](../results/craft-mlr-semantic-view-probes.json)
- Real worker integration — the MLR arm, launcher, executor and subprocess tree inside the boundary,
  with the model-driven tool route reserved for field qualification:
  [`_mlr_boundary.py`](../_mlr_boundary.py),
  [integration probes](../results/craft-mlr-boundary-integration-probes.json)
- Field qualification — **stopped before completion**: one real model-driven trajectory ran inside the
  boundary and was fully explainable, but the path is not yet reliable:
  [first freeze](../craft/modularity-local-reasoning/MLR-R4C-qualification-preregistration.md),
  [second freeze and outcome](../craft/modularity-local-reasoning/MLR-R4C2-qualification-preregistration.md),
  [record](../results/craft-mlr-r4c-field-qualification.json)
- Clean-route requalification — **complete measurement path field-qualified**: 4/4 valid, 4/4 correct,
  zero unresolved, contradictions or uncovered events, `contract` direct source zero:
  [freeze and outcome](../craft/modularity-local-reasoning/MLR-R4C3-requalification-preregistration.md),
  [route readiness](../results/craft-mlr-r4c3-route-readiness.json),
  [record](../results/craft-mlr-r4c3-field-requalification.json)
- Paired experiment — **executed and invalid**: four of twelve slots ran, all correct, before a
  material attribution defect stopped the series. A public docstring reached through runtime
  introspection was classified as direct implementation source in a `contract` slot, and the
  misclassification propagated through the content-echo index into a 42,915-byte worker-log read:
  [preregistration](../craft/modularity-local-reasoning/MLR-paired-r4-preregistration.md),
  [N audit](../craft/modularity-local-reasoning/MLR-paired-r4-N-audit.md),
  [run and defect](../craft/modularity-local-reasoning/MLR-paired-r4-run.md),
  [record](../results/craft-mlr-deepseek-v4-flash-high-paired-r4.json)
- Causal attribution precision repair — content no longer establishes that source was read, and
  ancestry of content covers only the spans that replay it. Attribution version `mlr-context-6`;
  two of fifty-four retained sessions reclassify, both false `contract` source:
  [`MLR-C3D-R5-attribution-precision.md`](../craft/modularity-local-reasoning/MLR-C3D-R5-attribution-precision.md),
  [replay](../results/craft-mlr-attribution-precision-replay.json)
- Live qualification of `mlr-context-6` — **incomplete**: real source ancestry recognised and a
  48 KB mixed worker-log read kept component-scoped, but neither `contract` trajectory delivered any
  source-form text, so live specificity against the repaired defect was not exercised:
  [freeze and outcome](../craft/modularity-local-reasoning/MLR-R5-attribution-field-qualification.md),
  [record](../results/craft-mlr-r5-attribution-field-qualification.json)
- Known-answer provenance calibration — **pass**: the same 169-byte docstring span delivered by
  three causal routes took three origins, with direct implementation source above zero only where an
  activity actually opened the source file. Completes the live evidence `mlr-context-6` was missing:
  [freeze and outcome](../craft/modularity-local-reasoning/MLR-R6-provenance-calibration.md),
  [record](../results/craft-mlr-r6-provenance-calibration.json)
- Paired experiment on the qualified stack — **executed, family E · Heterogeneous**. Twelve valid
  trajectories, one attempt each, 6/6 pairs both correct; `full` consumed 5,630-6,170 bytes of
  direct implementation source and `contract` zero in every pair, but the compensating runtime
  channel spans 102 to 39,231 bytes and is not arm-determined:
  [preregistration](../craft/modularity-local-reasoning/MLR-paired-q1-preregistration.md),
  [run](../craft/modularity-local-reasoning/MLR-paired-q1-run.md),
  [record](../results/craft-mlr-deepseek-v4-flash-high-paired-q1.json)
- Cross-fixture replication substrate — **frozen, not preregistered and not run**. A second module
  boundary, `eventbus`, chosen to differ from object storage on the axes that would let q1 explain
  it: inverted control flow, one-to-many fan-out and partial failure. Fixture A is unchanged and
  `mlr-context-6` is unchanged:
  [design and substrate](../craft/modularity-local-reasoning/MLR-B-cross-fixture-design.md)
- Cross-fixture replication — **frozen, not executed**. Same model, same measurement system, same
  N and slot order as q1; the fixture is the one changed dimension. N justified from replication
  design and the fixture-independent half of the pre-q1 rationale, never from q1's outcome:
  [preregistration](../craft/modularity-local-reasoning/MLR-eventbus-b1-preregistration.md)
- Cross-fixture replication, execution path — **committed and deterministically verified; not run**.
  The frozen design could not be executed: grading resolved fixture A's oracle, contract and
  vendored package by name, and the series loop drove the unbounded attempt path with a blanket
  retry that §11 C forbids. Both repaired, with a committed bounded runner and a preflight that
  buys nothing:
  [execution record](../craft/modularity-local-reasoning/MLR-eventbus-b1-execution.md)
- Cross-fixture replication, executor prerequisite — **resolved; b1 not yet run**. The frozen
  executor was acquired in isolation from the upstream `v1.18.29` release and its extracted binary
  matches the full 64-character historical digest, not merely the prefix §5 prints; under the frozen
  host's CPython 3.9.6 the semantic boundary identity reproduces `b88bd43109184459`. Preflight is
  launchable. An earlier inference that the frozen build was a Homebrew bottle was wrong and is
  withdrawn — no committed record names any distribution channel
- Cross-fixture replication — **executed, family R1 · the core phenomenon replicates**. Twelve
  slots, twelve valid trajectories, one attempt each, no retries, $0.238762 of $0.50 and the figure
  is the whole of it; every frozen identity held on all twelve. The secondary procedural pattern is
  heterogeneous and does not resemble q1's. A later dated audit corrects the run report's
  attempt-ceiling reasoning and leaves the result standing:
  [run](../craft/modularity-local-reasoning/MLR-eventbus-b1-run.md),
  [audit](../craft/modularity-local-reasoning/MLR-eventbus-b1-timeout-audit.md),
  [record](../results/craft-mlr-deepseek-v4-flash-high-paired-eventbus-b1.json)

---

## Nemotron 3 Ultra Free

| | |
|---|---|
| provider | `opencode` |
| requested model | `opencode/nemotron-3-ultra-free` |
| provider-observed identity | `nemotron-3-ultra-free` / provider `opencode` |
| thinking / effort | not configured — these runs predate explicit effort control |
| pricing | none billed |

**Evidence**

- MLR-C3 headroom pilot — material headroom, two instrument defects found:
  [`MLR-C3.md`](../craft/modularity-local-reasoning/MLR-C3.md),
  [record](../results/craft-mlr-c3-full-headroom-pilot.json)
- MLR-C3R headroom pilot — repaired instrument, 6/6 correct:
  [`MLR-C3R.md`](../craft/modularity-local-reasoning/MLR-C3R.md),
  [record](../results/craft-mlr-c3r-full-headroom-pilot.json)
- MLR paired calibration — **invalid**, five of eight pairs lost to a provider outage:
  [`MLR-paired-run.md`](../craft/modularity-local-reasoning/MLR-paired-run.md),
  [record](../results/craft-mlr-paired-calibration.json)

Earlier craft and P12 evaluations also ran under this model and are indexed by their research
question rather than here; this page lists the MLR series, which is where model identity became
load-bearing.

---

## Which models have exercised which experiment

| experiment | Nemotron 3 Ultra Free | DeepSeek V4 Flash · high |
|---|---|---|
| MLR headroom (`full` only) | MLR-C3, MLR-C3R | MLR-C3D, MLR-C3D-R — requalified |
| MLR paired (`full` vs `contract`) | attempted, invalid — provider outage | executed, invalid — attribution escape |
| MLR attribution qualification | not run | executed, does not pass — search route, host filesystem |
| MLR hermeticity precondition | not run | not met — the host holds reachable copies of the controlled evidence |
| MLR execution boundary | 2 trajectories, 0 slots | superseded by the clean-route requalification |
| MLR field requalification | not run | 4/4 valid and correct — complete path field-qualified |
| MLR paired `q1`, on the qualified stack | not run | executed, valid — family E · Heterogeneous, 12/12 |
| MLR cross-fixture `eventbus-b1` | not run | executed, valid — family R1 · core phenomenon replicates, 12/12 |

An empty cell means *not run*, never *worse*.

`MLR paired (full vs contract)` is the earlier attempt under each model — the Nemotron one lost to a
provider outage, the DeepSeek one to an attribution escape. Both are separate experiments from `q1`
and are never pooled with it, which is why `q1` keeps its own row rather than replacing theirs. This
table previously carried two rows with the same name, one of which described `eventbus-b1` while
`q1`'s executed result appeared nowhere; the rows below it are the correction.

## How this page is maintained

By hand, deliberately. A generated index would need machinery to read every manifest and a test to
keep it honest, and the Field Test does not support building that for two entries — nothing becomes
impossible without it. If the table outgrows hand maintenance, generating it from the experiment
manifests is the obvious next step, and the manifests already carry the fields it would need.
