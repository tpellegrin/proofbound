# Evaluation and regression

> **Design track, not implemented.** How Proofbound measures whether its agent pipeline actually works,
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
