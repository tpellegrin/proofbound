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
