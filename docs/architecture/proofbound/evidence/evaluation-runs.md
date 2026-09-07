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
