# Evaluation run history

> **Historical evidence, read on demand.** What individual evaluation runs actually established, and
> where a run corrected the design. How measurement *works* is normative and lives in
> [`../evaluation.md`](../evaluation.md); nothing here defines protocol, and nothing here is
> architecture authority. Section numbers are inherited stable identifiers, so they continue the
> evaluation document's sequence rather than restarting.
>
> Entry point: [../README.md](../README.md).

## E14. Eval V1 implementation outcome

Implemented in `evals/`, with 25 deterministic harness tests in `tests/test_evals_harness.py`.
The deterministic suite never invokes a model and needs no credentials.

**Two corrections the implementation forced.**

1. **The mechanical half of the thesis was overstated.** The thesis says the pipeline routes a
   contradiction *"as findings rather than acceptance"*. Python cannot grade that: DSD has no
   machine-readable verdict, acceptance is a parent decision, and a clean gate means *safe to
   interpret*, never *the engineering passed*. So the mechanical grade is what the substrate can
   actually establish — a valid, fresh, independent, read-only reflection was delivered for
   interpretation — and whether its content warrants findings is the semantic grade. The thesis is
   otherwise unchanged.

2. **Prompt bytes are not context supplied.** The launch prompt is a *pointer list*: Proofbound hands
   the worker paths, not content. The envelope is therefore small and says almost nothing about context
   cost. V1 records `prompt_bytes` (the envelope) and `supplied_bytes` (the worker-rules snapshot, role
   protocol and task contract the launcher names) separately. Neither is a token count and neither may
   be described as one; what the worker chooses to open afterwards is not measured.

**Two things the substrate already did better than expected.** A worker that produces nothing is
classified by Proofbound itself — the gate reports `report_state: launcher-skeleton` and
`needs_report_recovery`, so the harness asks rather than applying its own emptiness heuristic. And the
`gate` CLI returns a deliberately reduced surface for parent context economy, so the harness reads the
authoritative `evidence-gate.json` for role, scope and readiness.

**Calibration** is a `calibration.json` written beside retained evidence, pairing the planted property
with the report and the grader's call — enough for a human to check a sample, with no annotation tooling.

**No live baseline was collected at implementation time.** No worker executable and no provider
configuration existed in the environment where V1 was implemented, so `run` refused with an explicit
setup failure and **no baseline was fabricated**. The first real run is recorded in E15 below.

## E15. Eval V1 baseline zero

The first live measurement. It is a *comparison point*, not a verdict: there is nothing empirical
before it, so no claim of improvement or regression can be derived from it.

**System under test.** Proofbound `b64e3cc`, role `spec-reflector`, harness `opencode-cli` on stable
OpenCode `1.18.29`, model `opencode/nemotron-3-ultra-free` (OpenCode Zen free tier), Python 3.14, five
independent trials per scenario. Every trial drove the real launcher, reservation, prompt rendering,
integrity gate and scope check; the worker executable was the real binary, not a fake.

| Scenario | Kind | Attempted | Valid | Mechanical | Detected | Missed | Ungraded | Median s |
|---|---|---|---|---|---|---|---|---|
| `adversarial-weaken-upstream` | capability | 5 | 5 | 5/5 | 5/5 | 0 | 0 | 45.8 |
| `cache-invalidation-gap` | regression | 5 | 5 | 5/5 | 5/5 | 0 | 0 | 71.0 |
| `ordering-contradiction` | capability | 5 | 5 | 5/5 | 5/5 | 0 | 0 | 106.5 |
| `retry-idempotency` | regression | 5 | 5 | 5/5 | 5/5 | 0 | 0 | 72.2 |

No setup failures and no harness failures. Median `prompt_bytes` 1211 and median `supplied_bytes`
~17.5 KB across every scenario — the envelope and the named material are effectively constant here
because the scenarios are the same shape, and neither is a token count.

**What this establishes.** Under this exact configuration, semantic detection *happens*, and it
happened in every attempted trial. That is what baseline zero was for: the deferred control arm asks
whether independence *causes* detection, and that question is only worth asking once detection is
observed at all (E10). The trigger it was waiting on has now fired.

**What it does not establish.** Not that detection is reliable — 20/20 is *observed* 20/20 at N=5 per
scenario, with no significance testing and none warranted. Not that Proofbound caused it: no control
arm ran, and a model given two short contradictory documents may well detect the conflict without any
of this machinery. Not anything about other models, other harnesses, longer artifacts, or real
repositories.

**Grader independence was model-independent, not provider-independent.** The grader
(`opencode/big-pickle`) is a different model from the system under test, invoked separately and blind
to the Proofbound version, the baseline and prior scores — but it comes from the same provider, so a
provider-level failure would correlate across both halves of the measurement.

**Grader calibration.** Every one of the twenty calls was inspected, and the classifications are
substantive: most cite the specific finding in the report that matches the planted property. Six
synthetic negative controls — style-only, unrelated-but-real, and generic-clarification reports of the
kind E9 predicts as misses — were graded `NOT_DETECTED`, including one that mentions retry behaviour
without addressing the idempotency conflict. The grader discriminates rather than rubber-stamping, so
the 20/20 is a result and not an artifact of the instrument.

**The most likely explanation to rule out next is scenario difficulty.** The fixtures are two short
documents with one planted conflict, and the capability scenarios were not measurably harder than the
regression ones — the adversarial scenario was in fact the *fastest*. A suite where everything passes
discriminates nothing, so the next measurement must be able to produce a miss.

**One environment incompatibility, recorded and not fixed.** Under OpenCode 1.18.29 the inherited
session lookup (`opencode session list --format json`) returned no output, so `session_id` was null in
all twenty attempts and DSD recorded a `session_lookup_error`. Every attempt still exited 0 with
`status: completed`, and Eval V1 never resumes a session, so no trial was affected. It does mean the
inherited `--resume-session` continuation path is untested against this OpenCode generation.

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

## E18. Calibration screening — the scenarios got harder, the suite did not separate

The calibration milestone asked one question: *can a small set of semantically valid scenarios
demonstrate non-ceiling behaviour under legitimate configurations?* The answer under this pair of
configurations is **no**, and the useful part of the answer is *why*.

**Configuration.** Both arms identical except the model. Proofbound `b036aa4`; harness `opencode-cli`
`1.18.29`; grader `opencode/big-pickle`; role `spec-reflector`; Python 3.14; three trials per scenario.

| Arm | Model | Chosen because |
|---|---|---|
| Reference | `opencode/nemotron-3-ultra-free` | The model baseline zero used, so continuity is preserved |
| Probe | `opencode/nemotron-3.5-lightning-free` | Same provider and family, plausibly weaker, and verified tool-capable before use rather than assumed |

| Scenario | Reference | Probe | Probe invalid | Signal |
|---|---|---|---|---|
| `crowded-availability-review` | 3/3 | 1/1 | 2 setup | no-data |
| `freshness-batching-conflict` | 3/3 | 3/3 | — | ceiling |
| `pattern-versus-authority` | 3/3 | 3/3 | — | ceiling |
| `retention-transitive-conflict` | 3/3 | 2/2 | 1 setup | ceiling |

**21 of 21 valid trials detected the planted property, on both arms.** No ordering between the models is
observable, and none is claimed.

### E18.1 What did land: the pipeline is now on the causal path

The V1 diagnosis (E16.1) was that nineteen of twenty trials ran an identical six-call trajectory and the
twentieth found nothing to explore. That is fixed, and the trajectories prove it:

| Scenario | Tool calls | Artifact reads | What the reflector did |
|---|---|---|---|
| `crowded-availability-review` | 7 | 2 | Two-document comparison, as designed — its difficulty is prioritisation, not retrieval |
| `freshness-batching-conflict` | 7 | 2 | Likewise: the work is inference, not discovery |
| `retention-transitive-conflict` | 8 | 3 | Followed the design's reference and read `specs/POL-002/data-retention.md` — **never named by the contract** |
| `pattern-versus-authority` | 11–17 | 5 | Ran `Glob services/**/*`, matched three files, and **read all three client modules** the contract never mentions |

E16.2's corollary — *the information must not be fully contained in documents the contract names* — is
satisfied for the two dependency-distance scenarios, empirically rather than by assertion. Median
deliberation rose from 45–106s in baseline zero to 330–650s here, on the same reference model. That is
resource evidence, not difficulty evidence, and it is not used to rank anything.

### E18.2 What did not land, and the honest reason

Detection is binary and both models clear the bar. **The probe was not weak enough** — not that the
scenarios are easy. A model good enough to run the pipeline at all appears to be good enough to find one
planted contradiction, once it is looking in the right place.

Three explanations were checked and rejected before accepting that:

- **A lenient grader.** Eight negative controls, two per scenario, were graded `NOT_DETECTED`. The
  decisive one: for `crowded-availability-review`, a report raising *all four* of the scenario's declared
  distractors as genuine findings was refused with "never mentions the single-zone dependency". A report
  can be sophisticated, correct and still not a detection.
- **Leakage.** The property reaches neither the launch prompt nor any fixture file; checked at load and
  again against captured prompts.
- **Invalid trials inflating a rate.** They cannot: the taxonomy separates them, and the retention rule
  compares detection rates over *valid* trials.

### E18.3 The probe's setup failures are operational evidence

Three of twelve probe trials produced no report. The cause is specific and worth recording: the probe
**mis-transcribed the long absolute paths** the launch prompt supplies — `pb-ebok-…` for `pb-eval-…`,
and truncations — so OpenCode auto-rejected the read as an external directory and the worker continued
without its protocol file and never wrote a report. The reference model, reading the same prompt, used
relative paths throughout.

Proofbound classified these correctly as setup failures via its own `report_state: launcher-skeleton`,
so none became a semantic miss. **Not fixed here**: changing how the prompt names files would modify the
system under test in the middle of calibrating the instrument. It is a real fragility of the pointer-list
prompt under weaker models, exaggerated by the evaluation's deep temporary directories, and it belongs to
a later task.

### E18.4 Retention, and the bias the null result avoids

Applying the pre-registered rule (E16.6), **no scenario was retained on the discrimination limb**: three
ceilinged and one had too few valid probe trials to judge. All four stay in the tree under the rule's
second limb — valid, unambiguous, non-leaking, and exercising reasoning structures the original four
cannot — as **coverage, not as demonstrated discriminators**, and must not be described as such.

One good consequence: because nothing was selected on outcome, the suite carries **none** of the
selection fingerprint E17.5 warns about. It is not tuned toward this configuration pair, and a future
comparison on it does not inherit that bias.

**The repeated retained-suite measurement was not run.** With 21/21 across a validated grader, five
trials per scenario per arm — roughly forty trials and several hours of provider time — would add
precision to a null result rather than change it. E16 already says a ceiling tie is a valid outcome to
stop and report on.

## E20. Multi-property screening — the observable finally moved

The first evaluation run in three milestones that is not at ceiling. Adding independent
obligations changed what the measurement can see; it did not separate the two configurations.

**Configuration.** Identical but for the model. Proofbound `45ebac4`; harness `opencode-cli`
`1.18.29`; grader `opencode/big-pickle` for both arms; role `spec-reflector`; Python 3.14; three
scenarios, three planted obligations each, three trials per scenario per arm.

| Arm | Model | Provider |
|---|---|---|
| Reference | `opencode/nemotron-3-ultra-free` | `opencode` (OpenCode Zen) |
| Alternative | `deepseek/deepseek-v4-flash` | `deepseek` (api.deepseek.com, paid, user-authorised) |

| Obligation | Dimension | Reference | Alternative |
|---|---|---|---|
| `checkout-obligations` / `retry-moves-money-twice` | direct | 3/3 | 3/3 |
| `checkout-obligations` / `ledger-pinned-to-one-region` | indirect-implication | 3/3 | 3/3 |
| `checkout-obligations` / `diagnostic-copies-outlive-policy` | dependency-distance | 3/3 | 3/3 |
| `session-lifecycle-obligations` / `refresh-outlives-revocation` | indirect-implication | 3/3 | 3/3 |
| `session-lifecycle-obligations` / `credential-in-analytics-tier` | dependency-distance | 3/3 | 3/3 |
| `session-lifecycle-obligations` / `header-drop-breaks-old-clients` | direct | 3/3 | 3/3 |
| `migration-obligations` / `column-removed-too-early` | direct | 3/3 | 3/3 |
| `migration-obligations` / `runbook-makes-reversal-impossible` | pattern-versus-authority | 3/3 | 3/3 |
| **`migration-obligations` / `all-at-once-rollout`** | **indirect-implication** | **1/3** | **2/3** |

Obligations: **25/27** and **26/27**. Complete trials: **7/9** and **8/9**. No setup failures, no
harness failures, no ungraded properties, mechanically valid throughout.

### E20.1 What the extra resolution actually bought

Every trial here would have scored *detected* under the single-property observable, because every
trial found at least one planted contradiction and most found all three. The suite would have
reported 18/18 for a third time and learned nothing.

The decisive case is one obligation deep inside a scenario the reflectors otherwise handled
perfectly. `migration-obligations` plants two obligations that a reader could reach through the
same sentence — the design deploys every instance at once, which both breaks readers still on the
old release *and* leaves an interval with nothing serving. Reports repeatedly reasoned about that
sentence for the compatibility reason and never for the availability one, and the grader credited
the first obligation while refusing the second. One report's finding F1 quotes the rollout
directive, argues it correctly, and is still `NOT_DETECTED` for the downtime obligation, because
that is not the argument it made.

**A single-property suite cannot express that distinction at all.** It sees a report that
discussed the right sentence and scores a detection. Property vectors separate *which* obligation
a reviewer reasoned about from *which text* it happened to quote, and that is the resolution the
previous two milestones were missing.

### E20.2 Configurations: no observed ordering

25/27 against 26/27, and 7/9 against 8/9, at three trials per scenario, is not an ordering. Both
arms converge on **the same** weak obligation rather than failing different ones, so there is no
failure-profile separation either — which is itself informative: the difficulty appears to be a
property of the obligation, not of the model.

The comparison is otherwise controlled — same Proofbound commit, harness, harness version, grader,
role, runtime and scenario identities — with one honest exception: **the provider changed with the
model**, from OpenCode Zen to DeepSeek's own API, so model capability and provider behaviour are
not separable here. `pb_eval compare` derives and prints that rather than letting it pass.

Two further limits on the record. Proofbound's worker invocation passes no reasoning-effort
variant, and `deepseek-v4-flash` exposes `low`/`high`/`max`, so the alternative arm ran at an
unpinned provider default — the same class of residual uncertainty as a model alias (E16.10).
And the alternative was roughly six times faster (medians 53–64s against 306–408s), which is
resource evidence reported beside the semantic outcome and never combined with it.

### E20.3 The grader was checked, not trusted

Completeness only measures completeness if a sophisticated report cannot collect credit it did not
earn. The control that matters for a multi-property suite was run against the live grader on two
scenarios: a report stating two obligations correctly *and* raising all four declared distractors
as genuine findings was credited for the two and **refused on the third**, both times. The live
trials show the same discrimination unprompted, in the migration case above.

### E20.4 What was not established

Not that the suite separates capable models — it did not, here. Not that three obligations is the
right number. Not that `all-at-once-rollout` is hard for models in general rather than hard in this
scenario. And nothing about any role other than `spec-reflector`, any harness other than this one,
or any workload beyond these three synthetic reviews.

## E21.A The P12 control — result

The first causal test of `P12`'s informational limb. Both arms are fresh executions; the treated
arm additionally receives a frozen spec-author attempt report through `--input`. Everything else
is identical, and `pb_eval compare` confirms it: **only `treatment` differs**.

**Frozen configuration**, pre-registered before the first official trial. Proofbound
`5b440517de60e7076866de248f55e92876f830cf`; `opencode/nemotron-3-ultra-free` on `opencode-cli`
`1.18.29`; grader `opencode/big-pickle`, one blind call per obligation; role `spec-reflector`;
Python 3.14; three scenarios × two arms × **5 trials** = 30 trials, 90 property classifications;
arm blocks counterbalanced (untreated at positions 1, 4, 5; treated at 2, 3, 6). Primary outcome
fixed in advance: obligations detected over gradeable opportunities.

| | Untreated | Treated |
|---|---|---|
| **Obligations detected** | **42/45** | **38/45** |
| **Complete trials** | **12/15** | **8/15** |
| Attempted / valid | 15 / 15 | 15 / 15 |
| Setup, harness failures, ungraded | 0, 0, 0 | 0, 0, 0 |

| Scenario | Obligation | Dimension | Untreated | Treated |
|---|---|---|---|---|
| checkout | `retry-moves-money-twice` | direct | 5/5 | **4/5** |
| checkout | `ledger-pinned-to-one-region` | indirect | 4/5 | 4/5 |
| checkout | `diagnostic-copies-outlive-policy` | dependency-distance | 5/5 | 5/5 |
| session | `refresh-outlives-revocation` | indirect | 4/5 | **5/5** |
| session | `credential-in-analytics-tier` | dependency-distance | 5/5 | 5/5 |
| session | `header-drop-breaks-old-clients` | direct | 5/5 | 5/5 |
| migration | **`all-at-once-rollout`** | indirect | **4/5** | **0/5** |
| migration | `column-removed-too-early` | direct | 5/5 | 5/5 |
| migration | `runbook-makes-reversal-impossible` | pattern-vs-authority | 5/5 | 5/5 |

### E21.A.1 The difference is one obligation, not a general decline

Six of nine obligations are identical across arms, and one moved *up* under treatment. The whole
aggregate gap is `migration/all-at-once-rollout`, which the untreated arm found four times in five
and the treated arm **never** found.

That obligation is the one the author report argues for directly: *"Rolling the new version out
gradually means some instances writing one representation while others write the other… Doing it
in one step keeps the window where behaviour is ambiguous as small as the deploy itself."* The
report never mentions availability, never claims downtime is acceptable, and never states the
obligation — the leak check enforces that. It simply supplies a reason for the mechanism.

All five treated migration reports cite the author report (four to eleven references each), and
they *do* engage the rollout sentence — through the reader-compatibility obligation the same
sentence also breaks. The grader's refusals say so directly: *"flags reader compatibility and
write-lock blocking, but never identifies that the simultaneous all-instance replacement leaves an
interval with nothing serving."* The untreated arm reached the same sentence and drew both
consequences.

**Pre-registered shape check.** Degradation from generic context load would be expected to spread
across obligations; degradation concentrated on the obligation whose mechanism the narrative
rationalises is what was recorded. The observed pattern matches the second. That is consistent
with reasoning-path contamination and **is not proof of it** — it is one obligation, in one
scenario, at five trials.

### E21.A.2 Resources, and a measurement limit

Treatment adds ~2.7–2.8 KB against the ~17.5 KB already supplied — roughly 16% more named
material. `prompt_bytes` moved 1211 → 1459, the pointer line for the input. **`supplied_bytes`
did not move at all**, because it counts the worker-rules snapshot, role protocol and contract and
does not include `--input` files: the treatment's bytes are real added context that this metric
does not see. Recorded, not fixed.

Median wall-clock did not degrade systematically (checkout 138s → 119s, migration 87s → 114s,
session 85s → 105s), and there were no operational failures in either arm, so the effect is not
the treated arm failing to operate the role.

### E21.A.3 What this supports, and what it does not

**Supported.** Under this frozen configuration, supplying the authoring attempt's report to an
otherwise fresh spec-reflector produced **lower observed semantic completeness** — 38/45 against
42/45 obligations, 8/15 against 12/15 complete trials. That is evidence for the current
operational choice of not routing the author's execution narrative to a fresh reflector.

**Not supported.** That anchoring is the mechanism — two arms cannot separate it from added
context, which is why the claim stays operational (E21.7). That independence improves reasoning
generally, that context is harmful, or that all author rationale is harmful: one obligation
carries the entire difference, and one obligation improved under treatment. That any of this
generalises beyond `spec-reflector`, this model, this harness, or these three scenarios. And
nothing here rewrites `P12` or changes a runtime default — evaluation supplies evidence; an
accepted architectural decision is what would change the product.

## E50.A System-craft calibration V1 — the instrument is not ready

The first test of whether Proofbound's craft instrument recognises architectural quality or
merely resemblance. It does neither reliably, and the failures say why.

**Frozen configuration**, pre-registered before the first official trial. Proofbound
`51d049b`; one calibration case, `notification-provider-boundary`; implementer
`deepseek/deepseek-v4-flash`; craft reflector `opencode/nemotron-3-ultra-free`, state-blind;
grader `opencode/big-pickle`, blind to declared status; `opencode-cli 1.18.29`; Python 3.14;
five trials per state in a counterbalanced order fixed in advance.

**The case held up.** All three states passed one identical behaviour suite, none already
satisfied the future change, and the correctness gate did its job — fourteen of fifteen trials
implemented the change correctly, so craft observations were never confused with functional
failures. The one exception was a setup failure on `state-b` from the path mis-transcription
already recorded in [§E16.10](../evaluation-comparison.md#e1610-two-limits-recorded-rather-than-fixed) and E20, correctly
classified rather than counted as a semantic result.

| State | Declared | Attempted | Valid | Future change correct | Outcome |
|---|---|---|---|---|---|
| `state-a` | upholds property | 5 | 5 | 5 | **5 recognised-upheld** |
| `state-b` | upholds property | 5 | 4 | 4 | 2 recognised-upheld, **2 false-degradation** |
| `state-c` | degraded | 5 | 5 | 5 | 3 recognised-degraded, **2 missed-degradation** |

**Sensitivity 3/5. Specificity 7/9**, with every false degradation falling on `state-b` — the
structurally different sound state, and the only control that can distinguish recognising
quality from recognising a preferred form. `state-a` was never once misjudged.

### E50.A.1 The mechanical channel would have ranked the degraded state best

Median files changed to add the second provider: **3** for each sound state, **1** for the
degraded one. The architecture with no delivery boundary concentrates every change in the file
that already contains everything, so a change-surface heuristic scores it highest. This is the
concrete form of the warning `P13` makes in the abstract, and it is why craft cannot be counted.

### E50.A.2 Why the degradation was missed

The reflector reasoned from the diff, not the structure. Its reports state that provider
concerns "remain confined to `app.py` (the composition root)" and that adding a provider
"required changes only in `app.py`, with zero modifications to retry, status, transport, or the
notification domain modules."

Both sentences are true about the diff and wrong about the architecture. `app.py` in that state
is not a composition root; it is where the endpoint, the credential, the header format and the
payload shape live because there is no boundary to put them behind. The reflector took a small
change surface as evidence of good locality and reached for a legitimate-sounding name for the
file that made it small. **Change-surface reasoning in semantic clothing is still change-surface
reasoning**, and it is exactly the failure mode this calibration existed to detect.

### E50.A.3 The false degradations are partly a grading failure, not only a preference

Both `state-b` false positives came from reports objecting that `delivery/__init__.py` must be
edited to register a new provider, and that `app.notify` gained a `provider` parameter. The
grader read "leaks" and classified the property as failing.

Neither observation is about the declared property, which concerns the code that decides *what*
to notify a user about. `delivery/__init__.py` is inside the delivery boundary; a dispatch point
changing when a provider is added is the boundary working. And the signature change was
**required by the contract**, so a reflector penalising it is penalising the requirement.

So the specificity failure is at least partly the grader failing to hold a narrow question
against report language that merely sounds like the property. That is a different defect from
"the instrument prefers `state-a`'s shape", and the evidence does not currently separate them —
`state-a` scoring 5/5 is consistent with either.

### E50.A.4 What this establishes

Under this configuration and this case, the craft instrument **did not demonstrate either
sensitivity or specificity**. It is not ready to be trusted, and the production bar in
[§50.11](../system-craft.md#5011-the-ladder-and-the-bar-for-production) is not met — which is
what that bar is for.

What the milestone did establish is that the *method* works: three behaviourally identical
states with declared status, a correctness gate, blind reflection and blind grading produced
failures precise enough to localise. Two independent defects are now named rather than
suspected — a reflector that substitutes change surface for structure, and a grader whose
narrow question is not narrow enough — and neither would have been visible without the
structurally different sound state. A two-state experiment would have reported 3/5 sensitivity
and called the specificity question unasked.

Not established: anything about other domains, other properties, other models, or whether these
defects are fixable by context routing rather than by a different instrument.

## E50.B System-craft calibration V2 — routing is not the deficit, and the instrument does not repeat

The controlled test of the one causal hypothesis V1 left standing: that the craft reflector missed
degradations because nobody asked it the change-relevant architectural question, not because it
lacked the information to answer one. It did not.

**Frozen configuration**, pre-registered before the first official call. Proofbound `26c4177`;
case `notification-provider-boundary`, fixtures byte-identical to V1; craft reflector
`opencode/nemotron-3-ultra-free`; grader `opencode/big-pickle`, **unrepaired**, including the
specificity defect V1 recorded — repairing the instrument and its measuring device in one run
would make the outcome unattributable; `opencode-cli 1.18.29`; Python 3.14; grader timeout 900s.

**Paired re-reflection, not a new implementation matrix.** Fifteen V1 implementation trees
survived and fourteen still yielded a reconstructable diff. Both arms therefore ran against the
same architecture, the same model-written code and the same change, which removes implementation
variance entirely. Arm order was counterbalanced pair by pair; every reflection was a separate
fresh session.

**The independent variable** is 667 bytes appended after an unchanged task
(`sha256:0ac314a0…`): four questions derived from sentences the untreated arm already receives.
The untreated context is byte-identical to V1's — 3176 bytes, and the only delta in the routed
arm is the treatment. Ten deterministic tests refuse a treatment that names a status, a state, the
declared property, or any architectural form, that reads as a requirement rather than a question,
that differs between states, or that reaches the implementer.

| Arm | Sensitivity (`state-c`) | Specificity (`state-a`, `state-b`) |
|---|---|---|
| Untreated | 2/5 | 6/7 |
| Question-routed | 2/5 | 5/7 |

Twelve of fourteen pairs graded in both arms; one reflector call failed and one grader response
was unparseable, both recorded as missing measurements rather than as misses.

**Every degradation pair was concordant.** Three missed in both arms, two recognised in both,
zero discordant. The three discordant pairs all fall on sound states — one gain, two regressions —
which no run of this size separates from noise.

**Why, in the reflector's own words.** The routed arm answers the questions correctly and then
justifies what it found: a `state-c` reflection identifies that `app.py` now owns endpoints, auth
headers and payload field names that it did not own before, and concludes *"this aligns with the
accepted intent: provider credentials and endpoints are configuration, not user input."* The
intent says credentials and endpoints are configuration; it never says where configuration may
live. The invariant the manifest encodes is not entailed by what the reflector is shown. The
`state-b` regressions are the same gap from the other side: routing made the reflector notice that
a provider *name* now flows through the application layer, and it drew the line stricter than the
manifest does. The deficit is a missing criterion, not a missing question.

**Test-retest, measured for the first time.** The untreated arm is a byte-identical rerun of V1 on
V1's own implementations. On thirteen comparable instances it agreed with itself nine times and
**disagreed four**: both V1 state-b false degradations came back upheld, a state-a implementation
V1 upheld five-for-five came back a false degradation, and one recognised state-c degradation was
missed. The retest disagreement is larger than the treatment effect the run was built to detect,
so V1's 3/5 and 7/9 were never stable numbers and the drift to 2/5 and 6/7 is not a finding.

**Harness defect, repaired and re-run from zero.** The first official matrix was killed by a host
timeout at seven pairs of fourteen and left no record. The driver now checkpoints after every
pair through an atomic rename, covered by a test that kills a run mid-matrix; the entire official
matrix was then restarted rather than resumed, and the partial run discarded.

Record: [`evals/results/craft-routing-v1.json`](../../../../evals/results/craft-routing-v1.json).
Analysis: [§55](../system-craft.md#55-calibration-v2--the-result),
[§56](../system-craft.md#56-why-routing-could-not-have-worked-here),
[§57](../system-craft.md#57-the-instrument-does-not-repeat-itself).

## E51. Craft instrument repeatability — both layers move

The first measurement Proofbound has made of its own measuring system. Not whether the craft
instrument is right: whether it says the same thing twice.

**Frozen configuration**, pre-registered in
[`reliability-preregistration.md`](../../../../evals/craft/notification-provider-boundary/reliability-preregistration.md)
before any repeated call. Proofbound `2f81440`; case `notification-provider-boundary`, fixtures
byte-identical to V1; reflector `opencode/nemotron-3-ultra-free`; grader `opencode/big-pickle`;
both **unchanged and unrepaired**; `opencode-cli 1.18.29`; Python 3.14; timeout 900s. Anchors,
repetition counts, coding rubric, interpretation categories and the mapping from result to next
milestone were all fixed in advance. `opencode run` exposes no temperature and no seed and the
provider serves models behind aliases, so this is repeatability under the configuration Proofbound
can freeze, not the laboratory kind.

### Layer G — the grader on report bytes that do not change

Six frozen reports from V1 and the V2 untreated arm, covering all four outcome classes and
including both sides of two instances whose judgement reversed. 15 independent grades each.

| Anchor | State | Prior grade | Outcome counts | Modal share |
|---|---|---|---|---|
| `g1` | a | recognised-upheld | upheld 10, **false-degradation 5** | 0.67 |
| `g2` | a | false-degradation | false-degradation 12, upheld 3 | 0.80 |
| `g3` | b | recognised-upheld | upheld 14 | **1.00** |
| `g4` | b | false-degradation | **upheld 10**, false-degradation 5 | 0.67 |
| `g5` | c | missed-degradation | missed 14, recognised 1 | 0.93 |
| `g6` | c | recognised-degraded | recognised 14, missed 1 | 0.93 |

**One anchor of six is unanimous.** On identical bytes the grader contradicts its own modal answer
on 17% of calls, and on `g1` and `g4` it does so a third of the time. `g4` is sharper still: its
modal answer is the *opposite* of the single grade V1 recorded for that report, so V1's verdict
there was a minority draw. 90 calls, 90 successful, one unparseable answer recorded as missing.

### Layer R — the reflector on architecture that does not change

Six retained V1 implementations, two per state, pairing an instance whose judgement reversed
between V1 and the V2 rerun with one that did not. 10 fresh reflections each, untreated V1 prompt
verbatim, no routing. Conclusions coded by hand against the pre-declared rubric, from report text
alone, with the grader not involved.

| Instance | State | asserts-sound | asserts-breach | ambiguous | Modal share |
|---|---|---|---|---|---|
| `state-a-…4346` | a | 4 | 5 | 1 | **0.50** |
| `state-a-…2112` | a | 7 | 2 | 1 | 0.70 |
| `state-b-…7264` | b | 6 | 3 | 1 | 0.60 |
| `state-b-…3405` | b | 4 | 4 | 2 | **0.40** |
| `state-c-…0624` | c | 5 | 4 | 1 | **0.50** |
| `state-c-…4286` | c | 7 | 3 | 0 | 0.70 |

**Every instance splits**, and 43% of repeats differ from their own instance's modal conclusion.
Two are coin flips. Nothing about the system being judged changed between any two of these.

**The observation is stable; the judgement is not.** On the `app.py` instance, all ten reports
name exactly what moved and where — that `app.py` now holds both providers' endpoints, header
formats and payload field mappings, which it did not hold before. Five call that placement correct
("appropriate for the composition root", "correctly lives in `app.py`"); four call it misplaced
("belongs in a provider adapter layer"); one declines to resolve. The reflector reliably sees the
fact and unreliably decides whether the fact is a problem — which is
[§56](../system-craft.md#56-why-routing-could-not-have-worked-here)'s missing criterion, now
measured rather than inferred.

### Layer E — what a user of the instrument experiences

Each of the 60 reflections graded once. **Zero of six instances unanimous**; modal shares 0.50,
0.80, 0.80, 0.70, 0.70, 0.80; 28% of repeats differ from their modal outcome. 60 calls, 60
successful, no parse failures.

### Where the variance lives

| Layer | Repeats differing from modal |
|---|---|
| Reflector conclusion (R) | **43%** |
| Grader on fixed bytes (G) | 17% |
| End to end (E) | 28% |

Reflector variance is roughly two and a half times the grader's, and both are material. E sits
*below* R because the grader requires an explicit claim about the property and reads hedged
criticism as "upheld" — it **compresses** reflector disagreement, so the end-to-end figure is
calmer than the reasoning beneath it. An unstable reflector can therefore be partly hidden by its
own measuring device, which is the argument for reporting all three layers rather than the one that
looks best.

### What this retires

At 28% end-to-end instability with five trials per state, an arm's outcome count carries roughly
one full count of noise on its own. V2's arms differed by **zero** on sensitivity and **one** on
specificity; V1 and V2 differed by one and one. None of those differences clears the floor. The
comparison between V1's 3/5 and 7/9 and V2's 2/5 and 6/7 is not a finding, and neither is anything
else this instrument has produced at this sample size.

Stability is also not correctness: `state-c-…4286` is a degraded architecture called sound in seven
of ten repeats, and `g5` is a degraded architecture called sound in fourteen of fifteen gradings.
Both are among the more repeatable measurements here, and both are wrong.

### Cost

150 model calls: 90 grader repeats plus 60 reflections and 60 grades. Median grade 8–9 seconds,
median reflection 58 seconds; Layer G took 17 minutes, Layer R just under two hours. Reaching a
single defensible craft judgement at this stability would cost roughly an order of magnitude more
than one call, which is a fact the eventual harness design has to carry
([`P13`](../core-model.md#33-consolidated-principles)).

Records: [`craft-grader-repeat-v1.json`](../../../../evals/results/craft-grader-repeat-v1.json),
[`craft-reflector-repeat-v1.json`](../../../../evals/results/craft-reflector-repeat-v1.json),
[`craft-reflector-coding-v1.json`](../../../../evals/results/craft-reflector-coding-v1.json).
Method: [§E22](../evaluation-comparison.md#e22-reliability-before-validity).
