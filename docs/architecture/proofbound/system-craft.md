# System craft — what a sequence of valid changes does to a system

> **Design track.** How Proofbound measures whether a system stays understandable and changeable
> across many individually correct changes. Read this when designing that measurement. Nothing here
> is engineering authority: craft evidence never gates a change, and no result rewrites a principle.
>
> Entry point: [README.md](README.md).

## 40. This is not a new frontier

The failure mode is already named. [§38.1](long-running-autonomy.md#38-cumulative-coherence) calls it
**decision compounding**: each local decision changes the environment in which the next is made, every
step is locally rational and independently reviewed, and *"perfect memory would not prevent
compounding"*. `P10` asserts that local correctness does not imply global coherence. `P13` names the
surface it damages — **repository discovery context, which architecture quality determines** — and
[§28.2](context-economy.md#282-two-context-surfaces) states plainly that Proofbound *"currently does
not observe at all"*.

So the architecture has already said: this happens, here is the mechanism, here is the surface, and we
are blind to it. What is missing is measurement, and the move is to **compose pieces already designed
rather than invent a parallel concept beside them**:

`CE1` passive context telemetry and `CE2`'s controlled two-state replay are both designed and
unbuilt; the cumulative coherence audit and executable invariants are designed with their triggers
deliberately unresolved. None of it needs a parallel concept beside it.

Two of those absences are the real content of this document. The rest is composition.

**One prerequisite dissolves on inspection.** `CE2` was ordered behind worktree concurrency (M5)
because *"the experiment must never leak benchmark mutation into a real branch"*. That ordering
predates the evaluation harness, which copies each scenario into a fresh temporary tree and deletes it
afterwards, and never touches a branch at all. For the **evaluation** form of the experiment the
dependency does not apply. It still applies to any future production replay.

## 41. Three levels, separated by their referent

| Level | Question | Referent |
|---|---|---|
| **Correctness** | Did this change satisfy the accepted intent for this change? | The accepted contract |
| **Coherence** | Does the repository still conform to the accepted baseline plus the decisions authorizing divergence from it? | Accepted baseline and decisions ([§38.2](long-running-autonomy.md#38-cumulative-coherence)) |
| **Craft** | Did the system become harder to understand and change? | **None** |

The referent separates them, and it is not a presentational distinction. Correctness and coherence both
ask whether reality conforms to something somebody accepted. **Craft has nothing accepted to conform
to** — a system can conform perfectly to its baseline and still be miserable to work in, and no one
ever accepted "stay easy to change" as a contract clause.

Three consequences follow, and they are the spine of this design:

- Craft is **relative, never absolute**: the only honest question is whether a property became better,
  worse or unchanged, because there is no accepted standard to score against.
- Craft **cannot block**. A finding violating no accepted referent is an observation, and gating on it
  would let a generic concern override accepted engineering intent — `P5` generalized: integrity is not
  authority, and neither is an opinion about the future.
- Craft and coherence are **not merged**: one evaluator for both would give coherence's blocking
  authority to craft's advisory findings.

## 42. What system craft means here

Not "good code", "clean architecture" or "simple". Stated as a measurement of `P13`'s second surface:

> **A well-crafted system is one where the repository discovery context required to make a change stays
> proportional to the conceptual size of that change.**

Proportionality carries the weight. A cross-cutting security change legitimately reaches many places —
its conceptual size is large, and touching a lot is not a defect. The failure mode is **disproportion**:
a small, single-concept change that requires loading, understanding or modifying distant parts of the
system.

The definition does not reward smallness. A system with many services, modules and workflows can be
simple if boundaries are clear, state ownership is legible, contracts are stable and dependencies are
directional; a four-file system can be entangled. **Structural size and conceptual complexity are
different measurements**, which is why `P13` refuses size metrics and why counting files, services or
dependencies cannot stand in for craft. It is a guiding property, not an invariant: promoting it to a
rule would make every cross-cutting change a violation.
## 43. CUPID is a lens, and can only ever be a lens

Dan North's CUPID — Composable, Unix philosophy, Predictable, Idiomatic, Domain-based — is useful here
because of *how he frames it*: as **properties**, qualities to lean toward and never fully achieve,
explicitly contrasted with principles, which code either complies with or violates.

That framing settles two questions before they are asked. A property has no threshold, so **there is no
passing mark to compute** — a CUPID score would convert a property into a principle and lose the thing
that made it useful. And a property names a direction, not a rule, so **it cannot be an invariant**.

There is no `P14`. `P7` forbids a bounded evaluation from establishing cross-cutting policy, and `P11`
says repository patterns are evidence rather than authority; a vocabulary borrowed from outside the
repository has *less* claim than the repository's own patterns, not more. CUPID supplies words for
asking questions, and nothing else.

Two of its properties overlap and must not become separate evaluator dimensions: North's distinction is
that Unix philosophy concerns how code is *used* while single-responsibility concerns its *internals*,
a difference in viewpoint rather than a second measurement. **Predictable belongs mostly to
correctness**, which existing scenarios already plant and grade. **Idiomatic is the sharpest `P11`
hazard** — "looks like the surrounding code" would make accumulated debt self-enforcing — and is
deferred until that tension has a defensible answer. **Domain-based** must stay meaningful in systems
that never adopted DDD.

A minimal first vocabulary is therefore **three lenses, not five**: composability (including cohesion),
domain alignment, and change locality. They orient discovery
([§58](#58-craft-returns-discovered-consequences-not-verdicts)); they are never criteria to score.

## 44. Invariants, properties, preferences

Three authority classes, and only one of them can stop anything.

| Class | Example | Authority | Home |
|---|---|---|---|
| **Invariant** | Payments must not depend on UI; no cross-tenant access; public API compatibility | May block — but on the authority of the **accepted decision it projects**, never its own | [§37.4](long-running-autonomy.md#374-executable-invariants--accepted-decisions-made-operative), which already requires an invariant to cite its source decision |
| **Property** | Composability, domain alignment, change locality | Advisory only. No threshold exists | This document |
| **Preference** | Naming, folder layout, functions over classes | None architecturally | Local convention; `P11` keeps it evidence |

This is evaluation semantics and **no new persisted state**. The distinction is already carried by
existing structures: an invariant is a decision made operative, a property is a lens, a preference is a
pattern. Adding a `class` field would record something derivable from where a rule came from.

## 45. Measuring the second surface without rewarding laziness

`CE1` defines the telemetry: repository files read, repository bytes read, tool calls, duration —
provider-neutral first, token counts secondary. The harness already produces most of it as a by-product
of execution, so **no new instrumentation is required to begin**.

The hard problem is interpretation, and it must be stated before any number is collected: **an agent's
retrieval behaviour is not a property of the architecture.** A worker may open thirty files because it
is thorough, because it is weak, because the harness encourages breadth, or because the system is
genuinely tangled. An evaluation rewarding "read fewer files" would reward incuriosity.

The control is the one this project has used repeatedly: **hold the agent configuration fixed and vary
the architecture.** An absolute context footprint means nothing; the *contrast* between two repository
states executing the identical contract under the identical configuration means something. The derived
quantity worth measuring first is **context traversed but not changed**, read against the conceptual
size of the change and never against the repository's size — and §60 records that this observable has
been collected exactly once and never used as the measurement.

## 46. Longitudinal composition needs no new identity

A trajectory is `S0 → T1 → S1 → … → Tn → Sn`. The field test — *which invariant becomes impossible
without a new durable identity?* — finds none. Repository state is already identified by a Git commit;
a trajectory is `(initial commit, ordered task-sequence identity, configuration)` plus the commits it
produced, derived rather than stored; craft observations are evaluation evidence, and `P13` with
[§28.3](context-economy.md#283-why-this-is-not-a-ledger-field) already keeps execution economics out of
the artifact ledger.

**Architectural pressure** — the same craft observation recurring across many changes — is a **query
over accumulated evaluation evidence, never a stored fact**. Its output is an inquiry, not a
refactoring: evidence that a cross-cutting decision may be missing, which is the escalation `P7`
already requires a bounded worker to raise rather than settle. Pressure detected → parent → accepted
decision → possibly a
[§37.4](long-running-autonomy.md#374-executable-invariants--accepted-decisions-made-operative)
invariant. Never pressure detected → abstraction introduced.

## 47. Who decides

Craft findings are advisory to the parent, which already owns routing, architecture and the choice of
authoritative context, and which may accept, revise, open architectural work or record a local
decision. What neither parent nor evaluator may do is let a craft observation override accepted
engineering intent, and what Proofbound may never do is refactor a system because a metric moved.

## 48. What gaming would look like

Every candidate signal has a pathological optimization, which is why none may become a target:
dependency count is gamed by copying code instead of depending on it; files changed by growing one god
file; interface size by hiding complexity behind untyped payloads; context bytes by compressing code
until it is unreadable; and a craft score by writing prose the grader likes.

This is why craft evidence stays advisory and why `P1` holds: every signal terminates in a semantic
evaluator that can be asked *why*, and none of them gates anything on its own.
## 49. The smallest next milestone

**Benchmark-first, and deliberately small.** This project's own history is the argument: Eval V1,
calibration, multi-property and the `P12` control all validated the instrument before anything depended
on it, and production craft reflection has no ground truth to validate against.

The minimum reuses the whole existing substrate — scenario loading, fresh isolated trials, blind
per-property grading, comparison that proves only one field differed. Two repository states differing
**architecturally, not behaviourally**, both satisfying the same accepted intent; one fixed task
contract replayed against each under a fixed configuration; mechanical evidence from files read, bytes
read, tool calls and files changed; bounded semantic observations under composability, domain alignment
and change locality. Findings, never a score.

If a fixed configuration shows materially different change cost across two behaviourally equivalent
states, the instrument works. If it does not, **the observable is wrong and no amount of sequence
length will fix it** — the lesson the single-property ceiling taught, and the one
[§58](#58-craft-returns-discovered-consequences-not-verdicts) eventually collected.

**Explicitly not in that milestone:** a craft role or review purpose (no production routing exists to
justify one under `P2`); a dependency database or static-analysis layer; architecture policy files;
CUPID scoring; holdout trajectories; automatic refactoring; production integration.

## 50. Calibrating the instrument — and why there is no reference architecture

§49 proposed comparing two repository states and asking which the evaluator finds worse. That design has
a hole, and naming it is the point of this section: **a two-state good-versus-degraded experiment can be
passed by an instrument that merely prefers whatever its designer built as the good one.** Detecting the
planted degradation proves the instrument is sensitive. It proves nothing about whether the instrument
recognises quality or recognises resemblance.

The proposed fix was a vetted reference architecture to calibrate against. That instinct is right about
the problem — evaluator ground truth is missing — and wrong about the remedy.

### 50.1 Reject the yardstick

A reference architecture used as a yardstick asks *how close is this to the good one*, and three
independent lines of evidence say that measures the wrong thing. **Agent-benchmark precedent:**
SWE-bench carries a gold patch, but hidden tests grade — behaviour is the yardstick — and frontier
models have been found reproducing gold patches verbatim, so a reference that leaks becomes worthless
as ground truth. **Proofbound's own `P12` result:** supplying an evaluator with the reasoning that
produced an artifact *lowered* its completeness, concentrated on the obligation that reasoning argued
for; showing it "the good architecture" first is the same hazard. **Architecture has no unique
realisation:** a modular monolith with explicit internal boundaries and an event-driven decomposition
may both be excellent for one accepted intent, and ranking by proximity to either measures style, which
`P11` already refuses to let become authority.

### 50.2 What replaces it: a calibration case with declared property status

The thing actually needed is not something to resemble. It is **cases whose architectural property
status is known**, which is precisely the shape Proofbound already validated for semantic evaluation:
planted ground truth, blind grading, positive and negative controls.

> A **calibration case** is one accepted engineering intent, a set of **behaviourally equivalent**
> repository states, and a declared, independently vetted status for each state against a small set of
> named architectural properties.

No state is privileged, and none is "the reference". Two states are good; one is degraded on exactly one
declared property. The evaluator is never told which is which, and — decisively — **is never shown
another state at all**. It judges one state against the accepted intent, exactly as a spec-reflector
judges one artifact. Reference blindness is not a rule bolted on; there is no reference to be blind to.

Only the grader holds declared status, and its question keeps the shape already validated: *did this
craft report identify the degradation that was planted?*

### 50.3 Sensitivity and specificity

Two requirements, and the second is the one §49 could not test.

| | Question | Control |
|---|---|---|
| **Sensitivity** | Does the instrument detect a real architectural degradation? | `D` — behaviourally identical, degraded on one declared property |
| **Specificity** | Does it refrain from calling a structurally different but genuinely good architecture degraded? | `E` — behaviourally identical, structurally different, no degradation planted |

`E` is the positive control, and it is what makes "the instrument prefers its designer's architecture"
a falsifiable hypothesis rather than an unexamined assumption. A craft report that finds degradation in
`E` is a **false positive**, and the calibration must be able to say so — the same discipline as the
grader negative controls, where a report raising four genuine distractor findings still had to be
refused credit for the obligation it never identified.

### 50.4 Behavioural equivalence is what isolates architecture

All states satisfy the same contract and pass the same tests. Without that, a craft evaluator would
simply rediscover correctness failures and the experiment would measure nothing new.

Two shapes the degraded state must be allowed to take, because both are real and one is
counter-intuitive:

- **Under-structured.** A single service, shared mutable state, provider logic embedded in domain logic.
  Fewer files, fewer boundaries, worse craft.
- **Over-structured.** Interfaces nobody needs, eventing without a reason, fragmented modules, layers of
  indirection. Mechanically it looks maximally decoupled; the change-context cost is worse.

An instrument that used size or coupling counts would score the first as good and the second as
excellent. Both must be detectable as degradations, which is exactly why `P13` refuses size metrics and
why **proportionality**, not minimisation, is the property under test.

### 50.5 Properties are bound to scenarios, not asserted

ATAM's contribution here is a discipline, not a vocabulary: a quality attribute is meaningless until it
is expressed as a scenario with a **response measure**, and the method's outputs are risks, sensitivity
points and tradeoff points — never a score. Independent corroboration, from a tradition unrelated to
CUPID, of the position this document already took.

So a case property is a scenario rather than an adjective. Not *"provider isolation is good"* but
*"replacing the payment provider does not require changes in the order domain"* — which has a response
measure, can be probed by an actual change, and cannot be satisfied by naming an interface
`PaymentPort`. **Two layers, kept apart:** CUPID supplies the general lenses a reflector reasons with;
a calibration case supplies case-specific properties tied to its own scenarios. The lenses are how the
evaluator thinks, the case properties are the ground truth it is graded against, and neither is a global
registry.

### 50.6 Case properties are not engineering invariants

A named case property such as *provider replacement stays local* is **benchmark ground truth**. An
accepted engineering invariant such as *payments must not depend on presentation* is a projection of an
accepted decision and may block
([§37.4](long-running-autonomy.md#374-executable-invariants--accepted-decisions-made-operative)). They
must not merge: a case property carries no production authority whatever, and a production repository is
never continuously compared against an exemplar. Where an organisation genuinely maintains a template
service, `P11` governs — it is evidence, and becomes authority only through an accepted decision.

### 50.7 Vetting, and the reference that can itself be wrong

A state is not good because a strong engineer wrote it, because tests pass, or because it looks clean;
architecture is tradeoff-sensitive and an exemplar can be wrong for its own accepted intent. The minimum
credible vetting: intent and constraints stated; each property expressed as a scenario with a response
measure; the good states independently challenged against those scenarios by someone who did not build
them; the degraded state's planted property named and its behavioural equivalence demonstrated; human
acceptance as the stopping authority. Proofbound-shaped, but terminating at a person rather than
recursing.

### 50.8 Tradeoffs mean there may be no ranking

Two sound states may differ in tradeoff profile — one better on change locality, the other on
operational simplicity — with neither dominating. The instrument must be able to report **different
defensible tradeoff** rather than being forced to order them. Demanding a total ordering over good
architectures manufactures a ranking the evidence does not contain: a composite score in different
clothes.

### 50.9 Triangulation is the long-term answer to "bullet-proof"

No evaluator can prove architectural optimality; tradeoffs make that incoherent. The realistic standard
is that architectural degradation becomes **hard to hide**, because correctness, declared invariants,
mechanical structure, independent semantic reflection, calibrated controls, future-change behaviour,
context economy and longitudinal evidence each give the process an independent way to falsify its own
assumptions. One property corroborated across channels beats any single verdict.

### 50.10 The amended minimal experiment

§49's structure is kept with one change: **three states, not two.** `R` is good and vetted against the
case's property scenarios; `E` is good, structurally different, independently vetted; `D` is
behaviourally identical and degraded on exactly **one** named property. Freeze the contract,
configuration, harness version, grader, timeout, trial count and arm order; replay the identical
contract against each state; take one fresh state-blind reflection per state. An independent grader
holding declared status decides whether the degradation was identified in `D` and whether `E` was left
alone. **Success is sensitivity and specificity together**; failure means the instrument recognises
resemblance rather than quality. Neither result produces a score, a ranking, a blocking finding or
production routing.

Deliberately excluded: agent-generated candidates, multiple cases, multiple degraded properties,
longitudinal trajectories, and any comparison of Proofbound against a bare model.

### 50.11 The ladder, and the bar for production

Each rung validates a claim the next depends on: three-state calibration → several independent
properties per case → future-change probes as primary evidence → agent-generated candidates → ordered
trajectories → comparison of whole engineering configurations. A probe must be a plausible extension of
the domain, never an evaluator-only fact, and diverse enough that no single speculative abstraction
wins — otherwise the benchmark rewards **speculative generality**.
[§59.1](#591-what-a-calibration-probe-has-to-satisfy) adds the conditions this case was missing.

**Craft reflection reaches production routing only when** it detects controlled degradation, accepts
equivalent-good alternatives, demonstrably does not reduce to size or coupling heuristics, has a
calibrated grader, holds across more than one domain, repeats under a frozen configuration, and has its
limitations written down. Until then it is an evaluation experiment.

## 52. What the failed calibration actually showed

Calibration V1 failed on both counts — sensitivity 3/5, specificity 7/9, every false positive on the
structurally different sound state. The tempting reading was that Proofbound lacked a transformation
from intent into bound architectural consequences, and that an evaluator handed accepted design
decisions would have judged correctly. That reading does not survive the evidence.

**It was not missing artifact semantics.** The calibration ran on three repositories containing no
proposal, design or specification at all. And the proposed remedy would have destroyed the experiment:
handing the reflector *"delivery owns provider-specific knowledge"* converts *is this architecture
sound* into *does this code match the stated rule* — conformance against an accepted referent, which is
coherence ([§38.2](long-running-autonomy.md#38-cumulative-coherence)); craft is defined by having no
such referent (§41). The calibration would have passed by measuring something else.

**The hypothesis it produced, and V2 destroyed.** V1's intent stated in every arm that more than one
provider was expected, so the decision expected to vary was named visibly in sound and degraded states
alike — and the reflector still reasoned from diff size. The hypothesis that followed was a **question
never asked**: the reflector was asked what the change touched, never which changeable decision each
part exists to hide. Parnas grounds that question, and under it `state-a` hides the provider decision
behind an explicit contract, `state-b` behind registration and dispatch with no interface type, and
`state-c` nowhere — two architectures being equivalent when they hide the same decisions whatever their
form, which is the anti-imitation rule
[§51.1](execution-and-review.md#511-bind-consequences-not-resemblance) reaches from another direction.

V2 tested it and **refuted it** ([§56](#56-why-routing-could-not-have-worked-here)); §59 found the
deeper reason, and §58 the deepest.

## 53. Craft, coherence, and the loop between them

The boundary sharpens rather than moves.

| | Referent | May block | Question |
|---|---|---|---|
| **Coherence** | Accepted decisions and their bound consequences | Yes, on the authority of the decision it projects | Does the system still uphold what was accepted? |
| **Craft** | None | Never | Which decisions is this system failing to hide that nobody decided to hide? |

They compose into a loop needing no new machinery: a craft observation is architectural pressure;
pressure is escalated rather than settled by a bounded worker (`P7`); escalation produces a proposal, a
decision and a bound consequence through the ordinary acceptance chain; from there the consequence is
coherence's to protect, and may project into an executable invariant
([§37.4](long-running-autonomy.md#374-executable-invariants--accepted-decisions-made-operative)).

The direction matters: pressure becomes authority only by passing through an accepted decision. Craft
never acquires authority by being repeatedly observed, which is what keeps `P11` intact — an
evaluator's preference cannot become policy by repetition.

## 54. Calibration V2 — separate the explanations

V1 could not distinguish a weak reflector, insufficient routed context, an unobservable property, an
ambiguous grader or a badly framed task. V2 separated the two the evidence implicated, as a **context
treatment** rather than a new instrument: the same three states, property, models, grader, probe and
counterbalanced order, with the treated arm additionally receiving the decisions expected to vary,
stated as questions and sourced from the **intent** rather than the ground-truth manifest — sourcing
them from the manifest would have made the result unable to generalise past the benchmark.

**Falsifiers, fixed in advance.** Unchanged sensitivity means the reflector is not context-starved and
the instrument itself is the problem. Recovered sensitivity at the cost of specificity means the
questions are functioning as hints. Both improving means routing was the deficit.

## 55. Calibration V2 — the result

Paired re-reflection over fourteen retained V1 implementations, both arms on each, counterbalanced,
everything but the appended questions byte-identical — which removes implementation variance by
construction. **Sensitivity 2/5 untreated and 2/5 routed; specificity 6/7 and 5/7.** On the degradation
the treatment changed nothing at all: all five `state-c` pairs returned the same outcome in both arms,
zero discordant. The pre-registered falsifier for "the reflector is not context-starved" fired cleanly.
Configuration and per-pair record:
[§E50.B](evidence/evaluation-runs.md#e50b-system-craft-calibration-v2--routing-is-not-the-deficit-and-the-instrument-does-not-repeat).

## 56. Why routing could not have worked here

The routed arm answers the routed questions **correctly** — and then rules for the defence:

> Provider identity and its associated wire format (endpoint, auth header, payload field names) are now
> owned by `app.py`, which is the application entry point. **This aligns with the accepted intent:
> "Provider credentials and endpoints are configuration, not user input."**

That is a `state-c` reflection — the degraded state — graded as claiming the property upheld. It
identifies the concentration precisely: what moved, where it went, that `app.py` did not hold it
before. Question routing worked. The reflector then reads the intent's configuration clause as
*authorising* the concentration, because configuration is what a composition root is for.

It is not a bad reading. The intent says credentials and endpoints are configuration; **it never says
where configuration may live.** The specificity failures are the same gap inverted: a `state-b`
regression calls a provider *name* flowing through the application layer a leak, and the manifest says
`state-b` is sound because a name is not an endpoint, auth scheme, payload field or error code. With no
stated line, the reflector drew its own — stricter than the manifest here, looser there.

So V1's diagnosis was wrong in an instructive way. The deficit was never a missing question and never
missing information; it is a **missing criterion**.
[§59](#59-the-probe-rewards-the-degradation-it-plants) found why no wording repairs it on this case,
and [§58](#58-craft-returns-discovered-consequences-not-verdicts) why no wording repairs it at all: a
criterion is what §41 denies craft by definition.

## 57. The instrument does not repeat itself

V2's untreated arm was a byte-identical rerun of V1 on V1's own implementations, so it also measured
whether the instrument returns the same verdict twice. On thirteen comparable implementations it agreed
with itself **nine times and disagreed four** — same code, same diff, same prompt, same model, same
grader. The retest disagreement is larger than the treatment effect it was built to detect, so V1's 3/5
and 7/9 were never stable measurements. The dedicated repeatability run that followed put numbers on it
— 43% of reflector conclusions and 17% of grader readings differ from their own modal answer on
unchanged input
([§E51](evidence/evaluation-runs.md#e51-craft-instrument-repeatability--both-layers-move)) — and the
methodology it produced is now general to all Proofbound evaluation
([§E22](evaluation-comparison.md#e22-reliability-before-validity)).

## 58. Craft returns discovered consequences, not verdicts

§58 was written as a question. Three more milestones answered it.

**The evidence separates two layers that were always conflated.** On identical evidence, reflectors
name what moved and where in 57 of 60 reports, and disagree with their own modal *conclusion* 43% of
the time ([§E51](evidence/evaluation-runs.md#e51-craft-instrument-repeatability--both-layers-move)).
Once the probe genuinely exercised a boundary and the column asked one atomic question, untreated
discovery of the planted pressure ran **10 of 10** on the degraded architecture against 1 of 10 and 2
of 9 on the sound ones
([§E55](evidence/evaluation-runs.md#e55-the-atomic-column-discriminates-and-the-untreated-reflector-is-already-at-ceiling)).
The factual layer is reliable. The normative layer is not.

**The instability is not all evaluator failure.** Five reflectors said `app.py` is a composition root
and configuration belongs there; four said provider integration knowledge was misplaced. The accepted
intent decides neither. That is **normative underdetermination** — disagreement about a tradeoff the
authority left open — and it is epistemically correct behaviour, not noise to be averaged away.

**And the cause was structural, not statistical.** §41 defines craft as having **no accepted
referent**. A verdict needs one. Asking an evaluator for *"is this degraded?"* asks it to invent the
criterion the definition denies it, so each evaluator invents a different one and the spread is the
spread of invented criteria. Three calibrations failed at that seam, and no wording repairs it.

So craft's output is a **discovered consequence**: a claim about what future change becomes broader,
stated so it could be shown false.

> *Adding a provider that reports results differently now requires changing code that is not about any
> provider.*

Not *"this architecture is degraded"*, which needs a referent, and not merely *"provider knowledge is
in `notifications/status.py`"*, which is an observation without a stake. A consequence predicts, so it
can be tested — by making the change, by substituting an implementation, by a dependency query — and
[§51.1](execution-and-review.md#511-bind-consequences-not-resemblance) already requires exactly this of
specifications: bind consequences, never resemblance. Craft findings obey the rule the rest of the
architecture already obeys.

**This changes no machinery.** §53's loop already routes a craft observation as pressure → parent →
accepted decision → bound consequence → coherence's to protect → possibly an executable invariant
([§37.4](long-running-autonomy.md#374-executable-invariants--accepted-decisions-made-operative)). What
changes is the shape of the thing entering that loop, and it now matches what the loop always expected.

**What a finding carries** is decided by the Field Test, not a schema: the observation it rests on, the
consequence it predicts, and evidence a reader can check. Counter-considerations belong in the prose —
a small system, an unlikely change, a framework constraint may all make the consequence acceptable —
and no `disputed`, `ambiguous` or `confidence` state is created, because nothing mechanical consumes
one (`P3`). Unresolved tradeoffs stay unresolved in the report and in the dispersion across samples.

**Authority is untouched.** Ten evaluators agreeing creates no engineering authority (`P5`), and one
evaluator's consequence may be worth acting on without agreement at all. Recurrence still becomes
binding only through an accepted decision (§53), and the three lenses stay what §43 made them —
questions that orient discovery, never criteria to be scored.

## 59. The probe rewards the degradation it plants

Calibration V3 was to change the criterion and freeze everything else. Deriving one meant reading the
fixtures against the accepted intent asking *what is actually entailed here*, and the case did not
survive that question.

**The probe favoured the degraded state, and always had.** The future contract asked for a second
provider differing in endpoint, header and payload shape with everything else unchanged, and under it
`state-c` edited **one** file while both sound states edited three, in every trial ever run. Change
locality is one of the three lenses the craft task asks about, so every reflector praising `state-c`'s
locality reported a fact: the instrument was not failing to see the degradation, the probe was not
exercising it.

**The consequence that would discriminate was not entailed**, the narrower one that was entailed failed
its counterexample, and the pressure that remained was already discovered four times in five at
baseline. Analysis: [§E53](evidence/evaluation-runs.md#e53-why-calibration-v3-cannot-run-on-this-case).

### 59.1 What a calibration probe has to satisfy

> **The probe must be a change the planted degradation actually makes worse**, measured by the lenses
> the evaluator is asked to use. A probe the degradation handles more cheaply than the sound states
> measures the evaluator's willingness to disbelieve its own evidence.

Four conditions follow. **Entailment**: the consequence the degradation violates follows from the
accepted intent the evaluator receives, never from the author's private expectation. **Exercise**: the
probe changes the decision that consequence governs, so the degraded state cannot absorb it without
propagating knowledge outward. **Discrimination**: an answer-blind structural analysis, authored before
any call, can say *why* each location had to change in each state — provider-specific work, boundary
composition, an uninterpreted pass-through, or a module whose purpose is provider-independent. The last
category is the degradation, and it is a difference in **kind**, never a file count: a sound
architecture may well touch more files because its responsibilities are separated. **Headroom**:
baseline discovery leaves room to move, which is the one gate measurement alone can settle, so a
baseline arm runs before a treatment is designed rather than after.

The repaired probe — a second provider reporting outcomes in the response body rather than the status
line, which the degraded state cannot absorb without teaching a provider-independent module about a
provider or restating the retry policy — is designed in
[`case-repair-design.md`](../../../evals/craft/notification-provider-boundary/case-repair-design.md).

The case satisfies none of the three. Repairing it means changing the future contract *and* the
accepted intent — two fixture changes, which belong to their own milestone: moving the fixture and the
criterion together would leave the result unattributable, which
[§E24](evaluation.md#e24-what-it-takes-to-call-an-increment-an-improvement) exists to prevent.

## 60. What five milestones never measured

§42 defines craft as **repository discovery context staying proportional to the conceptual size of a
change**. Every calibration measured something else: whether a reflector classifies an architecture
correctly. That is not a restatement of the definition — it is a different observable, and the drift
went unnoticed for five milestones because a verdict is easy to grade.

The definition's own observable was collected once and never used. V1 recorded context traversed but
not changed for every trial: `state-a` median 5, `state-b` median 7, `state-c` median 5. It does not
separate the states — the alternative-good architecture reads the most, the degraded one reads no more
than the sound one. But that was measured under the probe
[§59](#59-the-probe-rewards-the-degradation-it-plants) later showed does not exercise the degradation,
so the honest statement is not *the canonical observable fails*; it is that **the canonical observable
has never been given a fair test**, while five milestones tested a proxy for it.

That reframes what comes next. A consequence-shaped craft finding (§58) is a claim about what future
work becomes broader — which is the definition's language, not a verdict's. The way to test such a
claim is to make the change and observe the cost, and the sharpest available form of that is the
question `P13` has always implied:

> When a boundary genuinely hides a decision, can work outside it proceed from the boundary's contract
> instead of its implementation — at the same correctness, for less repository context?

That is measurable without any verdict, it tests the definition rather than a proxy, and it fails
honestly: if hiding an implementation costs correctness, or if the contract has to reproduce the
implementation to work, the hypothesis is wrong. It also needs its own controls, because **more
modules is not the claim** — an over-fragmented arm must be able to win, and a minimum-sufficient-
contract ladder is what keeps the question *smallest context that preserves correctness* rather than
*smallest context*.

The notification-provider case is complete as a calibration corpus. It established what a probe must
satisfy, what an atomic column is, that discovery of an exercised pressure saturates, and that
judgement is underdetermined where intent is silent. Another run on it would answer nothing open, and
running it anyway would be experimental inertia. It stays as reference evidence, failures included.
