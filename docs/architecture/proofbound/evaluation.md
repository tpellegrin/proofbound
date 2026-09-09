# Evaluation and regression

> **Eval V1 is implemented** (`evals/`); later capabilities remain designed only. How Proofbound measures whether its agent pipeline actually works,
> stays reliable, and does not drift. Orthogonal to the contract-binding chain: nothing here participates
> in engineering authority, and understanding it requires no M2 detail.
>
> Entry point: [README.md](README.md).

## E1. The measurement gap, precisely

The deterministic suite (340 tests) proves **mechanical** claims, and proves them well: immutable contract
binding, purpose→role enforcement, review freshness, scope restriction, graph satisfaction, candidate
identity, aggregate consistency acceptance, execution authorization, replay refusal, worker authority.
Every one is a fact Python can check exactly, and every one is checked.

It proves **nothing** about the claims Proofbound is actually built on. Verified: all six vertical slices
drive a stub worker on `PATH`, and every stub reflector writes a canned line — one of them literally
*"Independent review reached the production path; no task-relevant defect."* No test in this repository
has ever exercised a real model.

So these remain entirely unmeasured:

| Claim | Status |
|---|---|
| A fresh reflector detects a real engineering contradiction | **Unmeasured** |
| Declared review purpose changes reviewer behavior | **Unmeasured** |
| Findings are specific enough to route repair correctly | **Unmeasured** |
| Repair happens at the right layer rather than the convenient one | **Unmeasured** |
| Aggregate reflection catches what artifact-level reflection misses | **Unmeasured** |
| Bounded context preserves quality while reducing cost | **Unmeasured** |
| Any of the above is reliable across repeated runs | **Unmeasured** |

This is not "the tests are insufficient". The tests are correct and complete for what they cover. The
architecture simply has two halves — mechanical and semantic — and only one has ever been exercised.

## E2. The V1 thesis

One claim, chosen because everything else rests on it:

> **A fresh spec-reflector, given an artifact it did not author, reliably detects a planted engineering
> contradiction and the pipeline routes it as findings rather than acceptance.**

Falsifiable, central, currently unmeasured, and testable with a handful of scenarios. It deliberately
combines a **semantic** half (did it find the contradiction?) and a **mechanical** half (was the task left
unaccepted, with findings, rather than accepted?) — the second is gradeable by Proofbound's own domain
APIs, which anchors the stochastic half to something exact.

**Rejected as the first thesis**, each for a stated reason. *Independence beats self-review* is the
deeper claim but needs a control arm and doubles cost; it is only meaningful once detection is known to
happen at all (E10). *Purpose separation changes behavior* is narrower and less load-bearing. *Aggregate
reflection catches what artifact reflection misses* is genuinely important but needs a full accepted spec
chain per scenario — the right **second** thesis. *Bounded context preserves quality* cannot be assessed
before quality itself is measurable.

## E3. Scenario

A scenario is a frozen, self-contained engineering situation with a known semantic target.

| Part | Content |
|---|---|
| **Fixture** | A synthetic project tree — small, self-contained, no real customer code |
| **Accepted context** | Artifacts already accepted, establishing what the planted flaw contradicts |
| **Task** | The contract the worker under test receives |
| **Planted condition** | The specific engineering contradiction, recorded as a *property*, not an expected sentence |
| **Mechanical expectations** | What Proofbound's own APIs must report afterwards |
| **Rubric** | How a semantic grader decides whether the property was found |

**Ground truth is a property, never a phrasing.** A scenario requires *"the reflector identifies that the
design's retry policy contradicts the accepted proposal's idempotency constraint"* — not any particular
wording, and not a single permitted repair. Several defensible findings can satisfy one property; exact
answer matching would measure paraphrase, not comprehension.

**Scenarios are synthetic and committed.** Synthetic fixtures avoid privacy problems, keep transcripts
publishable, and make reproduction free. Deriving them from Proofbound's own mechanics is convenient but
not required.

### Scenario identity

The scenario's canonical content — fixture bytes, accepted context, task contract, planted property,
mechanical expectations — determines its version. Changing any of them makes a **new scenario version**,
because results before and after are not comparable.

The **rubric and grader are not part of scenario identity.** They belong to the *evaluation
configuration*: re-grading retained transcripts with a better rubric is a new measurement of the same
scenario, not a different scenario. Conflating them would make every rubric fix silently discard history.

## E4. Trial

One trial is one isolated execution of one scenario under one exact system-under-test configuration.

Every trial starts from a pristine copy of the fixture: fresh working tree, fresh run directory, fresh
Git state, no reused contracts or attempt directories, no provider session reuse. Proofbound's own
mechanics make most of this natural — attempts are already self-contained and immutable — but the
*project* copy must be fresh, because a previous trial's accepted artifacts would change what the next
trial's reflector sees. Copying a small synthetic fixture into a temporary directory is sufficient; no
containers, and no worktrees needed for the sizes involved.

**Infrastructure failure is not semantic failure.** A provider timeout, a rate limit, a missing
credential, a harness crash — these produce an **invalid trial**, reported separately and never counted
as "the reflector missed the contradiction". Invalid trials are reported, never silently dropped: a suite
whose provider failed half the time must look different from one that genuinely scored 50%.

## E5. System under test

A result is meaningless without knowing what produced it. Field-tested — each entry answers *which
difference could change the outcome or invalidate comparison?*

| Recorded | Why |
|---|---|
| Proofbound commit SHA | The system being measured; also identifies role protocols and prompt sources, which are repository files |
| Rendered prompt identity | The exact bytes the worker received — captured per attempt already, see E6 |
| Model identifier | The dominant variable |
| Harness identifier | `role != provider != model != harness`; already a state field |
| Model configuration | Temperature/effort where the provider exposes it; omitted honestly when it does not |
| Runtime version | Python version, since the harness runs on it |
| Scenario version | E3 |
| Trial timestamp | **Deliberately kept.** Proofbound normally rejects timestamps, but a provider alias can change behavior behind a stable model ID, so time is genuinely part of comparability here. This is an exception with a reason, not a precedent. |

**Rejected:** derived cost in currency (provider-dependent and unstable — record raw token counts if the
provider reports them, and let a reader price them), grader outputs (a separate configuration, E8), and
any "winner"/"approved"/"production ready" field (interpretation, not protocol).

## E6. Invoking a real model — the substrate is already sufficient

The most consequential finding of this design check: **no provider adapter is needed.**

`run_worker.py` launches a worker as `subprocess.Popen(["opencode", "run", "--model", <model>, ...])`,
resolved through `shutil.which("opencode")`. That is precisely the seam every vertical slice already
substitutes by placing a fake `opencode` on `PATH`. A real trial is therefore the *same pipeline* with
the real binary on `PATH` and credentials in the environment — the launcher, reservation, prompt
rendering, gate, scope check and acceptance path are all exercised unchanged.

This matters beyond convenience: an eval that bypassed orchestration would measure a model, not
Proofbound. Here the evaluation runs the product.

Two honest limits. `dsd_attempt launch` currently accepts only the `opencode-cli` harness, so V1 measures
one harness even though the *record* stays provider-neutral (`harness` and `model` are already state
fields). And credentials come from the environment through existing configuration — missing credentials
must produce an explicit **setup failure**, never a semantic result.

Free instrumentation already exists: `launch-prompt.txt` holds the exact prompt bytes, `terminal.json`
holds exit code and start/end times, `worker.log` holds provider output, and the scope diff holds what
actually changed.

## E7. Mechanical grading

Python grades through **Proofbound's own domain APIs** — the evaluator must never reimplement protocol
semantics, or it would measure its own reimplementation. This is dogfooding: if the APIs cannot answer a
question cleanly, that is a finding about the APIs.

Gradeable exactly: the expected artifact changed and forbidden paths did not (scope diff); the integrity
gate is clean or is not; the task reached `accepted` or did not; a fresh independent review exists;
declared purpose matches the contract; the ledger, graph, freeze and consistency records are in the
expected state; execution authorization returns the expected findings; no forbidden persistent state
appeared.

For the V1 thesis the decisive mechanical fact is simple and exact: **the task was not accepted, and a
reflector attempt produced findings.**

## E8. Semantic grading

Some questions need judgement: did the reflector identify *the* contradiction, is the finding actionable,
did it repair the right layer, did it overengineer.

**V1 uses a hybrid**: mechanical grading first, a model grader for the semantic property, and a human
calibration sample. The grader is given the scenario's property and the reflector's report, and answers
one narrow question — *does this report identify this property?* — not *is this good work*.

Three constraints:

- **The grader is not the system under test.** Different model where practical, and blind to the
  Proofbound version, the baseline, and any previous score. Self-grading loops are the obvious failure.
- **A grader failure is not a semantic failure.** Malformed or missing grader output records
  *grading unavailable*, never an invented score, and never recursive re-grading.
- **A semantic grade is evaluation evidence, not Proofbound acceptance.** It never touches artifact
  validity, candidate identity, consistency acceptance or execution authorization. Nothing in the
  evaluation track writes into the engineering authority chain.

Human calibration is a small reviewed subset compared against grader judgement, retained as an
inspectable record. It exists to detect grader drift; V1 needs the sample, not annotation tooling.

## E9. Trials, metrics, and what a number means

One stochastic run is an anecdote. V1 runs **five independent trials per scenario** across **three to five
scenarios** — small enough that a human can read every scenario, grader and transcript, which matters more
at this stage than statistical power.

Reported per scenario, as a **vector, never a single score**:

| Dimension | V1 metric |
|---|---|
| Mechanical correctness | trials meeting all mechanical expectations, N/N |
| Semantic success | trials where the property was identified, N/N |
| Reliability | whether it was *every* trial, not just the median |
| Validity | invalid trials, reported separately with cause |
| Context/resource | prompt bytes supplied, files supplied, wall-clock, tool calls where available |

No weighted composite. A cheaper run that fails more often is not better, and merging the dimensions
would hide exactly that tradeoff — the same reason
[context-economy.md §37.5](context-economy.md#375-coherence-and-context-economy-are-different-measurements)
refuses a combined health score. No
significance testing at N=5; reporting false precision would be worse than reporting counts.

**Regression vs capability.** *Regression* scenarios cover behavior that should be dependable, where
degradation is a signal. *Capability* scenarios are harder and expected to leave headroom; passing one
once does not mean it is solved. V1 keeps both labels and **defers holdouts** — with three to five
inspectable scenarios there is nothing yet to hold out, and the overfitting risk becomes real only once
prompts are being tuned against results.

**"Regression" is a word V1 does not get to use automatically.** It reports differences between
comparable runs; whether a difference is a regression is a human call. A numeric threshold chosen before
any data exists would be invented, not derived.

## E10. Comparison, baselines, and authority

Two runs are comparable when the scenario version matches and the system-under-test record differs only in
the variable under study. Records are shaped so a report can say *"only the Proofbound commit changed"* or
*"same Proofbound, different model"* — score movement is never automatically attributed to Proofbound.

A **baseline is evidence chosen for comparison**, explicitly selected or version-controlled. There is no
`latest_good_baseline` and no automatic promotion; "highest score wins" is not an architecture rule.

> Evaluation evidence is not architecture authority. A result showing version B outscoring version A does
> not adopt B, change a prompt, promote behavior into policy, or rewrite an accepted rule. Authority
> continues to flow through the normal Proofbound process. No self-modification from metrics.

**The control arm is deferred, with a trigger.** Comparing a fresh reflector against one carrying the
author's context is the sharper test of `P12`, and `--input`/`--resume-session` already make the
contaminated arm expressible. It becomes the V2 question **once V1 establishes that detection happens at
all** — comparing two arms that both detect nothing would measure noise.

## E11. What is retained, and where it sits

| Thing | Retention | Layer |
|---|---|---|
| Scenario definitions | Committed | Repository test assets — architecture inputs, not provenance |
| Trial transcripts and run trees | **Ephemeral**, local, not committed | Execution evidence, same expendability as any run tree |
| Mechanical grades | Derived, in the result record | Derived evaluation evidence |
| Summary results and baselines | Committed if deliberately retained | Durable *measurement* records |

Transcripts stay out of Git: they are large, noisy, and provider output. Summaries are small and are the
thing worth comparing. If a transcript must be re-graded later, that is a new measurement of retained raw
evidence — **never a mutation of the historical grade**.

**Evaluation records are not `L4` engineering provenance.** They observe Proofbound; they are not part of
its authority chain, and no evaluation record may alter artifact validity, candidate identity, consistency
acceptance or execution authorization. If a persisted result schema is introduced it gets a version, fails
closed on unknown versions, and records the rubric and grader identity — so a future rubric cannot silently
reinterpret an old score, the same discipline M0 and freeze v1 already apply.

## E12. Seed scenarios

Every slice stays a deterministic test. Scenarios are *derived*, never replacements, and the deterministic
suite must never depend on evaluation code or provider credentials.

| Slice | Semantic decision currently canned | V1 seed? |
|---|---|---|
| M1 spec reflection | Reflector challenging one authored artifact | **Yes — primary** |
| M2A ledger slice | Same shape; adds recording mechanics | No — mechanics, not judgement |
| M2B graph slice | Authoring to a declared topology | **Candidate** — a planted dependency contradiction |
| M2C-A freeze slice | None; pure identity mechanics | No |
| M2C-B consistency | Reflector challenging an *aggregate* | Deferred — the V2 thesis |
| M2C-C execution | Reviewer judging implementation vs contract | **Candidate** — reviewer-purpose variant |

V1 takes the M1 shape as its primary family, with three to five planted-contradiction variants: a design
contradicting an accepted proposal, a specification contradicting its design, an artifact with a plausible
but architecturally wrong assumption, and at least one **adversarial** scenario tempting a defensible-looking
but wrong route — for example a contradiction whose easiest "fix" is to weaken the accepted upstream
artifact rather than report the conflict.

Fixture-building utilities may be shared, but only in one direction: evaluation may import from test
helpers, never the reverse.

## E13. Deferred

Scenario mutation and variant families; holdout suites; pairwise blind grading of two pipeline versions;
the control arm (E10); aggregate-consistency scenarios; factorial independence experiments; cost
dashboards; scheduled or CI-gated runs; token accounting normalized across providers; any composite score.

Live-model evaluation is **not** part of normal CI. Contributors must never need paid credentials to run
the deterministic suite.

## Run history

What individual runs established — the V1 implementation outcome (`E14`) and the first live baseline
(`E15`) — is historical evidence, read on demand, in
[`evidence/evaluation-runs.md`](evidence/evaluation-runs.md). Outcomes are recorded there rather than
here so that this document stays the protocol and does not grow by one section per run.

## Discrimination and comparison

Whether a suite can distinguish two systems at all, and what a comparison of two runs may claim, are a
separate concern with their own normative document:
**[evaluation-comparison.md](evaluation-comparison.md)** (`E16`, `E17`). Scenario authoring and grading
stay here.

## E19. Multi-property scenarios — more resolution, still not a score

Two milestones have now ceilinged on the same observable: 20 of 20 planted properties detected at
baseline zero, then 21 of 21 across two configurations *after* the scenarios demonstrably got harder.
Three causes are separable and only one is the problem. Scenario difficulty **rose** — reflectors now
glob for source files and follow a design's reference to a policy the contract never names. Model
capability was **above the bar on both arms** — the weaker probe mis-transcribed file paths and still
detected every trial it completed. Observable resolution stayed at **one bit per trial**.

Chasing a weaker model would optimise for failure rather than for measurement. The remaining move is to
raise the resolution of what is measured.

### E19.1 The unit: several independent obligations, each graded exactly as before

A scenario carries `K` planted properties instead of one. A trial produces a **vector** of per-property
verdicts, each one the same narrow semantic question V1 already asks — *does this report identify this
specific problem?* Nothing about a single grade changes.

`k/K` is legitimate because it has direct engineering semantics: **the fraction of accepted obligations
the reflector actually reported**. That is review completeness, a real property of a review, not an
opinion about it. The line from `P1` holds exactly where it did — Python performs arithmetic over
semantic classifications and never produces a semantic classification of its own. There is no
`semantic_quality`, no "is this report good", and no threshold at which `2/3` becomes a pass.

### E19.2 What makes two properties independent

A scenario with three restatements of one reasoning chain measures one thing three times. Four criteria,
all checked during scenario review: each property breaks a **different** accepted requirement rather than
one requirement seen twice; a plausible fix for one leaves the others standing; a defensible report can
raise any one without the others, so noticing one does not hand over another; and the artifact text that
violates each is different text.

The anti-pattern, stated so it can be rejected on sight: *retry occurs* → *retries duplicate effects* →
*duplication breaks idempotency* is one obligation split into three bullets. Engineering independence is
the standard, not statistical independence — properties may well correlate in difficulty.

### E19.3 Realism: not a bug buffet

Ten planted mistakes measure checklist scanning. The artifact must read like something a competent
engineer wrote on a deadline: mostly sound, with a few genuine non-breaking weaknesses and a small number
of real breaches, all mechanically checkable from the manifest.

### E19.4 Grading: one independent call per property

Of the three arrangements — one call returning a vector, one call per property, or one blinded batched
call — V1 takes **one call per property**.

The reason is not cost, which favours batching; the worker dominates wall-clock by an order of magnitude.
It is that per-property calls give blindness *by construction* where batching requires engineering it.
A grader shown three properties at once can see how many there are and how many it has already credited,
and a grader that has just credited two is being invited to infer something about the third. Batching
becomes worth revisiting only after it is shown to produce the same verdicts as independent calls.

Each call receives one property statement and the report, and nothing else — not the property count, not
the other properties, not their verdicts, not the worker model, not any prior result. Grading failure
stays per-property: an ungradeable property is `grading-unavailable` on its own and does not decide the
others.

### E19.5 The trial vocabulary generalises without changing a recorded number

A trial's semantic outcome is derived from its vector: *detected* when every property is graded and
detected, *not-detected* when every property is graded and at least one is not, *grading-unavailable*
when any could not be graded. At `K = 1` these are **exactly** the original definitions, so every
existing record keeps both its numbers and its meaning and no historical run is reinterpreted (`P6`).

**Never report the scenario total alone.** `P1 5/5, P2 5/5, P3 2/5` and `12/15` are the same arithmetic
and not the same information: only the first says where the reflector is weak. Two reliability views are
both wanted — **complete-trial rate**, how often every obligation was found in one pass, and
**per-property rate**, how often each was found at all. A reviewer that finds all three once and two of
three usually is not the same as one that finds all three every time.

### E19.6 Over-reporting is observed now and measured later

A richer completeness metric invites a cheap strategy: raise every possible concern and collect the
detections. Three things already stand against it. Grading is property-specific, so a report earns a
detection only by naming *that* conflict; the negative controls showed it empirically, refusing a report
that raised all four declared distractors as findings while never mentioning the breach; and reports are
retained, so human calibration can ask whether detections were earned or sprayed.

Precision becomes a milestone when calibration observes reports combining high completeness with many
unsupported findings. Extra findings are not false positives by default — whether an unplanted finding
is valid is itself a semantic judgement, and treating "unplanted" as "wrong" would punish good review.

### E19.7 Identity: the property set defines the scenario; properties need only local names

Scenario identity covers the planted property set, because changing what a scenario asks for changes the
engineering problem — and it does so without disturbing existing scenarios: identity is computed from
the form the manifest actually uses, so a legacy single-`property` scenario hashes exactly the fields it
always did. Grader model and rubric stay outside identity.

Individual properties need stable names, not identities. The field test — *does any durable artifact
have to refer to one property across scenario versions?* — finds nothing that does, since results are
reported within a scenario version and a changed property set is a new scenario. Scenario-local
kebab-case ids suffice; a property hash would be identity created because a concept felt important.

### E19.8 Two effectiveness views, both already derivable

Calibration produced a case worth building on: the probe model mis-transcribed absolute paths, lost a
protocol file and produced no report, three times. That is neither purely an infrastructure failure nor
purely a reasoning one. Proofbound evaluates a model *operating a role*, so following supplied pointers
is part of the job, and two views answer two questions with no new state — **end-to-end role
effectiveness**, detections over *attempted* trials, and **conditional semantic performance**,
detections over *valid* trials. Report both: the conditional view alone lets a configuration that barely
ran look excellent, and the end-to-end view alone conflates a provider outage with a weak reviewer.

## E20. Two measurement problems, wrongly sequenced as one

[§E23](evaluation-comparison.md#e23-what-one-semantic-measurement-should-be) concluded that the craft
measurement unit should become per-pressure discovery frequency, and named finding consolidation as the
next blocker. That sequencing was wrong. It treats two problems as one.

**Closed-world measurement.** The semantic column is declared before the run. *"Does the code deciding
what to notify a user about need to know how a delivery provider is called?"* is fixed in the case
manifest, and each sample is asked, independently, whether its report surfaced it. The column's identity
is supplied by pre-registration.

**Open-world discovery.** No column list exists beforehand. N reports raise overlapping, broader,
narrower, causally related and contradictory concerns, and something must decide what counts as one
distinct finding before anything can be counted at all.

Only the second needs cross-sample semantic identity. The first never compares one sample with another.

### E20.1 The relation already exists

The incidence a multi-sample evaluation needs — *sample × obligation → detected / not-detected /
grading-unavailable* — is the per-property vector `semantic()` has produced since
[§E19.1](#e19-multi-property-scenarios--more-resolution-still-not-a-score), with one index added.
`trial × property` becomes `sample × pressure`. No new artifact, no new protocol noun, no new state:
the Field Test asks which invariant becomes impossible without one, and the answer is none.

It preserves what matters by construction. A pressure surfaced by one sample of ten is a cell with
`k = 1`, recorded with its provenance, not a loser of an election. Recurrence becomes *observable*
without becoming authority, because nothing downstream consumes it — `P5` and
[§53](system-craft.md#53-craft-coherence-and-the-loop-between-them) already place disposition with
the parent.

**One trap, in existing code.** `trial_verdict` collapses a property vector with a logical AND: every
property detected, or the trial is not-detected. That is correct for its original purpose and would be
silently wrong here, reintroducing the whole-report verdict this design rejects. **In a multi-sample
matrix the per-pressure vector is the result**; no collapse across pressures, and none across samples.

### E20.2 Calibration V3 is not blocked

Every step of a closed-world run is available without cross-sample identity: pressures frozen in the
manifest; one report per sample; one grading per (sample, pressure) cell, the report never shown
alongside another sample's; counts and shares computed mechanically; missing measurements recorded as
missing. There is no point in that path at which two samples meet.

Most of it is not even new code. `semantic()` already reads a `properties` list and falls back to a
single `property`, so a craft case gaining pre-registered pressures is additive fixture work that the
grading path handles unchanged; the repeated-sampling machinery — preallocated `(item, repeat)` slots, a
hash over the whole frozen configuration, atomic checkpointing and a resume that refuses to splice
across configurations — was built for `§E51` and applies without modification.

Doing consolidation first would also **contaminate the experiment**. V3's purpose is to introduce a
pre-registered architectural criterion while holding measurement mechanics fixed. Adding semantic
grouping, or changing the reflector's output contract to make grouping easier, would change the criterion
and the instrument in the same run — the mistake
[§E22](evaluation-comparison.md#e22-reliability-before-validity) was written to prevent.

### E20.3 What V3 does need first, and it is small

**A different grader, whose repeatability is unmeasured.** The 16.9% figure belongs to the craft *verdict*
grader, which asks whether a report says the property fails and answers "upheld" both when the report
says it is fine **and when it never addresses it**. A closed-world run uses the *discovery* grader
instead — *does this report identify this specific problem?* — which has run since Eval V1, is already
canonical, and does not conflate silence with endorsement. Its contract needs no design work. Its
dispersion has simply never been measured, and one grade per sample is defensible only once it has been,
against a frozen anchor corpus, exactly as `§E51` did for the other grader. That is a run, not a redesign.

### E20.4 Open-world finding identity may be the wrong goal

Six cases decide it. Wording variation and broad-versus-narrow are arguably mergeable. Common cause with
distinct consequences is not obviously one finding or two. Partial overlap loses information when merged
and inflates support when split. **Same observation with opposite interpretation** is the decisive one:
the reliability run found precisely this shape — the observation stable, the judgement split — and any
merge that produces a single canonical finding destroys the structure that was the most valuable thing
measured. And a legitimate concern raised by one reviewer of ten must survive any scheme that records
support at all.

So the question "when are two concerns the same finding?" should be answered by not asking it. Reports
retain their provenance and are read together; the parent reasons across them, which is the authority
boundary that already exists. Canonical finding identity would add a semantic stage whose own reliability
would then need measuring — a regress `P13` cannot fund and `P1` should not license, since deciding that
two novel concerns mean the same thing is exactly a semantic judgement.

Consolidation may still earn its place later as a **presentation** economy for a human reading ten
reports. That is a different justification from measurement, and it must not be smuggled in as one.

### E20.5 Three independences, kept apart

| | What it means | Status |
|---|---|---|
| **Provenance independence** | No prior report, session or semantic result contaminates a sample | Enforced today (`P12`) |
| **Statistical independence** | Errors are independent draws | **Not known, never claimed** |
| **Perspective diversity** | Evaluators bring materially different search strategies | Not part of the protocol |

External evidence makes the middle row load-bearing rather than pedantic: a panel of nine frontier judges
across seven model families was measured as carrying roughly two votes' worth of independent information,
with neither more judges nor better aggregation closing the gap. Proofbound's repeats share one model,
one prompt and one provider, so their effective independence can only be worse. **Nominal N is not
evidence strength**, and a heterogeneous panel is a different measuring system rather than a cheaper way
to raise N.

### E20.6 Coverage, and what it may not claim

Software-inspection research offers one useful reframing and one clear warning. The reframing: under
perspective-based reading, reviewers who find *different* defects are complementary rather than
disagreeing, so low overlap in a discovery task is not automatically instrument noise. It does not rescue
the reliability result, which measured contradictory judgements about an identical observation — that is
not complementarity.

The warning is capture–recapture, which estimates undiscovered defects from reviewer overlap and depends
on inspector independence and homogeneous detection probability. Both assumptions are violated here, far
more severely than in the human inspections where the technique is already contested, and the documented
failure direction is **underestimation of what remains**. It is rejected for Proofbound as anything but a
cautionary analogy.

What may be recorded is **marginal discovery**: what an additional sample adds. It is a better `P13`
observable than N, because it says what the spend bought. What it may never support is a stopping claim —
correlated evaluators fall silent together, so *"no new pressure surfaced in the last two samples under
this measuring system"* is an observation about the measuring system, and never a statement that coverage
is complete.

## E24. What it takes to call an increment an improvement

A substrate that can measure the same thing many times creates a new way to be wrong: adopting a
change because it helped one run, because a paper endorses it, or because it sounds like better
engineering. This is the discipline that makes those harder.

**"Better" is never a property of an increment.** It is a relation between a declared claim, a
declared measurand, a named baseline and guardrails, under measurement mechanics that did not move.
An increment can raise discovery, cost ten times more, lose specificity and reduce repeatability at
once; the harness reports that vector and a person decides whether the trade is worth making.

### E24.1 What a pre-registered increment declares

Before any treatment measurement exists — `_experiment.py` refuses a manifest missing any of it:

| | |
|---|---|
| **Claim** | What is expected to improve, narrowly. *"Supplying accepted consequence C increases independent discovery of pressure P"*, never *"this makes evaluation better"* |
| **Measurand** | The observable that changes, e.g. per-sample discovery frequency for `P` |
| **Baseline** | The exact previous measuring system |
| **Treatment** | The single intended change |
| **Frozen** | What must stay identical: implementation evidence, model, grader contract, budget, everything but the treatment |
| **Primary comparison** | Stated before data, so it cannot be chosen afterwards from what moved |
| **Guardrails** | What must not materially regress — false pressure on sound architectures, ungradable rate, cost |
| **Falsifier** | The outcome that would show the mechanism does not work |
| **Invalid if** | Conditions that make the run uninterpretable rather than negative |
| **Adoption rule** | Fixed in advance, and never reducible to a p-value |

Once treatment measurement begins, none of it may change. A design flaw found mid-run makes the
experiment **invalid**, and the repair is a new experiment rather than a rewritten rule — editing a
criterion afterwards is how a benchmark gets fitted to itself.

### E24.2 Paired, interleaved, and read against its own noise

Baseline and treatment run in the **same window, on the same retained implementation evidence**,
with neither arm's output ever reaching the other's evaluator. V1 and V2 were separated by days,
which is why their comparison could not be read; the substrate now interleaves arms from an order
generated before execution, so provider drift cannot line up with the comparison.

Interpretation is against same-condition variation, not against a one-shot difference. A treatment
whose observed shift is comparable to the dispersion the instrument shows when nothing changed has
**not resolved** — and *"no measurable improvement under this configuration"* is a legitimate,
publishable result, as are *"tradeoff observed"*, *"invalid experiment"* and *"regression"*. None of
them is a protocol state; they are research conclusions about a run.

### E24.3 Controls, and what they cannot prove

Structurally different sound architectures remain the specificity control, because a treatment can
raise discovery simply by making the evaluator complain more. A negative control — the same
mechanics where the pressure should not be implicated — diagnoses that bias when it fails. **It
proves nothing when it passes**, and no control is ground truth merely because someone labelled it
one; its validity is argued before data collection or not at all.

Every pressure also passes an **entailment audit** first: is the graded property actually entailed
by the authority the evaluator receives? *"Must use a Sender interface"* is a mechanism and fails
unless the mechanism is itself accepted intent; *"the code deciding what to notify a user about
does not need to know how a provider is called"* is a consequence and can be satisfied by
architectures that look nothing alike. Calibration V2 failed exactly here — the criterion was not
entailed by what the reflector was shown — and that failure mode is common enough in coding
benchmarks to be worth naming as a standing check rather than a lesson.

### E24.4 Research motivates experiments; it never authorises adoption

An external result may justify *running* something. It may not establish that Proofbound should
adopt it. The sequence is: state the mechanism, state what it predicts, identify the Proofbound
measurand, build baseline and treatment, pre-register controls, measure paired, attempt to
falsify, inspect guardrails and cost — then adopt only the local claim that survived.

Three ideas are recorded as motivated but unadopted. **Metamorphic framing** fits an oracle-less
problem: a form-preserving change should not move discovery, a consequence-violating one should
raise it, and a consequence-restoring change in a different form should lower it again — a relation
about the accepted consequence, not about resemblance, which is why it is not a golden architecture.
**Mutant adequacy** asks whether the evaluator separates deliberately constructed semantic variants
in the predicted direction, testing the evaluator rather than the implementation; mutants built
after seeing failures measure nothing. **Falsification routing** would send a semantic candidate
toward a deterministic check where one exists, so the next evaluator need not be another model —
deterministic evidence outranks semantic agreement (`P5`). None is implemented, and each would have
to win its own controlled comparison first.

### E24.5 Not fitting the benchmark to itself

One case has now motivated three milestones, and repeatedly editing an instrument against the
fixtures that exposed its faults turns those fixtures into training data for the research process.
The discipline is a split, not a bigger benchmark: evidence used to *understand* failures and design
a treatment is development material, and a claim of general improvement may not rest only on it. A
small holdout that was not inspected while the treatment was designed is worth more than a large
contaminated corpus, and `P13` makes the small one affordable. No claim generalises past the one
domain that produced it.

Statistics stay out unless their assumptions hold, for the reasons
[§E23](evaluation-comparison.md#e23-what-one-semantic-measurement-should-be) already gives: exact
paired counts, per-cell distributions, discordant direction, missingness, control behaviour and cost
come first.
