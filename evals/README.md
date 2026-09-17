# Evaluating Proofbound

This directory answers a question the rest of the repository cannot: **does any of this actually
help?**

Evaluation *observes* Proofbound and is never part of it. A measurement is evidence for a person,
never an authorization: nothing here may accept an artifact, and no number adopts a change. That
boundary is normative — see [core-model.md](../docs/architecture/proofbound/core-model.md) on
evidence authority, and the root [README](../README.md#what-the-name-means).

> **There is no universal runner.** These are separate programmes that share conventions —
> pre-registration, blind grading, retained evidence, priced usage — and *not* a single harness with
> a common entry point. Anything implying one command runs "the evals" is wrong.

## Four questions, and what actually answers each

| Question | Evidence needed | Where it lives today |
|---|---|---|
| **Do the controls enforce their declared rules?** | Deterministic checks of identity, scope, freshness, authorization, lifecycle, attribution, limits | `python3 -m unittest discover -s tests -t .` — the canonical suite, 1,100+ cases, no model, no credentials. This is the only family that is fully answered |
| **Can the workflow make the right decision and deliver the required result?** | Calibrated valid and invalid cases, real-agent observations, external checks of the artifacts produced | Partly. Invalid cases: [Eval V1](eval-v1.md) (planted contradictions) and two authority demonstrations, both of which correctly **stopped**. Valid cases: [`authority_slice/`](authority_slice/README.md) — validated offline; no case's **workflow** has run against a model, and its two handoff fixtures have each been read once by a fresh context in a read-only recovery probe. Delivery of a required artifact end to end: **never observed** |
| **Does a proposed harness change improve outcomes?** | A declared baseline and treatment, variables held fixed, repetitions, uncertainty, cost, guardrails | The most developed machinery here: `_experiment.py` refuses an incomplete pre-registration, `_repeat.py` preallocates slots, `pb_mlr.py` runs paired interleaved arms. Discipline in [evaluation.md §E24](../docs/architecture/proofbound/evaluation.md#e24-what-it-takes-to-call-an-increment-an-improvement) |
| **Does the software remain understandable and changeable over time?** | Sequences of realistic changes, session handoffs, preserved requirements, architectural consequences, human effort | **Mostly a gap.** System craft ([system-craft.md](../docs/architecture/proofbound/system-craft.md)) attacked it and found its own instrument unreliable; the narrowed successor (MLR) measures one change in one module, not a sequence. Multi-change and handoff-cost measurement is not built |

## The entry points, and what each really does

**Every command below is marked for what it spends.** `unpaid` reaches no provider and needs no
credentials; `PAID` invokes real models through the worker harness.

| Entry point | What it measures | Commands |
|---|---|---|
| [`pb_eval.py`](pb_eval.py) | V1: does a fresh `spec-reflector` detect a planted contradiction in an artifact it did not author? | `list`, `show`, `compare` — *unpaid*. `run` — **PAID**, one call per trial plus one per grade |
| [`pb_craft.py`](pb_craft.py) | System craft: does architecture stay changeable? Calibration and repeatability | `validate <case-dir>` — *unpaid*. `run`, `reflect`, `regrade`, `repeat-reflect`, `sample` — **PAID** |
| [`pb_mlr.py`](pb_mlr.py) | Modularity and local reasoning: does reading a module's implementation contribute to a change outside it? | `preflight`, `b1-preflight`, `analyse`, `retrospect` — *unpaid*. `pilot`, `paired`, `b1` — **PAID** |
| [`pb_lifecycle_field_check.py`](pb_lifecycle_field_check.py) | Whether the attempt deadline actually stops a real worker | **PAID** — two provider-backed trials. An engineering validation, never a treatment sample |
| [`authority_slice/pb_slice.py`](authority_slice/README.md) | The four-case authority slice: challenge and handoff, valid and invalid | `validate`, `replay`, `build`, `probe-input`, `launch-arithmetic`, `report` — *unpaid*, all of them |

Supporting modules, none of them an entry point: `_scenario` (cases and their identities), `_trial`
(one execution through the real pipeline), `_grade` (mechanical and blind semantic grading),
`_profile` (calls, tokens, tool activity, measured time, context by origin), `_pricing` (dated price
tables; usage and cost kept apart), `_compare` (two runs, derived not stored), `_summary`,
`_experiment` (pre-registration), `_repeat` (preallocated slots and checkpointing), `_hermetic` and
`_semantic_view` (isolation), `_mlr*` (the modularity series), `_lineage`, `_provider`.

### What runs with no credentials at all

```bash
python3 -m unittest discover -s tests -t .                        # the canonical suite
python3 evals/pb_eval.py list                                     # scenarios and identities
python3 evals/pb_eval.py show evals/results/eval-v1.json          # a recorded run
python3 evals/pb_craft.py validate evals/craft/notification-provider-boundary
python3 evals/pb_mlr.py preflight                                 # hermeticity scan
python3 evals/authority_slice/pb_slice.py validate                # the slice's oracle
python3 evals/authority_slice/pb_slice.py replay                  # four cases, fake executor
python3 evals/authority_slice/pb_slice.py launch-arithmetic       # derive a launch ceiling
```

`pb_craft.py validate` takes a **path**, not a bare case name. Commands are written out in full
here because a schematic ellipsis is not a command; where one appears in this repository's docs it
marks an argument list to fill in, never a runnable line.

## How an evaluation is run here

Six steps. They are not a pipeline with an entry point; they are what a defensible result required
every time one was produced.

1. **State the product claim and how an observation could refute it.** "Supplying accepted
   consequence C raises independent discovery of pressure P" is a claim. "This makes evaluation
   better" is not, because nothing could refute it.

2. **Declare the input domain, then construct a case and an oracle.** Check the oracle against
   sound alternatives and against defective variants: an oracle that only accepts its own reference
   implementation is testing resemblance. Passing a finite suite supports its stated coverage and
   nothing wider. Where a domain is finite, say so and enumerate it — the slice's contradiction is
   *proved* by enumerating six dispatch orders, while the authority demonstrations' floating-point
   claim rested on a bounded search that ran out, which
   [establishes nothing](../docs/architecture/proofbound/evidence/authority-workflow-demo-2-audit.md).

3. **Separate case development from evaluation.** Calibrate first. Then freeze identities,
   information access, allocation, recovery policy and the decision rule *before* collecting
   comparison evidence. Once treatment measurement begins nothing may change; a design flaw found
   mid-run makes the experiment **invalid**, and the repair is a new experiment with a new identity
   — not an amended rule. Both authority demonstrations amended frozen rules mid-run, which is why
   neither is a controlled observation.

4. **Run through the product path being claimed.** No eval-only client that bypasses orchestration:
   that would measure something Proofbound does not ship. **Mark every simulated component**, and
   retain inputs, outputs, configuration, attempt identities and attribution.

5. **Grade mechanical facts, semantic findings and product outcomes separately.** Mechanical
   grading is deterministic. Semantic grading is blind — the grader is never told the expected
   result — and must itself be calibrated against concrete evidence and human adjudication. Product
   outcome is whether the requested artifact exists and is usable, which a favourable test tally
   does not establish.

6. **Report the outcome and its uncertainty, decide, and turn failures into regressions.**
   "No measurable improvement under this configuration" is a result. Adoption is a person's
   decision. Scope a regression to what actually failed.

**Reliability before validity.** Do not interpret a difference smaller than the instrument's own
variation under identical conditions. Measured here: a craft reflector's conclusion moves on 43% of
byte-identical repeats and the grader on 17%. Consistency is not correctness — a system can repeat
the same wrong answer indefinitely.

## What to report

A small set of decision-relevant measures, deliberately **not** collapsed into one score. Nothing
supplies the exchange rates that would require.

| Measure | Why it is separate |
|---|---|
| Requirement fulfilment, and regressions | Delivering the requested thing is not the same as passing tests |
| Correct rejection, and **false** rejection | Improving abstention can suppress needed repairs; refusing well is only half |
| Finding correctness, and supporting-**evidence** correctness | A finding can be right while its exhibit is wrong — demo-2's decisive exhibit had its two instants in the wrong order |
| Authority and recovery accuracy | Did a fresh coordinator recover the real state, and stop when it should? |
| Execution failures | An infrastructure failure is not a semantic verdict, and it is still operational reliability |
| Cost, and accounting completeness | Unknown expenditure is unknown, never zero. Measured usage, derived cost, estimated reserve, justified bound and provider-confirmed billing are five different facts |
| Coordinator and human interventions | The manual effort a run required is a product cost, not overhead to leave out |

Architectural quality connects to an accepted consequence under a *later* change — never to
resemblance to a preferred design.

### Keep every case visible

Report `reached`, `completed`, `blocked`, `failed`, `invalid` and `not-observed` separately. A case
that was never run and a case that ran and failed are different facts.

**Conditional stage results carry their denominators.** Six launches are not six independent
demonstrations; demo-2's six attempts were one dependent chain, and its two clean reviews came after
the stages before them had already succeeded. Retries and post-hoc case selection stay in the
accounting — a result reported after discarding the runs that went badly is a different result.

## Reproducibility, honestly

Pin and record what is actually available: model and variant, executor path **and** sha256,
interpreter (record `sys.executable`, not a nominal path — demo-2 recorded `/usr/bin/python3` at a
version that binary is not), harness version, prompt and contract digests, oracle identity, price
table id and retrieval date, fixture digests.

That supports **inspection**, not replay. A provider model is not deterministic, identical
conditions produced 16 to 38 model calls and 154k to 288k input tokens across six runs of one
configuration, and no pinning here promises otherwise.

**Host restrictions that affect how you run things.** Tests share host state, so the canonical suite
runs **serially** — `python3 -m unittest discover -s tests -t .`, not a parallel runner.
`tests/_host_serial.py` exists for exactly this. Paid runs need the `opencode` executable on `PATH`
and a provider that resolves in your environment; credentials live in OpenCode's own configuration,
outside this repository, and nothing here reads, stores or prints them. CI runs the canonical suite
only ([`.github/workflows/tests.yml`](../.github/workflows/tests.yml)) — no evaluation family runs
in CI, and none should without an explicit cost decision.

## Results and designs

`results/` holds committed run **summaries**; raw evidence (prompts, reports, grader output, run
trees) is large, local, and deliberately uncommitted — `--evidence` directories are never committed.
When raw evidence is gone the summary still says what was measured; the ability to re-verify the
execution is what is lost, and that is reported as unavailable rather than treated as fine.

| Design document | Covers |
|---|---|
| [evaluation.md](../docs/architecture/proofbound/evaluation.md) | How one run is measured: scenarios, trials, mechanical vs semantic grading, multi-property completeness; `§E24` pre-registration; `§E25` the instrument is part of the experiment |
| [evaluation-comparison.md](../docs/architecture/proofbound/evaluation-comparison.md) | Whether a suite can discriminate at all; `§E22` reliability before validity; the `P12` independence control |
| [system-craft.md](../docs/architecture/proofbound/system-craft.md) | Whether a system stays changeable; why the first instrument was not ready |
| [evidence/evaluation-runs.md](../docs/architecture/proofbound/evidence/evaluation-runs.md) | What individual runs established. History, never protocol |
| [eval-v1.md](eval-v1.md) | V1's own prerequisites, usage, scenario populations and authoring rules |
| [authority_slice/README.md](authority_slice/README.md) | The four-case slice, its oracle, and its readiness |
| [craft/modularity-local-reasoning/](craft/modularity-local-reasoning/) | The MLR pre-registrations, runs and audits |

### What the MLR findings are, narrowly

The modularity series asks one question: for a change whose responsibility lies **outside** a
module, does reading that module's implementation contribute to getting the change right? Its
`eventbus-b1` replication ran twelve valid trajectories with no retries and replicated the core
phenomenon; the secondary procedural pattern was heterogeneous and unlike the earlier `q1` series.

That is a result about **one fixture, one model, one task shape, and one kind of context
withholding**. It is not evidence that Proofbound improves engineering quality, that bounded context
is generally better, or that any of this transfers to another repository.
