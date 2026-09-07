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
