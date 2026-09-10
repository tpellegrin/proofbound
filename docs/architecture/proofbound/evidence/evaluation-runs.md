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

## E52. The discovery grader, characterised before anything relies on it

`§E51` measured the craft **verdict** grader — *does this report say the property fails?* A
closed-world experiment does not use it. It uses the **discovery** grader — *does this report
identify this specific problem?* — which every other Proofbound evaluation already grades with, and
which had never had its dispersion measured. This is that measurement, run before the substrate is
relied upon rather than after.

**Frozen configuration.** Proofbound `db05eef`; the six committed anchors from
`anchors/manifest.json`, unchanged; 15 independent gradings each; grader `opencode/big-pickle`,
unchanged; `opencode-cli 1.18.29`; Python 3.14. The planted-problem statement is `state-c`'s own
committed rationale — written when the case was built, never shown to any worker or reflector, and
not authored for this run, so nothing semantic here was fitted to reports already read.

The anchor set carries its own controls by construction: the four `state-a` and `state-b` reports
describe architectures where the `state-c` problem is genuinely absent, so *not-detected* is the
correct answer and they act as negative items; the two `state-c` reports are the positive items.

| Anchor | State | Counts | Modal share |
|---|---|---|---|
| `g1` | a | not-detected 15 | **1.00** |
| `g2` | a | not-detected 15 | **1.00** |
| `g3` | b | not-detected 15 | **1.00** |
| `g4` | b | not-detected 15 | **1.00** |
| `g5` | c | **detected 10**, not-detected 5 | 0.67 |
| `g6` | c | detected 15 | **1.00** |

**Five of six anchors unanimous, 90 of 90 calls graded, no parse failures.**

| | Verdict grader (`§E51`) | Discovery grader |
|---|---|---|
| Unanimous anchors | 1/6 | **5/6** |
| Pooled non-modal | 15/89 = **16.9%** | 5/90 = **5.6%** |
| On sound architectures | 8/30 and 5/29 | **0/30 and 0/30** |
| On the degraded architecture | 2/30 = 6.7% | 5/30 = 16.7% |
| Missing measurements | 1/90 | **0/90** |

**The profile inverts, and the inversion makes sense.** The verdict grader was least stable on
sound architectures, where reports raise concerns without ever claiming a breach and it had to
decide what the prose amounted to. The discovery grader is perfectly stable there — a report cannot
identify a problem the architecture does not contain — and disperses only on `g5`, the genuinely
ambiguous case where the report names the planted problem and then endorses it.

**`g5` is the finding.** The verdict grader classified that report as *upheld*, which the V1 and V2
records carry as a missed degradation. The discovery grader's modal answer on the identical bytes is
**detected**: the report does identify the planted problem, and merely declines to call it a breach.
The conflation [§E20.3](../evaluation.md#e20-two-measurement-problems-wrongly-sequenced-as-one)
predicted — "says the property is fine" and "never addresses it" sharing one label — is visible here
as recovered signal, not as an argument.

**Adequacy, with a stated bound.** Dispersion is three times lower pooled and zero on four of six
anchors, but it is not zero where it matters: 16.7% on ambiguous degraded reports, which is exactly
where a sensitivity measurement lives. At ten samples per cell that is roughly 1.7 counts of grading
noise, so a distribution shift of three counts or more is resolvable and a one-count shift is not. A
future calibration must pre-declare a minimum effect above that floor and a budget to match, and
must report per-cell dispersion rather than a pooled figure that would hide it.

Record: [`craft-discovery-grader-repeat-v1.json`](../../../../evals/results/craft-discovery-grader-repeat-v1.json).
Method: [§E24](../evaluation.md#e24-what-it-takes-to-call-an-increment-an-improvement).

## E53. Why Calibration V3 cannot run on this case

The V3 design check was to author one architectural consequence, prove it entailed, and pre-register a
paired experiment. Deriving it required reading the three fixtures against the accepted intent asking
*what is actually entailed here*. The answer disqualified the case. No live call was made.

### The probe change favours the degraded state

The future contract asks for a second provider differing in endpoint, header and payload field names,
and states that everything else is unchanged — same outcome vocabulary, same rejection and retry
policy, same three-attempt limit, same `transport.post` seam. Under that change:

| State | Work the change requires | Files changed, every trial |
|---|---|---|
| `state-a` | new sender module, select per notification in `delivery/__init__`, thread parameter through `app` | 3, 3, 3, 4, 5 |
| `state-b` | new provider module, register and dispatch, thread parameter through `app` | 3, 3, 3, 5 |
| `state-c` | add a second endpoint, key and payload builder in `app.py` | **1, 1, 1, 1, 1** |

Recomputed from [`craft-calibration-v1.json`](../../../../evals/results/craft-calibration-v1.json).
**Change locality** is one of the three lenses the craft task asks the reflector to answer under, so
every report that praised `state-c`'s locality was stating a fact about the probe it was given. The
instrument was not failing to see a degradation; the probe was not exercising one.

### Candidate consequences, and how each failed

**C1 — "Code deciding what to notify a user about does not need to know how any delivery provider is
called."** The wording carried from earlier milestones. It fails twice. No code in any fixture *decides*
what to notify: `app.notify(user_id, channel, subject, body)` receives the content as parameters in all
three states, so the responsibility the criterion constrains does not exist in the case. And the only
statement the accepted intent makes about placement is *"provider credentials and endpoints are
configuration, not user input"* — a statement about untrusted input, not about where configuration
lives. Making `state-c`'s placement a violation would overrule the intent rather than follow from it.

**C2 — "A change to provider invocation mechanics must not require changing a module whose purpose is
the product's stable outcome vocabulary."** Genuinely entailed: the intent declares the outcome
vocabulary contractually stable and more than one provider expected. It discriminates on paper —
`state-c` interprets provider response codes in `notifications/status.py` while both sound states keep
that inside the provider module. It fails its counterexample audit. That module maps `2xx → sent`,
`400/422 → rejected`, everything else retry: **generic HTTP semantics, not Acme's**. A shared HTTP
outcome mapper is a defensible design, so C2 would mark a legitimate architecture degraded.

**C3 — the case's own committed `state-c` rationale.** Not usable as a pre-registered column: it is a
conjunction of four separate consequences (no delivery boundary; endpoint, credential, header and
payload names in the entry point; retry and outcome policy in the notification package; adding a
provider requires editing both). A report naming any one of them would be credited, which makes
"detected" semantically indeterminate.

### And the remaining pressure is already at ceiling

Fifty-seven of sixty untreated reports named where provider knowledge sits
([§E51](#e51-craft-instrument-repeatability--both-layers-move)). Graded against C3 by the discovery
grader, the two untreated `state-c` anchors were detected **25 times in 30**
([§E52](#e52-the-discovery-grader-characterised-before-anything-relies-on-it)). A treatment cannot
raise discovery of something the baseline already discovers four times in five. Eval V1 and the first
calibration suite both ceilinged on exactly this; the discovery framing inherits it here rather than
escaping it.

### What this does not mean

The substrate is not implicated: the closed-world machinery, the discovery grader characterisation and
the increment contract all stand, and this design check used them exactly as intended — to refuse an
experiment before spending on it. Nor is `state-c` a badly built fixture in isolation; it is a genuine
degradation under a probe that would exercise it. What is missing is the pairing between the planted
degradation and the change used to probe it, which
[§59.1](../system-craft.md#591-what-a-calibration-probe-has-to-satisfy) now states as a standing
condition on any calibration case.

**A repaired case needs two changes**, and therefore its own milestone: a future change whose providers
differ in *rejection semantics* rather than only in wire format, which would force `state-c` to edit the
notification package while the sound states still add a single module; and an accepted intent that
states what must remain true rather than only what is configuration, so a discriminating consequence
becomes entailed. Making those two changes and the criterion treatment in one run would leave the
result unattributable.

## E54. The repaired case measures, and the pressure statement does not discriminate

The repaired `r0002` case was encoded, passed every deterministic gate, and was frozen before a
single semantic call. Its untreated baseline then failed — not on the fixture, but on the sentence
handed to the grader.

**Fixture validity, established before measurement.** All three states pass the Acme behaviour suite
before and after the change; none satisfies the hidden Beacon gate before it; all three satisfy it
after, with a reference implementation written inside each state's own architecture. **No
deterministic result separates sound from degraded**, which is the property the whole case rests on.
The old confound is gone: the probe changes exactly three files in every state, where the old one
changed one in the degraded state and three in the sound ones. Structural discrimination held —
Beacon's reporting convention lives only in a Beacon-specific file in `state-a` and `state-b`, and
in `notifications/status.py` in `state-c`, which is not specific to any provider.

**Baseline**, Proofbound `4e0784a`, one untreated arm, N=10 per state, 30 reflections each graded
once by the characterised discovery grader.

| State | Declared | Counts | Graded |
|---|---|---|---|
| `state-a` | sound | **detected 7**, not-detected 2 | 9/10 |
| `state-b` | sound | **detected 5**, not-detected 5 | 10/10 |
| `state-c` | degraded | detected 10 | 10/10 |

One reflector call failed on `state-a` and is recorded as missing, never as a not-detected.

**Both pre-registered failure conditions fired at once.** `state-c` sits at ceiling, leaving no room
for a treatment to raise it; and the sound states are detected 7 of 9 and 5 of 10, which is
non-specificity severe enough that a treatment could not be read even if headroom existed.

### Why: the pressure contains a disjunct the contract forces true everywhere

The frozen pressure named three ways to fail — a provider-independent module acquiring outcome
knowledge, **the application entry point** acquiring it, or **the retry policy being restated**. The
future contract *requires* `app.notify` to gain a `provider` parameter, so the entry point changes in
every state by construction; and both sound architectures keep each provider's retry loop inside that
provider's own module, so the retry policy is restated in all three. Two of the three disjuncts are
true in the sound states by design.

Lexical corroboration of the human reading, across all thirty reports — which disjunct each detected
report discusses:

| State | Detected | mention the entry point | mention outcome interpretation |
|---|---|---|---|
| `state-a` | 7 | 7 | 1 |
| `state-b` | 5 | 5 | **0** |
| `state-c` | 10 | 10 | 10 |

Every sound-state detection is driven by the entry-point clause. The clause that actually
discriminates — provider-independent code learning how a provider reports outcomes — appears in
10 of 10 degraded reports and in 0 of 5 `state-b` detections.

The reports say it themselves. One `state-a` reflection graded *detected* states that each
provider's own concerns, *"endpoint, auth header, payload field names, response-body interpretation,
retry mapping"*, are **correctly encapsulated** in the provider modules — it declares the
architecture sound on precisely the axis the pressure was meant to capture — and was credited anyway,
because it also observed that `app.py` now knows provider names.

### What this does and does not implicate

**Not the fixture.** Intent, probe, states, reference implementations and hidden gate all did what
they were designed to do, and the structural audit before measurement showed the discrimination the
design predicted.

**The pressure statement.** It was carried forward verbatim from the design milestone and never
re-audited against the reference implementations, which only existed once this milestone wrote them.
The design document had already noted that a criterion about restating the retry policy would be
violated by both sound states; the final wording reintroduced exactly that clause, and added the
entry point beside it.

**Not repaired here.** Re-grading the same thirty reports against a narrowed pressure would be
benchmark repair after results, and the numbers it produced would be fitted to reports already read.
The corroboration above says what a next pre-registration should test; it is a diagnosis, never a
measurement, and the narrowed pressure must earn its own baseline.

**Cost.** 30 reflections and 30 gradings, 1h50m wall clock (02:22Z to 04:13Z); median reflection 128s, 104 minutes of reflector time.

Record: [`craft-r0002-baseline.json`](../../../../evals/results/craft-r0002-baseline.json).
Pre-registration: [`baseline-preregistration.md`](../../../../evals/craft/notification-provider-boundary/baseline-preregistration.md).

## E55. The atomic column discriminates, and the untreated reflector is already at ceiling

`§E54` failed on the measurement column rather than the fixture: three propositions were bundled
into one cell, and two of them were true in sound architectures by construction. This milestone
kept the fixture frozen, replaced the column with one proposition, proved the grader could measure
it, and re-ran the baseline. Both results are decisive and they point in opposite directions.

### The column, made atomic

Checked against the frozen reference implementations rather than against labels:

| Clause of the old pressure | `state-a` | `state-b` | `state-c` |
|---|---|---|---|
| Entry point gains provider selection | true | true | true |
| Retry policy is restated | true | true | **false** |
| Provider-independent code learns how a provider reports outcomes | false | false | **true** |

The first is true everywhere because the contract requires `app.notify` to gain a `provider`
parameter. The second is **inverted** — keeping a retry loop inside each provider is what a
provider-specific integration does. Only the third discriminates.

The repair was deletion. The frozen pressure is now that clause alone:

> Code that is not specific to any one delivery provider had to interpret how a particular provider
> reports the result of a delivery attempt, in order to produce the product's delivery outcome.

It is verbatim the criterion the pre-baseline case-repair design already used in its own state
analyses, so the wording predates every report. The retained reports were used only as grader
anchors, never to estimate what the new baseline would show.

### Grader adequacy, measured before spending reflector calls

Six frozen anchors, 15 gradings each, budget fixed in advance. **Three of the six are the exact
reports the old column false-credited**, so the set is biased toward difficulty.

| Anchor | Category | Counts | Modal share | Old column |
|---|---|---|---|---|
| `d1` | identifies the leakage plainly | detected 15 | **1.00** | detected |
| `d2` | identifies it, calls it reasonable | detected 15 | **1.00** | detected |
| `d3` | says interpretation is correctly isolated | not-detected 11, detected 4 | 0.73 | **detected** |
| `d4` | selection and central import only | not-detected 15 | **1.00** | **detected** |
| `d5` | provider identity and selection only | not-detected 15 | **1.00** | **detected** |
| `d6` | generic provider concerns | not-detected 14, detected 1 | 0.93 | — |

Every modal outcome matches its declared category; 90/90 graded, no parse failures; pooled non-modal
5/90. The column separates provider-awareness from provider-outcome interpretation, which the old one
could not. **Gate passed on the rule fixed before the numbers existed.**

### Fresh baseline

Same fixture, same substrate, one arm, N=10 per state, 30 fresh executions with nothing reused from
the previous series.

| State | Declared | Counts | Graded | Under the old column |
|---|---|---|---|---|
| `state-a` | sound | detected 1, not-detected 9 | 10/10 | detected 7/9 |
| `state-b` | sound | detected 2, not-detected 7 | 9/10 | detected 5/10 |
| `state-c` | degraded | **detected 10** | 10/10 | detected 10/10 |

One reflector call failed on `state-b`, recorded as missing.

**Specificity is repaired.** False pressure fell from 78% to 10% on `state-a` and from 50% to 22% on
`state-b`. The case now discriminates: 10/10 against 1/10 and 2/9.

**Every sound-state detection is a grader error of one identified kind.** All three reports deny the
pressure in their own words — *"each provider encapsulates its own endpoint, headers, payload shape,
and response interpretation in its own file — correct"*; *"the retry policy and outcome vocabulary
are centralized in each provider's deliver function, so Beacon implements its own mapping without
touching shared code"*; *"that module absorbs all Beacon-specific divergence"*. Each also recites
Beacon's `accepted`/`refused`/`unavailable` mapping in detail while attributing it to the provider
module, and the grader credits the recitation. This is the same failure mode and the same magnitude
as anchor `d3`'s 4/15, so it was measured before the baseline rather than discovered by it. **None of
them identified a pressure the reference analysis had missed; the ground truth stands.**

### The result that stops V3

`state-c` is detected **10 out of 10**. There are no non-detections to analyse.

Against the pre-registered categories this is **no headroom**: the untreated reflector already finds
this pressure every single time. A treatment designed to raise discovery has nothing to raise, and
an experiment comparing 10/10 against 10/10 measures only its own noise.

The finding underneath it is worth more than the experiment it cancels. Given a probe that genuinely
exercises the boundary and a column that asks one atomic question, **the untreated craft reflector's
*discovery* is already perfect on the degraded architecture.** The reflector was never
criterion-starved for discovery. What V1 and V2 measured as failure was a probe that did not exercise
the degradation and a column that could not tell knowledge placement from provider awareness — and
what remained unstable in the reliability run was *judgement*, the layer this column deliberately
stopped measuring.

### Cost

90 gradings for adequacy (median 16s) and 30 reflections with 30 gradings for the baseline (median
reflection 110s, 80 minutes of reflector time), 1h27m wall clock.

Records: [`craft-atomic-grader-repeat-v1.json`](../../../../evals/results/craft-atomic-grader-repeat-v1.json),
[`craft-r0002-atomic-baseline.json`](../../../../evals/results/craft-r0002-atomic-baseline.json).
Pre-registrations: [`atomic-pressure-preregistration.md`](../../../../evals/craft/notification-provider-boundary/atomic-pressure-preregistration.md),
[`baseline-preregistration-atomic.md`](../../../../evals/craft/notification-provider-boundary/baseline-preregistration-atomic.md).
[§E54](#e54-the-repaired-case-measures-and-the-pressure-statement-does-not-discriminate) stands
unchanged and was not re-graded.

## E56. The modularity pilot finds material headroom, and two defects in the instrument that found it

`full`-only headroom pilot for the modularity and local-reasoning calibration, pre-registered and
committed before the first call. Six attempts, one arm, the frozen external task, implementer role,
`opencode/nemotron-3-ultra-free`. Development evidence with its own experiment identity; **no attempt
in it may become a `full` sample of a paired run.**

Record: [`craft-mlr-c3-full-headroom-pilot.json`](../../../../evals/results/craft-mlr-c3-full-headroom-pilot.json).
Pre-registration: [`MLR-C3-pilot-preregistration.md`](../../../../evals/craft/modularity-local-reasoning/MLR-C3-pilot-preregistration.md).
Analysis: [`MLR-C3.md`](../../../../evals/craft/modularity-local-reasoning/MLR-C3.md).

### The question the pilot was allowed to ask

Only one: whether unrestricted `full` executions consume the module's implementation source often
enough for a paired source-visibility experiment to have anything to remove. Not effect size, not
whether the model understands modularity, and not an architecture verdict.

### Headroom, against the categories declared before the first call

| # | correct | impl. source | file reads only | impl. runtime | contract read | calls | input tokens |
|---|---|---|---|---|---|---|---|
| 1 | no | 5,458 | 4,076 | 0 | 0 | 16 | 154,233 |
| 2 | yes | 4,740 | 3,358 | 611 | 0 | 27 | 216,145 |
| 3 | yes | 5,458 | 4,076 | 0 | 0 | 22 | 154,132 |
| 4 | yes | 7,204 | 5,822 | 151 | 0 | 38 | 288,296 |
| 5 | yes | 0 | 0 | 0 | 0 | 21 | 182,953 |
| 6 | yes | 6,602 | 4,076 | 0 | 2,994 | 32 | 207,647 |

Six valid attempts, no setup or harness failure. Four of five correct runs consumed implementation
source; median 5,458 bytes, or 4,076 counting only file reads and excluding the directory listing
that names the module. **Material headroom** under either reading, and unchanged if the disputed
attempt 1 is scored correct.

Consumed bytes exceed the 4,405 bytes on disk because OpenCode's `read` returns a line-numbered
rendering; every session was summarised, so all delivered-volume figures are upper bounds.

**Five of six runs never opened the contract.** They read the implementation, or inferred the
semantics from how the application already called the module. Attempt 5 completed the task correctly
having consumed neither. This is not a modularity finding — it is only the finding that there is
implementation-source consumption available for a treatment to remove.

### Why the paired experiment was not pre-registered

Two defects, both found by running the pilot, both fatal to the paired comparison rather than to the
headroom answer.

**The correctness oracle rejects a legitimate restructuring.** Attempt 1 is product-correct on every
status, body and second-download assertion, and passes the service's own suite. It fails one line:
the gate calls `exports.fetch(...)` and the agent had turned that into a get-or-create returning
`(body, created)`. Nothing in the task fixes that signature and nothing else in the workspace pins
it; the reference solution merely happens to keep it and add a separate `fetch_or_create`. The gate's
own docstring promises it "asserts nothing about how the service is arranged". This is the defect
MLR-C2 already repaired one level down, when it removed the gate's reach into the private helper
`exports._key` and left a dependency on a public function's shape in its place.

**Consumed-context attribution misses Python's own documentation route.** Attempt 5 — the run that
reads as *used no implementation at all* — ran `help(objectstore)` and received 5,397 bytes carrying
`_backend` and `_store`. The classifier scored it `other`; `python3 -m pydoc objectstore` is scored
`behaviour`, which is worse. The independent internal-name flag is the only reason the gap is
visible, and it records *that* interior names arrived, not how many bytes did — and the measurand is
bytes. In `full` this costs little. In `contract`, where interrogating a closed-source package with
`help()` is the most natural first move an agent has, such a run would report zero implementation
representation and be read as pure contract substitution. That is the fake zero the pre-registration
calls mandatory to prevent.

### What this does not mean

No modularity claim, no local-reasoning claim, no architecture verdict, and nothing about a second
domain. Headroom is not evidence that hiding the implementation preserves correctness — only that
there is something to hide. Both defects are pinned as deterministic tests and neither is repaired
here: the fixture and telemetry are frozen for this series, and repairing them from observed
behaviour is what creates a new revision, under which this pilot does not transfer.

### Cost

Six attempts, 1,203,406 input tokens, 51 minutes wall clock, no monetary cost on this model.

## E57. The repaired instrument measures what E56 could not

MLR-C3R. Two defects repaired before any call, the `full`-only pilot re-run under a new identity, and
the repair audited against what the runs actually did. Development evidence with its own experiment
identity; no MLR-C3 run is a sample of it and none of its runs may become a paired sample.

Record: [`craft-mlr-c3r-full-headroom-pilot.json`](../../../../evals/results/craft-mlr-c3r-full-headroom-pilot.json).
Pre-registration: [`MLR-C3R-pilot-preregistration.md`](../../../../evals/craft/modularity-local-reasoning/MLR-C3R-pilot-preregistration.md).
Analysis: [`MLR-C3R.md`](../../../../evals/craft/modularity-local-reasoning/MLR-C3R.md).
Methodology: [`§E25`](../evaluation.md#e25-the-instrument-is-part-of-the-experiment).

### The oracle, stated as a number rather than an anecdote

[§E56](#e56-the-modularity-pilot-finds-material-headroom-and-two-defects-in-the-instrument-that-found-it)
reported one product-correct attempt rejected for changing an internal signature. Held against four
realizations that satisfy the task with different internal decomposition and five that are
behaviourally wrong, **v1 rejects two of the four**; v2 accepts all four and rejects all five, and
still rejects a workspace where the task was not done.

One clause of the task — *nothing is stored* for a refused account — turns out not to be observable
from the product surface at all, since a refused account can never read anything back. v2 asserts the
consequence that is observable, that it never receives the export, and records the gap rather than
closing it by reaching into the service.

### Attribution, decided by content rather than by verb

Route and content are now two channels, and the module's internal names are derived from its source
with `ast` rather than listed — the hand-written list already missed four names present in the module
today. Executed against the fixture: `help(package)` 5,389 B, `help(_store)` 882 B,
`pydoc.render_doc` 6,355 B, `vars(_store)` 912 B, `dir` 245 B, `getmembers` 245 B, `co_names` 92 B,
disassembly 10,212 B and module enumeration 33 B all disclose interior names and are
implementation-derived; `__all__` 68 B, signatures 110 B and docstrings 318 B disclose none and are
public; `inspect.getsource`, `loader.get_source` and `importlib.metadata` remain refused.

### The pilot

| # | correct | impl. source | impl. runtime | contract | calls | input tok | cache read | s |
|---|---|---|---|---|---|---|---|---|
| 1 | yes | 7,204 | 0 | 0 | 46 | 324,731 | 440,640 | 746 |
| 2 | yes | 7,204 | 0 | 0 | 34 | 273,570 | 354,240 | 458 |
| 3 | yes | 4,797 | 0 | 0 | 21 | 159,127 | 159,840 | 299 |
| 4 | yes | 4,797 | 0 | 0 | 33 | 232,212 | 185,760 | 412 |
| 5 | yes | 2,761 | 0 | 0 | 23 | 172,530 | 159,840 | 251 |
| 6 | yes | 6,543 | 0 | 0 | 24 | 200,903 | 203,040 | 238 |

**6/6 correct, 6/6 consuming implementation source, median 5,670 bytes** — valid headroom under the
categories declared before the first call. Every profile complete. 1,363,073 input tokens, 38,718
output, 1,503,360 cache-read, 40 minutes, no monetary cost on this model.

Correctness rose from 5/6 to 6/6 because the false negative is gone, not because the agents improved.
Five of six runs again never opened the contract. And the execution profile shows the pipeline is
**model-latency-bound**: attempt 1 spent 733.8 s of session span against 1.72 s of measured tool
execution and 0.10 s of verification.

### Attribution audit

**Material inbound escapes: 0.** Five items carried internal names outside the implementation classes
and all five are `assistant:reasoning` — text the model wrote, not a route by which information
enters — each in a run that had consumed 4,797–7,204 attributed implementation bytes. Model-side
disclosure in runs that consumed no implementation: 0, which is the check that would have caught an
escape hiding behind that exclusion.

**Stated limitation.** No `full` run used `help`, `pydoc` or introspection: implementation-runtime is
0 in all six. An agent holding readable source has no reason to interrogate the live object. The
repaired documentation attribution is therefore validated deterministically rather than by field
observation, and the `contract` arm — where the source is gone — is what will exercise it.

### What it does not establish

No treatment effect, no local substitution, no modularity benefit, nothing about a second domain, and
nothing about the boundary being the cause: the internal control remains unbuilt.

## E58. The paired comparison ran as frozen and lost five pairs to a provider outage

Record: [`craft-mlr-paired-calibration.json`](../../../../evals/results/craft-mlr-paired-calibration.json).
Pre-registration: [`MLR-paired-preregistration.md`](../../../../evals/craft/modularity-local-reasoning/MLR-paired-preregistration.md).
Analysis: [`MLR-paired-run.md`](../../../../evals/craft/modularity-local-reasoning/MLR-paired-run.md).

The frozen `full`/`contract` comparison — N = 8 pairs, oracle v2, attribution `mlr-context-2`,
identity `0eabff2091f486c7` — executed exactly as declared. Three pairs completed. From roughly 20:14
the frozen model began returning `Upstream request failed: [404] Provider returned error`, confirmed
independently outside the fixture at two separate times. Each affected slot took its three bounded
attempts and no more; 33 records, 8 valid executions, 25 failed attempts, 1.7 hours.

**Nothing was changed to rescue it.** The model is a frozen component and was not substituted; N was
not extended; no pair replaced a lost one; the driver ran to exhaustion so the outage's extent is
recorded. Pairs 6 and 7 hold a valid `full` run whose partner never completed and are recorded
`pair-invalid` — an unpaired execution is not a result for its arm.

### The three complete pairs

| pair | F source | C source | F runtime | C runtime | both correct |
|---|---|---|---|---|---|
| 1 | 5,822 | 0 | 1,383 | 2,154 | yes |
| 2 | 2,538 | 0 | 0 | 1,351 | yes |
| 3 | 5,458 | 0 | 0 | 975 | yes |

The treatment held exactly: `contract` consumed **zero** direct implementation source in every run,
and compensated with runtime introspection that was smaller than what it replaced. `help(objectstore)`
appeared and was classified correctly — the first field confirmation that the
[§E56](#e56-the-modularity-pilot-finds-material-headroom-and-two-defects-in-the-instrument-that-found-it)
attribution defect is closed.

**This is not reported as a result.** Three pairs is not the pre-registered experiment, and the
budget reasoning behind N = 8 was that correctness is the quantity with the least resolution — 3/3
concordance carries almost none. A "substitution supported" conclusion from the pairs that survived an
outage would be fitting the claim to the data that happened to arrive.

### Audits

No incorrect run occurred, so oracle v2 rejected nothing that ran. Three inbound items carried
module-internal names while classified `behaviour` — **one of them in the `full` arm** — and all three
are the same 103–105 byte traceback naming `objectstore/_store.py`, a line number, and the qualified
name of a *public* exception. `co_filename` was accepted as reachable in MLR-C2, and
[`MLR-C3R-pilot-preregistration.md`](../../../../evals/craft/modularity-local-reasoning/MLR-C3R-pilot-preregistration.md)
pre-declared this treatment. Its appearance in `full` confirms it is a property of probing absence, not
a `contract` compensation route. Model-side disclosure in runs that consumed no implementation: 0.

### Cost and shape

`full` 1,054,507 input / 36,023 output tokens over 5 valid runs; `contract` 662,997 / 17,675 over 3.
$0 on this model. Verification time ~0.09 s and tool time under two seconds against three to six
minutes of session span: the workload stays **model-latency-bound**, as
[§E57](#e57-the-repaired-instrument-measures-what-e56-could-not) found.

### Status

The instrument is sound, the treatment held, and the experiment is **incomplete**. A re-run requires a
new experiment identity, since resuming a partially consumed frozen series would splice two runs. No
execution here may become a sample of it.

## E59. A second model qualifies the phenomenon and disqualifies the instrument

MLR-C3D. Five `full`-only runs under a frozen DeepSeek V4 Flash configuration, pre-registered before
the first fixture call, to answer one question: does *this* model naturally read the implementation,
and does the instrument that survived Nemotron survive it too.

Record: [`craft-mlr-deepseek-v4-flash-high-headroom.json`](../../../../evals/results/craft-mlr-deepseek-v4-flash-high-headroom.json).
Pre-registration: [`MLR-C3D-headroom-preregistration.md`](../../../../evals/craft/modularity-local-reasoning/MLR-C3D-headroom-preregistration.md).
Analysis: [`MLR-C3D.md`](../../../../evals/craft/modularity-local-reasoning/MLR-C3D.md).
Model index: [`evals/models/README.md`](../../../../evals/models/README.md).

### Model is a condition, not a detail

Nothing Nemotron established applies to DeepSeek. The experiment id carries the model configuration,
the configuration hash binds thinking mode and reasoning effort, and no execution from either series
may become a sample of the other. `deepseek-v4-flash` is a moving alias: request, documented version
`DeepSeek-V4-Flash-0731` and provider-observed identity are recorded separately, and all five runs
reported one model and one variant.

Sampling parameters could not be frozen and this is recorded rather than faked — the provider
documents that thinking mode ignores `temperature`, `top_p`, `presence_penalty` and
`frequency_penalty` entirely.

### The pilot

| run | correct | impl. source | impl. runtime | contract | calls | input | output | cost |
|---|---|---|---|---|---|---|---|---|
| 1 | yes | 5,822 | 12,746 | 2,994 | 23 | 30,645 | 7,559 | $0.0330 |
| 2 | yes | 5,822 | 1,885 | 2,994 | 25 | 22,277 | 8,934 | $0.0304 |
| 3 | yes | 5,822 | 14,668 | 3,069 | 32 | 33,364 | 11,215 | $0.0464 |
| 4 | yes | 5,822 | 35,796 | 2,994 | 22 | 31,761 | 7,995 | $0.0337 |
| 5 | yes | 5,822 | 1,805 | 2,994 | 22 | 21,426 | 7,593 | $0.0272 |

5/5 correct, 5/5 consuming source, median 5,822 bytes — **strong headroom** under the pre-registered
categories. Total $0.171 derived at peak rates, against a $2.00 ceiling.

**A different agent.** DeepSeek reads the contract every time, where five of six Nemotron runs never
opened it; introspects the runtime up to 35,796 bytes even with source available, where Nemotron's
`full` arm peaked at 1,383; and uses roughly a seventh of the input tokens in a third of the time.
This is observation, not comparison — the two series answer questions within their own model.

### The instrument did not survive

**Four material inbound escapes.** Three of five runs read **their own `worker.log`** — 5,962, 6,218
and 8,154 bytes naming `_backend`, `_errors` and `_store`, each classified `harness` because the log
sits on a `DeepSeekAndDestroy/` path. It is a verbatim echo of the agent's own tool outputs, so
implementation text arriving through it is invisible to implementation accounting. A fourth run's
`git status && git ls-files` disclosed the same three internals as `behaviour`.

Both appeared in the `full` arm, so neither is a `contract` compensation route. That is exactly why
they block a paired run: in `contract`, an agent that introspected and then re-read its own log would
have that interior returned to it as *harness* bytes, and the arm would score as consuming less
implementation representation than it did — the fake zero the design exists to prevent.

Model-side disclosure was clean: sixteen items where the model's own text named internals, each in a
run that had consumed 18,568–41,618 attributed implementation bytes, and **zero** in a run that
consumed none.

No run was incorrect, so oracle v2 rejected nothing and is not implicated.

### Verdict and what it cost

Strong headroom authorises a paired design **only with a clean attribution audit**. The audit is not
clean, so no paired experiment was designed and no `contract` sample was bought.

A second model was an adversarial test of an instrument that had only met one agent's habits, and it
found two disclosure routes in five runs for seventeen cents — before paired money was spent, and
before a result could be published that the instrument could not support. Cost is not what stops the
paired experiment; the instrument is.
