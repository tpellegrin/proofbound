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

An empty cell means *not run*, never *worse*.

## How this page is maintained

By hand, deliberately. A generated index would need machinery to read every manifest and a test to
keep it honest, and the Field Test does not support building that for two entries — nothing becomes
impossible without it. If the table outgrows hand maintenance, generating it from the experiment
manifests is the obvious next step, and the manifests already carry the fields it would need.
