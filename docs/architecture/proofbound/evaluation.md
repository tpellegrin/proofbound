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

## E16. Discrimination — why baseline zero cannot compare systems

Baseline zero established that the semantic trigger works. It did not establish that the suite can tell
two systems apart, and the retained evidence explains why in a way scores alone could not.

### E16.1 The diagnosis, from trial evidence rather than from the score

Nineteen of the twenty trials executed an **identical six-call trajectory**: read the four files the
launch prompt names (worker rules, common protocol, reflector role, contract), read the two engineering
artifacts, write the report. The twentieth tried to do more — it globbed for `**/*.py`, `**/*.ts` and
`**/*.go`, matched **nothing**, listed the project root, read `PLAN.md`, enumerated `specs/`, found the
two files it had already read, and wrote its report.

That trial is the finding. A reflector that went looking discovered there was nothing to find.

The supply confirms it. Each trial received ~17.5 KB, of which the **engineering problem is 1,101 bytes**
— a 526-byte design and a 575-byte proposal — plus a 408-byte contract that names both of them by path.
The remaining ~16 KB is Proofbound protocol, including role protocols for eleven roles the worker will
never play.

So every scenario reduces to: *compare two short documents you have been handed, in which one states
constraints in imperative form and the other states a mechanism.* Detection needs no retrieval, no
traversal, no prioritisation and no synthesis. Reports were substantive — ~3 KB, half of them raising
several findings — so the reflector is doing real work. The work simply has no room to vary.

**Both explanations are true and the suite cannot separate them.** The model is competent, *and* the
scenarios are near-trivial. That is precisely the property that makes the suite non-discriminative:
under these fixtures every candidate configuration receives the same effective input, so no
configuration can score differently. A raw model handed the same two documents has everything the
Proofbound reflector had.

### E16.2 What discrimination means here

Not "harder". The narrowest definition that unblocks the next question:

> A scenario is **discriminative** when configurations that differ in something Proofbound controls
> produce materially different detection rates on it.

The corollary is the actionable design rule, and it is what the current suite violates:

> **The information needed to detect the planted property must not be fully contained in a fixed set of
> documents the contract names.** When it is, the pipeline is not on the causal path, and no intervention
> in it can be measured.

Discrimination is a property of the scenario, not of the score. A scenario that everything passes
discriminates nothing; so does one that everything fails.

### E16.3 Difficulty is engineering structure, never obscurity

Legitimate difficulty and benchmark trickery both lower scores, and only one of them is informative. The
boundary, stated so a scenario can be rejected against it: difficulty must come from the **structure of
the engineering relationship**, and the property must remain fully derivable from the supplied
authoritative context by a competent engineer who knows nothing the reflector could not know.

Excluded, permanently: missing required context; deliberately confusing wording; dependence on trivia or
specialist outside knowledge; burying the constraint in bulk purely to tax retrieval; evaluator-only
facts; and any property satisfied by exactly one phrasing. A scenario that needs a trick is not a hard
scenario, it is a broken one.

### E16.4 Three dimensions, chosen because Proofbound is on their causal path

Many difficulty dimensions exist. These three are selected by one filter — *could a change in Proofbound
plausibly change the outcome?* — which is the only filter that serves E16.2.

| Dimension | What it adds | Why this one |
|---|---|---|
| **Dependency distance** | The binding constraint lives in an artifact the contract does *not* name; reaching it requires one traversal from the named artifact | Proofbound ships a dependency graph and a ledger. Nothing has ever evaluated whether that structure helps a reflector find the constraint that governs. It is also the dimension that creates genuine variance: a reflector may or may not traverse. |
| **Competing valid concerns** | Several genuine weaknesses exist; exactly one breaches accepted intent | Attacks the current "one salient issue, inert filler" shape directly, and defeats lexical-overlap shortcuts. It also stresses the grader in the way that matters: a report finding three real problems and missing the planted one must not earn credit. |
| **Indirect implication** | Neither document contains the conflict verbatim; it follows from consequences | Kills the sentence-to-sentence route that 19 of 20 trials could take. |

Deliberately **not** treated as difficulty dimensions: negative requirements, temporal semantics and
quantitative bounds. Those are subject-matter flavours worth having for diversity, but they do not by
themselves put the pipeline on the causal path — a quantitative conflict between two named documents is
still a two-document comparison.

### E16.5 Candidate scenario families

Four were built, each in a different ordinary engineering domain and none in Proofbound's own
vocabulary — a benchmark about Proofbound would measure familiarity with Proofbound.

| Scenario | Dimension | Shape |
|---|---|---|
| `retention-transitive-conflict` | dependency distance | The reviewed specification is consistent with the design the contract names; the limit it breaks lives in a retention policy that design depends on and the contract never mentions. |
| `crowded-availability-review` | competing concerns | Four defensible weaknesses and one actual breach of an accepted single-zone-loss requirement. Detection means prioritising the breach over the merely imperfect. |
| `freshness-batching-conflict` | indirect implication | A thirty-second batching interval and a two-second visibility commitment: individually reasonable, jointly impossible, and stated by no sentence in either document. |
| `pattern-versus-authority` | dependency distance | The design chooses its credential handling only *by reference* to the estate's existing clients, so whether it satisfies the accepted rotation requirement can be decided only by reading their code. Tests `P11` — repository patterns are evidence, never authority. |

A fifth family, a **plausible repair trap** (the artifact applies a textbook workaround that breaks an
accepted guarantee), was designed and not built: `adversarial-weaken-upstream` already occupies that
shape, and four candidates is enough to screen.

### E16.6 Eligibility is decided before outcomes are seen

The obvious failure of a calibration milestone is selecting scenarios because the current model failed
them, which manufactures difficulty and quietly tunes the suite against one model. Eligibility is
therefore fixed in advance, and **"the model missed it" is not on the list**:

1. the property is genuinely implied by the supplied authoritative context;
2. the obligation is narrow and not a matter of taste — a competent engineer would agree it is a breach;
3. several different phrasings satisfy it;
4. no evaluator-only fact is required, and the existing leak check passes;
5. the grader's calls agree with human reading on the screening sample;
6. **and either** the scenario shows non-ceiling behaviour under a legitimate weaker configuration
   **or** it targets an invariant worth holding as regression coverage.

Criterion 6 is deliberately shaped so that a scenario qualifies by having *range*, not by defeating the
current system. A scenario the current configuration also fails most of the time is a candidate for
being ambiguous, not for being valuable.

### E16.7 Calibration probes are not baselines and not control arms

Three concepts that must not merge:

- A **calibration probe** runs a candidate scenario against a deliberately different system-under-test
  configuration to find out whether the scenario has dynamic range. It answers a question about the
  *instrument*.
- A **control arm** varies one thing in Proofbound to test a causal claim about the *architecture*.
- A **baseline** is a measurement of the shipped configuration, recorded for comparison.

V1's fix to model propagation is what makes probes possible at all: changing `state.worker_runtime.model`
now actually changes the model that runs, and nothing else in the pipeline moves with it. A probe is
therefore a legitimate configuration, not a crippled one — which is the line that matters. **Degrading
the reflector prompt, withholding required context or breaking freshness to manufacture misses is
forbidden**; those change the system under test rather than measure the scenario.

Probe results are calibration evidence about a scenario. They are not committed as baseline summaries,
and they never become a model leaderboard.

### E16.8 Calibration must precede the control arm

E10 deferred the control arm until detection was observed at all. That trigger fired. A second condition
is now visible that E10 could not have known, because it comes from E16.1:

> A control experiment is only informative on scenarios where the intervention could change the outcome.

On the current four, every arm — independent reflector, contaminated reflector, raw review — receives the
same 1.1 KB of engineering content, so the expected result is a tie at ceiling. A tie would be read as
*independence does not matter*, when it would only show that the suite cannot see independence. The
failure mode is asymmetric: the ceiling can falsely acquit the architecture, so scenario range must be
established first.

**Readiness to run the control experiment**, in evidence rather than in scores:

1. at least three retained capability scenarios exercising at least two of the E16.4 dimensions;
2. at least two of them show non-ceiling behaviour under a probe configuration while the shipped
   configuration still mostly detects — dynamic range, not induced failure;
3. grader and human agree on the screening sample, with no unresolved disagreement;
4. no leakage and no ambiguity in the retained set;
5. the four V1 scenarios still detect at their anchor rate;
6. `system.harness_version` is recorded, so the calibration run and the control run are machine-comparable.

**The causal hypothesis the control will test**, named now so calibration can aim at it: *does a reflector
carrying the author's rationale detect the planted contradiction less reliably than a fresh independent
one?* — the direct test of `P12`. Fixed: scenario, model, provider, harness, budget, tool availability,
grader and rubric. Varied: whether the author's rationale is supplied. The contaminated arm is
expressible today through `--input`, which adds the artifact and its SHA-256 to the launch prompt and
requires it inside the run root; it needs **no session resume**, which matters given E16.10.

### E16.9 Harness version is a comparability defect, and the fix is one field

The summary records `harness: "opencode-cli"` and no version. Applying the field test — *without it, can
two materially different execution environments produce identical system-under-test metadata?* — the
answer is yes: OpenCode 1.18.29 and a future stable release are indistinguishable in the record, and the
only trace is prose in E15. That justifies the field.

- **Source.** The invoked executable's own version output, taken once where the harness is already
  resolved. Never inferred from `opencode-cli`, and never from whatever binary happens to be installed
  when a record is later read.
- **Scope.** Once per run, not per trial. A baseline is one frozen configuration by construction; a
  per-trial field would imply it may drift mid-run.
- **Absent means unknown.** Not "assume current". A harness that cannot report a version records null.
- **Not part of scenario identity.** It is evaluation configuration (E5), not engineering content (E3);
  it changes run comparability and leaves every scenario identity untouched.
- **No format bump.** `load` validates only the format string and `render` reads system fields
  defensively, so an additive optional key is backward compatible. `proofbound-eval-summary-v1` stays.
- **Historical records are not backfilled.** Writing `1.18.29` into the committed V1 summary would
  disguise a later human annotation as a machine observation — exactly the historical-semantics error
  `P6` exists to prevent. Baseline zero keeps its record as written; its harness version lives in E15.

### E16.10 Two limits recorded rather than fixed

**Session lookup.** Under OpenCode 1.18.29 `opencode session list` returned nothing even against a
database that had hosted sessions, so `session_id` was null in all twenty attempts. No trial needed it,
every attempt exited 0, and the control arm in E16.8 is file-based, so nothing planned depends on it.
It is recorded and deferred; it becomes a prerequisite only for an experiment that genuinely requires
resumed or shared session state, and none is scheduled.

**Model aliases.** `opencode/nemotron-3-ultra-free` is a name, not a pinned deployment, and the harness
exposes no fingerprint for what a name currently serves. Model string plus harness version plus timestamp
bound the environment; they do not reproduce it. The target is historically interpretable evidence, not
bitwise reproducibility, and provider fingerprinting is not worth building.

### E16.11 Baseline zero and the scenarios that produced it are immutable

The four V1 scenarios are not edited to become harder. `_scenario.py` already gives the clean model:
identity is derived from content and the scenario id is its directory name, so **a new scenario is a new
directory**, with a new id and a new identity, and nothing mutable is introduced. New difficulty arrives
as new scenarios beside the old ones.

The original four keep their 5/5 anchor and become regression coverage — which is what a scenario with a
known-good rate is for. Their `kind` labels record intended purpose, not measured difficulty, and are
left alone; one honest note is that `adversarial-weaken-upstream` is labelled capability but announces
its own violation in prose (*"restated here as best-effort… a reasonable relaxation"*) and was the
fastest of the four, so it behaves as a regression anchor. No directory split into `regression/` and
`capability/`: the `kind` field already carries the distinction, and at this size separate trees would
buy nothing but churn.

## E17. Comparing models without building a leaderboard

Calibration produced Proofbound's first comparison of two models. That capability is useful and easy to
misuse, so its limits are protocol rather than etiquette.

### E17.1 A ranking is a sentence with conditions in it

The claim an evaluation may support has a fixed shape:

> On suite `S`, under configuration `E`, model `A` showed higher observed semantic reliability than
> model `B`.

Never *model A is better than model B*. The same model may rank differently for a spec-author, an
implementation reviewer or a fixer; on another scenario distribution; under another harness, provider,
budget or grader. Model choice is role- and workload-dependent, and a sentence that drops the conditions
has dropped the evidence.

### E17.2 A comparison is derived, never stored

Two ordinary run summaries already hold every fact, so `pb_eval compare` computes and prints; it writes
nothing. There is no comparison identity, no ranking record and no leaderboard: by the state test,
nothing in a comparison fails to recompute from the two summaries it names, and a persisted copy would
be a second place for the same facts to live and eventually to disagree.

### E17.3 What must be equal before a difference means anything

Configuration is reported before counts, because a reader can only attribute a difference to the model
if nothing else moved. A comparison is **controlled** only when both runs evaluated the same scenario
*identities* and exactly one recorded field differs. Everything else is still evidence, and says of
itself that it is not a single-variable comparison.

- **Scenario population is matched by identity, not by name.** Two runs over different scenarios are
  two measurements of different things, however similar their names.
- **A field neither run recorded is unverified, not agreement.** Two summaries that both predate
  `harness_version` are not thereby known to have used the same harness release.
- **Provider is derived from the model identifier, not stored.** When the provider changes along with
  the model, model capability and provider behaviour are no longer separable, and the comparison says
  so.

### E17.4 Counts, stratified; no composite, no winner

Results are reported per scenario and grouped by `kind`, so easy regression anchors cannot dominate a
headline number and hide the capability scenarios carrying the signal. There is no weighted score, no
`winner`, and no automatic promotion — a model that scores better does not become a default, because
**evaluation evidence is not architecture authority** (E10). Choosing a model is an accepted decision
made by a human with the vector in front of them.

Resource dimensions — duration, prompt bytes, supplied bytes — are reported beside semantic outcomes and
never combined with them. A cheaper model that misses more is not "worse by 12%"; it is a different
tradeoff, and which side of it a deployment wants is not the evaluation's call.

**No ordering is computed in code.** At calibration trial counts a one-trial gap is not an ordering, and
software that turned it into one would manufacture confidence the evidence does not contain. No
significance testing either: it would dress up N=5 rather than inform it. For a review role the property
that matters is **repeated reliability**, not best-of-k — a reflector that finds the contradiction once
in five attempts has not found it.

### E17.5 Screening is not a ranking, and selection leaves a fingerprint

Low-N screening exists to choose scenarios. Its model ordering is never published as a model comparison:
it has small N, candidate scenarios, and selection effects by construction.

More important, and easy to forget later: **a suite selected because one configuration passed and
another failed is, by construction, discriminative between those two configurations.** That is exactly
what calibration is for, and it also means the resulting suite is not a neutral benchmark for unrelated
models. The configurations used during selection are therefore recorded with the suite, and any later
ranking on it inherits that provenance.

**Holdout trigger, documented and not built:** when Proofbound begins repeatedly selecting or tuning
models or prompts against known calibration scenarios, held-out scenarios become justified. Until then
they would guard against a practice that does not exist.
