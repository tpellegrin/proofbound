# Evaluation — discrimination and comparison

> **Normative.** How Proofbound decides whether an evaluation suite can tell two systems apart, and what
> may and may not be claimed when two runs are compared. Read this when calibrating a suite or comparing
> configurations; read [`evaluation.md`](evaluation.md) instead when authoring scenarios or grading a
> single run. Section numbers are inherited stable identifiers and continue that document's sequence.
>
> Entry point: [README.md](README.md).

## E16. Discrimination — why baseline zero cannot compare systems

Baseline zero established that the semantic trigger works. It did not establish that the suite can tell
two systems apart, and the retained evidence explains why in a way scores alone could not.

### E16.1 The diagnosis, from trial evidence rather than from the score

The baseline's own trajectories, and what they showed about why a perfect score measured nothing, are
recorded in
[`evidence/evaluation-runs.md` §E16.1](evidence/evaluation-runs.md#e161-the-diagnosis-from-trial-evidence-rather-than-from-the-score).
The rule it produced is E16.2 below.

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

Which families were built, and in which domains, is recorded with their outcomes in
[`evidence/evaluation-runs.md` §E16.5](evidence/evaluation-runs.md#e165-candidate-scenario-families).
Inventory is evidence; the dimensions above are the protocol.

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

## E21. The P12 control — does withholding the author's reasoning help?

The multi-property suite finally has headroom: 25/27 and 26/27 obligations, 7/9 and 8/9 complete
trials, with one obligation repeatedly missed by both configurations. A causal experiment can now
produce a difference instead of tying at ceiling, which is the condition E16.8 set.

### E21.1 What `P12` actually claims, and which half has never been tested

Canonically: *fresh independent evaluation at semantic boundaries, and evaluators do not inherit the
execution context that produced what they judge* — because *an evaluator carrying the reasoning that
produced a change cannot independently assess it*. Its falsifier is an evaluator **handed the
execution narrative of the work it evaluates**.

That is two claims, and Proofbound enforces only the first:

| Limb | Status |
|---|---|
| **Execution freshness** — the evaluation is a separate, later attempt | Mechanically enforced. `_assert_fresh_reviewer` requires the reviewer's launch to postdate every project-mutating attempt on the same contract |
| **Informational independence** — the evaluator does not receive the reasoning that produced the artifact | **Never enforced and never tested.** It holds by construction: a fresh worker gets pointers to accepted artifacts and a contract, and nothing hands it the author's narrative |

The second limb is a design choice nobody has ever measured. This experiment measures it.

### E21.2 Freshness and independence are not the same variable

They are routinely conflated and must not be here. **Freshness** is a property of the execution: a
new process, a new session, no carried conversational state. **Independence** is a property of the
information: whether the evaluator receives the reasoning that produced what it judges. A fresh
execution can be handed an author's narrative; a resumed session can carry reasoning without any
document naming it.

**Both arms are fresh executions.** Only the information differs. The rationale-exposed arm is
therefore *not* "the non-fresh arm", and calling it that would describe an experiment nobody ran.
Freshness is held constant; independence is varied. Session reuse — the other way to vary this — is
not used, and would in any case be blocked by the OpenCode session-lookup gap recorded in E16.10.

### E21.3 The mechanism under test is architectural, not psychological

Proofbound never claimed anything about cognition, and the experiment should not smuggle one in. The
architectural claim is narrow: an evaluator that receives the reasoning which produced an artifact
tends to re-derive that reasoning rather than independently deriving what the accepted context
requires. The observable consequence is specific — **obligations the author's reasoning path talks
around go unreported**, while obligations it never touches are unaffected.

The architecture already asserts this about its own orchestrator: the parent *"is the least
independent evaluator in the system — it has been present for every decision and is maximally
contaminated by exactly the execution context"*. The control tests that same claim where it can
actually be measured.

### E21.4 The treatment is an artifact the system already produces

The author's reasoning is not an invention for this experiment. The shipped spec-author protocol
instructs an author to *"report what you wrote, the decisive reasoning behind consequential
choices, what you verified against the repository, and any unresolved question"* — an attempt report
that is, in P12's own words, the execution narrative of the work.

And supplying it is already expressible. `--input` exists to hand a worker exact run artifacts;
production uses it to give the Evidence Clerk a source report and its gate, and DSD's own test suite
passes an implementer's report to a *reviewer* the same way. Nothing prevents a parent doing this for
a reflector — Proofbound's current default simply does not.

So the experiment compares **current behaviour against a supported alternative a parent could choose
today**, which is what makes it an architectural question rather than a benchmark trick. The
treatment is a frozen synthetic spec-author attempt report per scenario, written to the role
protocol's own description of what such a report contains.

### E21.5 Constructing a rationale that anchors without cheating

Four rules, because the treatment is where this experiment is easiest to corrupt.

- **Plausible, never adversarial.** It explains mechanisms and tradeoffs as a competent engineer on a
  deadline would. No lie, no instruction to the reviewer, no stated conclusion about correctness. A
  rationale that says *"ignore availability concerns"* would test obedience to persuasion, which is
  not `P12`.
- **Blind spots preserved.** It must explain why the artifact is as it is **without ever naming the
  accepted obligation it breaks**. For the migration design it may argue for a single coordinated
  deploy to avoid mixed schema versions; it may not mention an interval with nothing serving, which
  would hand over the obligation.
- **It should discuss the declared distractors as things it considered.** This is realistic, involves
  no dishonesty, and is precisely the anchoring surface: a narrative that visibly canvassed several
  concerns invites a reader to believe the space was covered.
- **Mechanically leak-checked.** The existing per-property check runs against the treatment artifact:
  no distinctive run of any planted property statement may appear in it. Human review confirms the
  rest, and every treatment artifact is **frozen before the first trial**.

### E21.6 The rationale never becomes engineering authority

It is experimental context and nothing else. It is not an accepted artifact, never enters the ledger,
never becomes a graph dependency, is never frozen as engineering intent, and no artifact's validity
depends on it. The reflector is free to reject every word of it. The accepted proposal and design
remain the only authority in the scenario, exactly as before.

### E21.7 The context confound is real, deliberate, and bounds the claim

The rationale-exposed arm receives more material. If it performs worse, anchoring is one
explanation and additional context load is another, and two arms cannot separate them.

That is accepted, because the decision Proofbound faces is operational: **should a parent hand a
fresh reflector the authoring attempt's report?** The alternative to supplying it is supplying
nothing — there is no neutral filler in the real system, and inventing one would measure a
configuration the product will never run. A matched-neutral-context arm answers a different
question, one the architecture does not currently need decided.

Two things bound the confound without a third arm. The treatment is small against what is already
supplied — roughly 17.5 KB of rules, protocol and contract — and the ratio is recorded, so
"attention dilution" can be judged rather than asserted. And the per-obligation vector gives a shape
test worth **pre-registering**: diffuse context load should depress detection roughly evenly across
obligations, whereas anchoring should preferentially depress the obligations the rationale reasons
around. That is not proof, and it is not the primary outcome; it is a discriminating observation
recorded before any result exists.

### E21.8 Treatment binds to the run; the engineering scenario is untouched

Verified rather than assumed: a file placed **beside** `fixture/` in a scenario directory leaves
scenario identity unchanged, and the same file placed **inside** `fixture/` changes it. The treatment
artifact therefore lives beside the fixture and is copied into the run tree at launch, so the three
frozen multi-property scenarios keep the identities their screening recorded.

The run binds the exact bytes through `system.author_report_sha256`. Field test: without it, two
control runs using different author reports produce identical system metadata and look like the same
experiment. State test: the **arm label is derived**, not stored — a run is the fresh arm exactly
when it carries no author report — so no `arm` field is persisted, the same discipline that keeps
`provider` derived from the model identifier.

Scope is unaffected: the launcher excludes `DeepSeekAndDestroy` from the scope baseline and the run
root must live under it, so a treatment artifact in the run tree cannot make the reflector look like
it mutated the project.

### E21.9 Two changes the comparison substrate needs first

Found by inspection, and both would silently misreport the experiment:

- **`controlled` hardcodes the model as the only legitimate variable** (`differing == ["model"]`). A
  `P12` control varies the treatment and holds the model fixed, so it must generalise to *exactly one
  comparison-relevant field differs*, with the render naming which one.
- **Absent currently means "unknown", not "no treatment".** `configuration_diff` marks a field
  recorded by neither run as unverified and excludes it from the difference. If the fresh arm stored
  a null treatment, `compare` would report that nothing material differs — for the one comparison
  where the treatment is the whole point. The fresh arm therefore records an explicit "no author
  report" value rather than an absence.

With both, `compare` **proves** the two runs differ only by treatment instead of taking it on trust,
which is why no `controlled: true` is ever persisted.

### E21.10 The experiment

| | |
|---|---|
| Population | All three frozen multi-property scenarios, all nine obligations. Not the weak obligation alone — selecting on a prior outcome would build the result in |
| Worker | One configuration: `opencode/nemotron-3-ultra-free`. Continuity with every prior measurement, and — decisively — it exposes no reasoning-effort variants, while the alternative runs at an unpinned provider default. A causal experiment should not carry an uncontrolled variable it can simply avoid |
| Grader | Unchanged: `opencode/big-pickle`, one blind call per obligation, never told the arm, the hypothesis, the other arm's results, or the worker model. Reports are compared mechanically afterwards, never by the grader |
| N | **5 trials per scenario per arm** — 30 worker trials, 90 property classifications. Fixed before execution |
| Ordering | Arms alternate within each repetition, deterministically and fixed in advance, so provider drift over a multi-hour run cannot align with an arm |
| Isolation | Every trial gets a fresh temporary tree, fresh Git state, fresh run root. No session, conversation, run tree, report or grader output is ever reused, across arms or within one |
| Primary outcome | **Obligations detected over gradeable opportunities**, chosen because it yields 45 observations per arm rather than 15 and states completeness directly |
| Secondary | Per obligation, per scenario, complete-trial rate, and end-to-end effectiveness against conditional completeness |
| Stopping | Run the full matrix. Stop early only for provider unavailability, a harness defect that invalidates trials, grader calibration failure, or discovered treatment leakage — **never** because a difference has appeared, and never extend N because one has not |

Both arms receive identical worker timeouts, grader timeouts, tool permissions and budgets. If the
rationale-exposed arm times out or misuses paths more often, that is a result of the treatment and is
reported as such, not quietly reclassified as infrastructure.

### E21.11 What each outcome would mean

**Fresh higher.** Under this frozen configuration, withholding the author's report produced higher
observed semantic completeness than supplying it. That supports the current operational choice. It
does **not** establish anchoring as a mechanism, that independence improves reasoning generally, that
context is harmful, or that all author rationale is harmful.

**No difference.** No observed benefit from withholding, under this configuration. `P12`'s
informational limb would then be an untested convention rather than a demonstrated one — worth
saying plainly.

**Rationale-exposed higher.** Genuine counter-evidence, to be reported as such. Author reasoning can
legitimately carry intent, rejected alternatives and constraints that help a reviewer. The
architecture may eventually need a sharper principle — *independent judgement need not mean
information deprivation* — distinguishing author reasoning **as authority**, which stays dangerous,
from author reasoning **as non-authoritative evidence**. A third arm supplying the rationale with an
explicit instruction to challenge it would separate those, and is deliberately **not** part of this
experiment because it would change the reflector's prompt and thus the system under test.

No result rewrites `P12`, and none changes a runtime default. Evaluation supplies evidence; an
accepted architectural decision is what would change the product.

## E22. Reliability before validity

Every evaluation this repository has run asked whether an instrument was *right*. None had asked
whether it says the same thing twice. Calibration V2 forced the question by accident: re-measuring
thirteen implementations with byte-identical inputs, the craft instrument agreed with its earlier
judgement nine times and **disagreed four**. That is larger than the treatment effect the
experiment existed to detect, which makes the treatment result — and every comparison of that size
— unreadable.

The two questions are independent, and conflating them is the standard failure:

| | Question | Failure it hides |
|---|---|---|
| **Reliability** | Does repeated measurement of the same input produce the same result? | An instrument whose answer is partly a coin flip, so small differences are noise |
| **Validity** | Is the instrument measuring the property we intend? | An instrument that is consistently, repeatably wrong |

Neither implies the other, and the asymmetry matters in one direction: **improved repeatability is
never evidence of validity**, while poor repeatability makes validity claims of small magnitude
unmeasurable. The external literature reaches the same place from the other side — judges have been
observed with test–retest reliability above 0.99 while carrying severe position bias, so
"consistent" and "correct" are separate axes and reporting only the first misleads.

### E22.1 What a repeatability claim may say here

**Test-retest under frozen Proofbound configuration**, not laboratory repeatability. VIM's
*repeatability condition* requires the same procedure, operators, measuring system, operating
conditions and location, replicated over a short period. Proofbound can hold every one of those it
touches — identical prompt bytes, one machine, one harness version, one short window — and cannot
hold the one it does not own: `opencode run` exposes neither temperature nor seed, and providers
serve models behind aliases. A run therefore reports repeatability under the configuration it can
actually freeze, and says so.

A comparison across days, as V1↔V2 was, is weaker again: same laboratory, longer period, conditions
possibly changed. That is **intermediate precision**, and pooling it with a same-window series
would overstate both.

### E22.2 Measure the layers, never one number

A semantic evaluation has more than one stochastic stage, and a single end-to-end repeatability
figure cannot say which one moved. Proofbound separates them:

| Layer | Held fixed | Repeated | Reads |
|---|---|---|---|
| **G** | report bytes | the grader | how stable the judge is on text that does not change |
| **R** | architectural evidence | the reflector | how stable the reasoning is on evidence that does not change |
| **E** | architectural evidence | reflector, then one grade | what a user of the instrument actually experiences |

Layer R needs a reading of report *meaning*, and the tempting solution — a second model comparing
reports — would add a third stochastic measurement rather than resolve one. Textual similarity,
lexical overlap and embeddings are all worse: they measure prose, not architectural claim. The
resolution is bounded human coding against a rubric declared before the reports are read,
explicitly analysis-only — it never overrides a grader output, never becomes ground truth, and
never enters the benchmark.

E is not the sum of G and R. A grader that requires an explicit claim will read a hedged criticism
as "upheld", so it **compresses** reflector variation: an end-to-end figure can look calmer than
the reasoning underneath it. That is a reason to report all three, not to prefer the flattering one.

### E22.3 The rule this produces

> **Do not interpret a difference smaller than the instrument's own measured variation under
> identical conditions.**

Not a significance test and not a power calculation — at these sample sizes both would import
precision the evidence does not have. It is a floor: before an arm-to-arm difference means
anything, the same measurement must be repeated on unchanged input often enough to know how much
it moves on its own. An evaluation that has never done that cannot claim an improvement, because
it cannot distinguish one from a redraw.

Two disciplines follow, and both are cheap:

- **Missing measurements are missing.** A failed call and an unparseable answer are infrastructure
  facts. Counting either as a semantic outcome manufactures disagreement, so execution reliability
  is reported separately from semantic dispersion.
- **Report the distribution, not the majority.** "Ten of fifteen upheld" is the result; "upheld" is
  the result with the finding deleted. Whether repeated judging should later be *aggregated* is a
  design question, and aggregating during measurement would destroy the evidence needed to answer
  it.

Evidence: [§E51](evidence/evaluation-runs.md#e51-craft-instrument-repeatability--both-layers-move).
