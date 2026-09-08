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
are blind to it. What is missing is measurement, and the correct move is to **compose the pieces
already designed rather than invent a parallel concept beside them**:

| Piece | Status |
|---|---|
| `CE1` passive context-economy telemetry — repository files read, bytes read, tool calls | Designed; unblocked since M2C; not built |
| `CE2` controlled representative-change experiment — replay one contract against two repository states with a fresh worker | Designed; not built |
| [§38.2](long-running-autonomy.md#38-cumulative-coherence) cumulative coherence audit | Designed; not built; trigger policy deliberately unresolved |
| [§37.4](long-running-autonomy.md#374-executable-invariants--accepted-decisions-made-operative) executable invariants | Designed; not built |
| **Semantic craft reflection** | **Absent** |
| **Longitudinal trajectory comparison** | **Absent** — `CE2` is two points, not a sequence |

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
| **Coherence** | Does the repository still conform to the accepted baseline plus the decisions that authorize divergence from it? | The accepted baseline and accepted decisions ([§38.2](long-running-autonomy.md#38-cumulative-coherence)) |
| **Craft** | Did the system become harder to understand and change? | **None** |

The referent is what separates them, and it is not a presentational distinction. Correctness and
coherence both ask whether reality conforms to something somebody accepted. **Craft has nothing
accepted to conform to** — a system can conform perfectly to its baseline and still be miserable to
work in, and no one ever accepted "stay easy to change" as a contract clause.

Three consequences follow immediately, and they are the spine of this design:

- Craft is **relative, never absolute**: the only honest question is whether a property became better,
  worse, or unchanged, because there is no accepted standard to score against.
- Craft **cannot block** anything. A finding that violates no accepted referent is an observation, and
  treating it as a gate would let a generic concern override accepted engineering intent — `P5`
  generalized: integrity is not authority, and neither is an opinion about the future.
- Craft and coherence are **not merged**. Building one evaluator for both would give the blocking
  authority of coherence to the advisory findings of craft.

## 42. What system craft means here

Not "good code", "clean architecture" or "simple". Stated as a measurement of `P13`'s second surface:

> **A well-crafted system is one where the repository discovery context required to make a change stays
> proportional to the conceptual size of that change.**

Proportionality carries the weight. A cross-cutting security change legitimately reaches many places —
its conceptual size is large, and touching a lot is not a defect. The failure mode is **disproportion**:
a small, single-concept change that requires loading, understanding, or modifying distant parts of the
system.

This definition explicitly does not reward smallness. A system with many services, modules and
workflows can be simple if boundaries are clear, state ownership is legible, contracts are stable and
dependencies are directional; a four-file system can be entangled. **Structural size and conceptual
complexity are different measurements**, which is exactly why `P13` refuses size metrics and why
counting files, services or dependencies cannot stand in for craft.

It is a guiding property, not an invariant. Promoting it to a rule would make every cross-cutting
change a violation.

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

| Property | Mechanically observable | Semantic question | Danger if universalized |
|---|---|---|---|
| **Composable** | New outgoing dependency edges; public surface additions; new configuration keys | Were these dependencies necessary, coherent, and in the right place — or does this component now know something about another that it should not? | Rewards copy-paste over reuse: duplicating code removes an edge |
| **Unix philosophy** | Reasons-to-change concentrated in one component; growth of a component already large | Does this component still have one coherent purpose, or did it acquire an unrelated responsibility? | Rewards splitting for its own sake; indiscriminate factoring is not the mechanism of benefit ([§28.5](context-economy.md#285-measurement-is-mechanical-refactoring-is-semantic)) |
| **Predictable** | Retry, ordering, idempotency, compatibility and failure-visibility surfaces touched | Are the semantics of this change explicit and observable, or did it add an implicit temporal or ordering assumption? | Largely *correctness*, not craft — most of it is already what the planted-obligation scenarios test |
| **Idiomatic** | Deviation from prevailing local structure | Does this belong here, and where it deviates, is the deviation deliberate? | **The sharpest `P11` hazard.** "Looks like the surrounding code" would make accumulated debt self-enforcing |
| **Domain-based** | Infrastructure vocabulary appearing inside domain modules; domain concepts split across boundaries | Does the code still name the problem, or has provider/infrastructure language displaced domain language? | DDD is not mandatory; the question must remain meaningful in systems that never adopted it |

Two notes that keep the vocabulary from becoming taxonomy. **Composable and Unix philosophy overlap and
should not be split into two evaluator dimensions**: North's own distinction is that Unix philosophy is
about how code is *used* while single-responsibility is about its *internals*, which is a difference in
viewpoint, not a second measurement. And **Predictable belongs mostly to correctness** — Proofbound's
existing scenarios already plant retry, ordering and compatibility obligations and grade them.

A minimal first vocabulary is therefore **three lenses, not five**: composability (including cohesion),
domain alignment, and change locality. Idiomatic fit is deferred until the `P11` tension has a
defensible answer; Predictable stays where it already works.

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
provider-neutral first, token counts as secondary. The evaluation harness already produces most of it
as a by-product of execution; worker logs carry the tool trajectory, and the scope diff carries what
changed. **No new instrumentation is required to begin**, only derivation from evidence already
retained.

The hard problem is interpretation, and it must be stated before any number is collected: **an agent's
retrieval behaviour is not a property of the architecture.** A worker may open thirty files because it
is thorough, because it is weak, because the harness encourages breadth, or because the system is
genuinely tangled. A raw file count cannot distinguish those, and an evaluation that rewarded "read
fewer files" would reward incuriosity — which is worse than the problem it set out to detect.

The control is the one this project has already used four times: **hold the agent configuration fixed
and vary the architecture.** An absolute context footprint means nothing; the *contrast* between two
repository states executing the identical contract under the identical configuration means something.
That is precisely `CE2`'s structure, and it generalizes from "one refactoring step" to "two
architectural histories" without changing shape.

The derived quantity worth measuring first is **context traversed but not changed** — material the
worker had to understand and did not need to modify — read against the conceptual size of the change,
not against the repository's size.

## 46. Longitudinal composition needs no new identity

A trajectory is `S0 → T1 → S1 → … → Tn → Sn`. Applying the field test — *which invariant becomes
impossible without a new durable identity?* — none does:

- **Repository state** is already identified by a Git commit; a synthetic evaluation can use a tree
  hash. There is no case for `proofbound-system-state-v1`.
- **A trajectory** is `(initial commit, ordered task-sequence identity, configuration)`, and the
  ordered commits it produced. Derived, not stored.
- **Craft observations** are evaluation evidence. `P13` and
  [§28.3](context-economy.md#283-why-this-is-not-a-ledger-field) already forbid execution economics
  from entering the artifact ledger, and evaluation evidence is not `L4` provenance. Small committed
  summaries survive; transcripts do not.

**Architectural pressure** — the same craft observation recurring across many changes, such as three
domains independently re-implementing provider-interaction semantics — is a **query over accumulated
evaluation evidence, never a stored fact**. Its output is an inquiry, not a refactoring: it is evidence
that a cross-cutting decision may be missing, which is exactly the escalation `P7` already requires a
bounded worker to raise rather than settle. Pressure detected → parent → accepted decision → possibly a
[§37.4](long-running-autonomy.md#374-executable-invariants--accepted-decisions-made-operative) invariant. Never pressure detected → abstraction introduced.

## 47. Who decides

Craft findings are advisory to the parent, which already owns routing, architecture and the choice of
authoritative context. The parent may accept, revise, open architectural work, or record a local
decision. What neither the parent nor an evaluator may do is let a craft observation override accepted
engineering intent, and what Proofbound may never do is refactor a system because a metric moved.

## 48. What gaming would look like

Every candidate signal has a pathological optimization, which is why none may become a target:

| Signal | Gamed by |
|---|---|
| Dependency count | Copying code instead of depending on it |
| Files changed | Growing one god file |
| Interface size | Hiding complexity behind untyped payloads |
| Context bytes | Compressing code until it is unreadable |
| Craft findings | Trivial abstractions that look composable |

Two structural defenses, neither of which is a threshold. **Mechanical facts are inputs to a semantic
judgement, never verdicts** — the rule `T10` already depends on, and the reason no metric is a gate
anywhere in Proofbound. And the strongest one: **measure change cost on tasks the agent did not author
and could not anticipate.** Gaming a future-change measurement requires predicting the future change.

## 49. The smallest next milestone

**Benchmark-first, and deliberately small.** This project's own history is the argument: Eval V1,
calibration, multi-property and the `P12` control all validated the instrument before anything depended
on it, and production craft reflection has no ground truth to validate against.

The minimum is `CE2`'s structure with a craft lens on top, reusing the entire existing substrate —
scenario loading, fresh isolated trials, per-property blind grading, comparison that proves only one
field differed:

- Two repository states that differ **architecturally, not behaviourally**, both satisfying the same
  accepted intent.
- One fixed task contract, replayed against each with a fixed agent configuration.
- Mechanical: files read, bytes read, tool calls, files changed, context traversed but not changed.
- Semantic: bounded observations under three lenses — composability, domain alignment, change locality —
  each answered independently, relative to the other state. Findings, never a score.
- Output: a metric vector plus observations. No verdict, no threshold, no blocking, no persistence
  beyond an ordinary evaluation summary.

If a fixed agent configuration shows materially different change cost across two states that are
behaviourally equivalent, the instrument works and longitudinal trajectories become worth building. If
it does not, the observable is wrong and no amount of sequence length will fix it — the same lesson the
single-property ceiling taught.

**Explicitly not in that milestone:** a craft role or review purpose (no production routing exists to
justify one yet under `P2`); a dependency database or static-analysis layer; architecture policy files;
CUPID scoring; holdout trajectories; automatic refactoring; production integration.

**Deferred with a stated trigger.** Longitudinal trajectories become justified once the two-state
experiment shows the observable discriminates. Holdout trajectories become justified when agents are
tuned against known future tasks — the overfitting rule already learned in calibration. A craft review
purpose becomes justified when craft reflection moves into production routing, and not before.

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
independent lines of evidence say that measures the wrong thing.

**Precedent from agent benchmarks.** SWE-bench carries a gold patch, but the gold patch is not what
grades: hidden `FAIL_TO_PASS` and `PASS_TO_PASS` tests are. The reference exists to prove the problem is
solvable; *behaviour* is the yardstick. And an OpenAI audit found frontier models reproducing gold
patches verbatim — a reference that leaks into a model becomes worthless as ground truth, which is a
structural warning about any design where ground truth is a repository somebody could recognise.

**Proofbound's own P12 result.** Supplying an evaluator with the reasoning that produced an artifact
*lowered* its completeness, concentrated on the obligation that reasoning argued for. An evaluator shown
"the good architecture" before judging a candidate is the same hazard with a different artifact.

**Architecture has no unique realisation.** A modular monolith with explicit internal boundaries and an
event-driven decomposition may both be excellent for the same accepted intent. An instrument that ranks
by proximity to one of them is measuring style, and `P11` already refuses to let prevailing patterns
become authority.

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

So a case property is stated as a scenario rather than an adjective. Not *"provider isolation is good"*
but *"replacing the payment provider does not require changes in the order domain."* That has a response
measure, it can be probed by an actual change, and it cannot be satisfied by naming an interface
`PaymentPort`.

**Two layers, kept apart.** CUPID supplies the *general lenses* a craft reflector reasons with —
composability, domain alignment, change locality. A calibration case supplies *case-specific properties*
tied to its own scenarios. The lenses are how the evaluator thinks; the case properties are the ground
truth it is graded against. Neither is a global registry.

### 50.6 Case properties are not engineering invariants

A named case property such as *provider replacement stays local* is **benchmark ground truth**. An
accepted engineering invariant such as *payments must not depend on presentation* is a projection of an
accepted decision and may block ([§37.4](long-running-autonomy.md#374-executable-invariants--accepted-decisions-made-operative)).

They must not merge. A case property carries no production authority whatever, and a production
repository is never continuously compared against some exemplar. Where an organisation genuinely
maintains a template service, `P11` governs: it is evidence, and it becomes authority only if the
project accepts a decision that says so.

### 50.7 Vetting, and the reference that can itself be wrong

A state is not good because a strong engineer wrote it, because tests pass, or because it looks clean.
Architecture is tradeoff-sensitive, and an exemplar can be wrong for its own accepted intent.

The minimum credible vetting: intent and constraints stated; each property expressed as a scenario with
a response measure; the good states independently challenged against those scenarios by someone who did
not build them; the degraded state's planted property named and its behavioural equivalence
demonstrated; human acceptance as the stopping authority. Proofbound-shaped, but it terminates at a
person rather than recursing.

### 50.8 Tradeoffs mean there may be no ranking

`R` and `E` may differ in tradeoff profile — one better on change locality, the other on operational
simplicity — with neither dominating. The instrument must be able to report **different defensible
tradeoff** rather than being forced to order them. Demanding a total ordering over good architectures
would manufacture a ranking the evidence does not contain, which is the same error as a composite score
wearing different clothes.

### 50.9 Triangulation is the long-term answer to "bullet-proof"

No evaluator can prove architectural optimality; tradeoffs make that incoherent. The realistic standard
is different and achievable:

> Architectural degradation becomes **hard to hide**, because correctness, declared invariants,
> mechanical structure, independent semantic reflection, calibrated controls, future-change behaviour,
> context economy and longitudinal evidence each provide an independent way for the process to falsify
> its own assumptions.

One property corroborated across channels beats any single verdict. V1 exercises two of them against
declared truth; the rest is the ladder, not the first rung.

### 50.10 The amended minimal experiment

§49's structure is kept — one accepted intent, one contract replayed, one frozen configuration, CE1
telemetry, three lenses, no score — with one change: **three states, not two.** `R` is good and vetted
against the case's property scenarios; `E` is good, structurally different from `R`, independently
vetted against the same scenarios; `D` is behaviourally identical and degraded on exactly **one** named
property.

Freeze one future-change contract, one worker configuration, one harness and version, one grader, one
timeout, one trial count and one arm order. Replay the identical contract against each state. Record
mechanical traversal from evidence already retained, and one fresh, state-blind craft reflection per
state under the three lenses. An independent grader holding declared status decides whether the planted
degradation was identified in `D` and whether `E` was left alone.

**Success** is sensitivity and specificity together. **Failure** — `E` marked down for being different,
or `D` passing unnoticed — means the instrument recognises resemblance rather than quality, and no
amount of extra scenarios or trials would fix that. Either result is worth having, and neither produces
a score, a ranking, a blocking finding or production routing.

Deliberately excluded from V1: agent-generated candidates, which would add generation variance before
the instrument is validated; multiple cases; multiple degraded properties; longitudinal trajectories;
and any comparison of Proofbound against a bare model, worth nothing until the instrument is known to
work.

### 50.11 The ladder, and the bar for production

Each rung validates a claim the next one depends on: three-state calibration → several independent
properties per case → future-change probes as the primary evidence → agent-generated candidates →
ordered trajectories → comparison of whole engineering configurations, including Proofbound against a
bare model. Fairness constraints on future probes apply from the moment they carry weight: a probe must
be a plausible extension of the domain, never an evaluator-only fact, and diverse enough that no single
speculative abstraction wins — otherwise the benchmark rewards **speculative generality**, which is the
opposite of proportionality.

**Craft reflection reaches production routing only when** it detects controlled degradation, accepts
equivalent-good alternatives, demonstrably does not reduce to size or coupling heuristics, has a
calibrated grader, holds across more than one domain, repeats under a frozen configuration, and has its
limitations written down. Until then it is an evaluation experiment, exactly as every measurement in
this project has been before the architecture was allowed to depend on it.

## 52. What the failed calibration actually showed

Calibration V1 failed on both counts — sensitivity 3/5, specificity 7/9 with every false positive on
the structurally different sound state. The tempting reading is that Proofbound lacks a transformation
from intent into bound architectural consequences, and that a craft evaluator handed accepted design
decisions would have judged correctly. That reading does not survive the evidence.

### 52.1 The failure was not caused by missing artifact semantics

The calibration ran on three repositories that contained **no proposal, design or specification at
all** — hand-built states and a future-change contract. Whatever is or is not underspecified about
artifact semantics, it cannot explain a result produced where no artifacts existed.

Worse, the proposed remedy would have destroyed the experiment. Handing the reflector *"delivery owns
provider-specific knowledge"* converts *is this architecture sound* into *does this code match the
stated rule* — conformance against an accepted referent, which is coherence
([§38.2](long-running-autonomy.md#38-cumulative-coherence)); craft is defined by having no such
referent (§41). The calibration would have passed by measuring something else.

### 52.2 The information was already there; the question was not

The evaluator's own intent material stated, in every arm: *"More than one delivery provider is expected
over time. Nothing about which providers, or when."* The decision expected to vary was named, visibly,
in both the sound and the degraded states — and the reflector still reasoned from diff size, concluding
that provider concerns "remain confined to `app.py` (the composition root)."

The hypothesis that followed: the deficit is not information the reflector lacked but a **question it
was never asked** — asked what the change touched, never which changeable decision each part exists to
hide. V2 tested exactly that and **refuted it**
([§56](#56-why-routing-could-not-have-worked-here)): asked the question, the reflector answers it
correctly and upholds the degradation anyway.

### 52.3 Parnas gives the missing question a foundation

Parnas's criterion is that one begins with the design decisions likely to change, and each module is
built to hide such a decision from the others. That reframes the craft question:

> Which decision expected to vary does this part of the system hide, and from what?

`state-a` hides the provider decision behind an explicit contract; `state-b` behind registration and
dispatch, with no interface type at all; `state-c` hides it nowhere — endpoint, credential, header
format and payload shape sit in the entry point because no module exists whose purpose is to conceal
them.

Two architectures are equivalent when they hide the same decisions, whatever their form — the same
anti-imitation rule [§51.1](execution-and-review.md#511-bind-consequences-not-resemblance) states for
specifications, reached from another direction. The question is also **answer-blind**: naming the
decision expected to vary is not naming where it should live.

It also reads V1's false positives without appealing to preference: `notify` gaining a `provider`
argument, and a dispatch point changing when a provider is registered, are consequences of hiding the
decision successfully — the boundary used, not breached. V2 found a simpler account
([§56](#56-why-routing-could-not-have-worked-here)).

## 53. Craft, coherence, and the loop between them

The boundary sharpens rather than moves.

| | Referent | May block | Question |
|---|---|---|---|
| **Coherence** | Accepted decisions and their bound consequences | Yes, on the authority of the decision it projects | Does the system still uphold what was accepted? |
| **Craft** | None | Never | Which decisions is this system failing to hide that nobody decided to hide? |

They compose into a loop that already has every mechanism it needs: a craft observation is architectural
pressure; pressure is escalated rather than settled by a bounded worker (`P7`); escalation produces a
proposal, a decision and a bound consequence through the ordinary acceptance chain; from that point the
consequence is coherence's to protect, and may project into an executable invariant
([§37.4](long-running-autonomy.md#374-executable-invariants--accepted-decisions-made-operative)).

Nothing in that loop is new machinery, and the direction matters: pressure becomes authority only by
passing through an accepted decision. Craft never acquires authority by being repeatedly observed, which
is what keeps `P11` intact — an evaluator's preference cannot become policy by repetition.

## 54. Calibration V2 — separate the explanations

V1 cannot distinguish a weak reflector, insufficient routed context, an unobservable property, an
ambiguous grader, or a badly framed craft task. V2 separates the two the evidence implicates, and it is
a **context treatment**, not a new instrument.

**Independent variable.** What the reflector is asked, holding everything else frozen — same three
states, same property, same models, same grader, same probe, same counterbalanced order.

| Arm | Reflector receives |
|---|---|
| **Control** | Exactly what V1 supplied: intent, contract, before-state, diff |
| **Treatment** | The same, plus the decisions expected to vary — stated as questions, never as answers |

The treatment adds a question and no answer, and every underlying fact was already visible in V1's
material, which is what makes it a routing experiment rather than a leak. The questions come from the
**intent**, not the ground-truth manifest; sourcing them from the manifest would make the result unable
to generalise beyond the benchmark.

**Falsifiers, fixed in advance.** Unchanged sensitivity means the reflector is not context-starved and
the instrument itself is the problem. Recovered sensitivity at the cost of specificity means the
questions are functioning as hints. Both improving means routing was the deficit.

**The grader needs its own correction, independently** — its property decomposed into obligations graded
separately, the resolution the multi-property milestone already established for this class of failure.
Decompose the grader *or* treat the reflector, never both at once, or V2 will attribute its result no
better than V1 did. (V2 ran the treatment arm; [§57](#57-the-instrument-does-not-repeat-itself) shows why
the decomposition is not yet the next step either.)

## 55. Calibration V2 — the result

V2 ran §54's experiment with one design change the evidence forced: **paired re-reflection** rather
than a fresh implementation matrix. Fourteen of the fifteen V1 implementation trees still yielded a
reconstructable change, so both arms ran against the same architecture, the same model-written code and
the same diff — removing implementation variance, the largest noise source at this scale, by
construction. The treatment is four questions, 667 bytes, each derived from a sentence the untreated
arm already receives; it names no interface, adapter, registry, port, file or boundary. Full
configuration and provenance: [§E50.B](evidence/evaluation-runs.md#e50b-system-craft-calibration-v2--routing-is-not-the-deficit-and-the-instrument-does-not-repeat).

| | Sensitivity (state-c) | Specificity (state-a, state-b) |
|---|---|---|
| Untreated | 2/5 | 6/7 |
| Question-routed | 2/5 | 5/7 |

**On the degradation, the treatment changed nothing at all.** Not "no net change" — every one of the
five state-c pairs returned the *same* outcome in both arms: three missed in both, two recognised in
both, zero discordant. The three discordant pairs all fall on sound states, one gain and two
regressions, a difference no run this size distinguishes from noise. The pre-registered falsifier for
"the reflector is not context-starved" fired cleanly.

## 56. Why routing could not have worked here

The reports say why, and they say it in almost the same words every time. The routed arm answers
the routed questions **correctly** — and then rules for the defence.

> Provider identity and its associated wire format (endpoint, auth header, payload field names)
> are now owned by `app.py`, which is the application entry point. **This aligns with the accepted
> intent: "Provider credentials and endpoints are configuration, not user input."**

That is a state-c reflection — the degraded state — graded as claiming the property upheld. It
identifies the concentration precisely: it knows what moved, it knows where it went, it knows
`app.py` did not hold that knowledge before. Question routing worked. The reflector then reads the
intent's configuration clause as *authorising* the concentration, because configuration is what a
composition root is for.

It is not a bad reading. The accepted intent says provider credentials and endpoints are
configuration. **It never says where configuration may live.** The invariant the ground truth
encodes — provider wire detail stays out of the notification domain — is not entailed by anything
the reflector was shown, and one clause of what it was shown points the other way.

The specificity failures are the same gap from the other side. A state-b regression observes that the
`provider` string now flows through the application layer and calls that a leak of delivery
configuration into the application API — a real observation, correctly derived from the routed
questions, and the manifest says state-b is sound, because a provider *name* is not an endpoint, an
auth scheme, a payload field or an error code. With no stated line, the reflector drew its own:
stricter than the manifest on state-b, looser on state-c. Routing raised attention to knowledge
movement in both directions, which is what it was designed to do and why it could not move the score.

So V1's diagnosis was wrong in an instructive way. The deficit was never a missing question, and
never missing information. It is a **missing criterion**: the reflector is asked to arrive
independently at a judgement the benchmark encodes privately, from material that does not entail
it. No amount of asking fixes that.

## 57. The instrument does not repeat itself

The untreated arm is a byte-identical rerun of V1's reflection on V1's own implementations, so V2
also measured something V1 could not: whether the instrument returns the same verdict twice.

On thirteen comparable implementations it agreed with itself **nine times and disagreed four**: both of
V1's state-b false degradations came back upheld, a state-a implementation V1 upheld five-for-five came
back a false degradation, and a state-c degradation V1 recognised was missed. Same code, same diff,
same prompt, same model, same grader — different answers.

The retest disagreement is *larger than the treatment effect it was built to detect*. That
reorders everything: V1's 3/5 and 7/9 were never stable measurements, the difference between them
and V2's 2/5 and 6/7 is not a finding, and any future comparison at this scale is measuring its
own variance. Before another treatment is worth running, the instrument needs repeats per
implementation and a reported spread — n=1 per cell cannot support a claim either way.

The obvious repair — state the invariant in the accepted intent — is legitimate in principle and
forbidden to adopt now, after seeing outcomes; the [implementation
plan](../specification-reflection-harness-implementation-plan.md) records the conditions under which a
V3 may use it.

[routing-record]: ../../../evals/results/craft-routing-v1.json
