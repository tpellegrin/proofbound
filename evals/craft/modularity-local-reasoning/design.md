# Modularity and local reasoning — experiment design

Design only. No fixture, no live call, no context-hiding implementation. This document decides
whether the experiment can be built such that **modularity is able to lose**, and how.

## 1. The question

Not *is modular architecture better*, and not *do agents like modules*. The question is narrow
enough to answer:

> For a change whose conceptual responsibility lies outside module `M`, does access to `M`'s
> internal implementation provide material correctness value — and if not, how much smaller is the
> representation of `M` that correct reasoning actually required?

It separates four things the loose version confuses: tasks that genuinely need internals; tasks that
need only external behaviour; tasks that cross the boundary because the product intent says so; and
tasks that cross it only because the boundary leaks. The design addresses each with a task-selection
rule (§5) and a boundary-crossing control (§6).

## 2. The causal claim

The full chain — hiding → stable contract → less inspection → smaller discovery context → lower cost,
correctness preserved — is five hypotheses, and this experiment tests **one link**:

> Replacing access to `M`'s implementation with a sufficient external contract preserves correctness
> for a genuinely external task, while reducing the amount of `M` that entered reasoning.

Everything downstream of that (cost, longitudinal effects, production value) is deferred.

## 3. What "boundary" means here, and what it does not

For this experiment only, a useful boundary is one where a design decision is owned internally,
external callers hold a stable contract, the implementation can vary without callers knowing, and
the chosen task does not modify that contract. Parnas is the reasoning aid, not the authority.

It is explicitly **not** deployment topology. Not microservices, separate repositories, processes,
containers, network boundaries or packages. A modular monolith can have excellent reasoning
boundaries and a microservice system terrible ones. The experiment is defined by *what implementation
knowledge a client must possess*, never by deployment form. It is also not module count, coupling
counts, file sizes or interface presence.

## 4. Domain

**Object storage**, selected over the alternatives.

| Domain | Why not |
|---|---|
| Notification delivery | Four milestones of prior fitting on this corpus. Reusing it would make any result unreadable. |
| Persistence / repository | Query and performance behaviour legitimately leak into callers, so "external" tasks are hard to keep external. |
| Search / index | Ranking semantics legitimately reach clients; the boundary is not supposed to hide them. |
| Payment processing | Regulatory and business rules cross the boundary by intent, which is the confound this design most needs to avoid. |

Object storage's danger is the opposite one — the contract can look trivial, `put` and `get` — and
that danger is answerable. What an external client actually needs is not the two verbs but the
**failure and lifetime semantics**: what happens when a key is absent, whether overwrite is safe,
whether a read immediately after a write is guaranteed to see it, what a size or content-type
violation does. Those are exactly the facts a caller cannot invent, and exactly the facts an
implementation would otherwise have to be read to discover.

## 5. The hidden decision and the external task

**Hidden decision:** how objects are actually stored and addressed — the SDK or filesystem calls,
the retry and backoff behaviour, multipart or chunking, checksum handling, key derivation.
Realistically volatile, semantically meaningful, and irrelevant to a caller.

**Task-selection rule, fixed before any fixture exists.** A task is admissible as *external* only if
it (a) changes application behaviour visible to a product user, (b) uses the storage boundary through
its existing contract, (c) requires no change to that contract, and (d) can be judged correct by
tests that never reference `M`'s internals. A task failing any clause is not external.

**Primary external task (illustrative shape, to be fixed in MLR-C1):** add an application feature
that stores a generated artefact and serves it back, handling the absent-object case in a
product-visible way. The caller needs: how to store, how to retrieve, what absence looks like, and
whether repeated stores are safe. The caller does not need: the SDK, the retry loop, or chunking.

## 6. The boundary-crossing control — included in V1

A second task whose conceptual responsibility is **inside** `M`: change the storage retry behaviour.

This is the control that stops the experiment from concluding *less context is always better*. Under
it, `FULL` should plausibly succeed and `CONTRACT` should either fail or visibly report that the
contract does not contain what the task needs. If `CONTRACT` succeeds at an internal task without
internals, the task was mislabelled and the design has a defect.

It is included rather than deferred because it is cheap — the same fixture, one more task — and
because without it a positive result on the external task cannot be distinguished from a general
context-reduction effect.

## 7. Contract sufficiency, and the leakage audit

The treatment cannot merely delete code; then a failure would only mean *information was removed*.
`CONTRACT` substitutes the implementation with enough external knowledge that a competent engineer
could do the task. Candidate contents, each admitted only by the Field Test — *what does an external
client actually need to reason correctly?*:

callable surface and types; what each operation does in product terms; the failure it raises when an
object is absent; whether writes are safe to repeat; read-after-write visibility; ownership and
lifetime of stored objects; any externally relevant accepted invariant.

Deliberately excluded: SDK names, retry counts, backoff shapes, chunk sizes, checksum algorithms,
internal helper structure, error types that never escape, and performance characteristics of the
implementation.

**Two audits before any model call.** *Sufficiency:* can a competent engineer perform each external
task using only this contract? If not, `CONTRACT` is invalid and must be fixed before measurement,
never after seeing a model fail. *Leakage:* does the contract contain internal detail a client
should not need? If so, remove it — a contract that reproduces the implementation defeats the
hypothesis and is detected numerically by the measurand in §10.

**And the contract must not encode the answer.** *"When an object is missing, `get` raises
`NotFound`"* is module semantics. *"When the object is missing, return HTTP 404"* is the task's
solution. The first belongs in the contract; the second never does. Nor may the contract contain
any of *"this module is well encapsulated"*, *"you should not need the implementation"*, or *"the
boundary owns X"* — those teach the hypothesis.

## 8. Arms

**`FULL`** — ordinary repository access, `M`'s implementation source present and readable.

**`CONTRACT`** — identical in every respect except that `M`'s implementation source is not present in
the repository the agent explores; the contract document is. No instruction differs. Neither arm is
told anything about boundaries, and `CONTRACT` is never told it should not need internals.

## 9. Isolation mechanism — tested, not assumed

The requirement is that **the same bytes execute in both arms** and only inspectability differs;
otherwise context and runtime both change and no result is attributable.

Two mechanisms were examined concretely.

**Sourceless bytecode — rejected.** Compiling `M` to a bytecode-only module does hide the source and
does import correctly. It also pins the fixture to one interpreter: a module compiled by 3.14 fails
to import under 3.10 with a bad-magic-number error, verified directly. Proofbound's deterministic
suite runs on both interpreters, so a fixture that can only be exercised by one is a defect, not a
mechanism.

**Out-of-tree dependency — selected.** `M` is installed outside the project tree and imported from
there in **both** arms, exactly as a third-party library would be. The `FULL` fixture additionally
carries a readable, byte-identical copy of `M`'s source inside the project; the `CONTRACT` fixture
carries the contract document instead. Runtime resolution is identical in both arms because both
import the same out-of-tree module, and a deterministic test pins the in-tree copy byte-identical to
the installed one so the two cannot drift.

An agent could in principle reach outside the project tree with an absolute path. That is not a leak
to be prevented but **evidence to record** — see §12.

## 10. The primary measurand

One, and chosen so that the traps in §16 cannot be passed off as success:

> **The size of the representation of `M` that correct reasoning required.**

In `FULL` that is the bytes of `M`'s implementation the agent actually read. In `CONTRACT` it is the
bytes of contract supplied. It is only defined for runs that **completed the task correctly** —
correctness is a gate on the measurand, never a term traded against it.

This formulation does the work three separate metrics would do badly. If the contract must reproduce
the implementation to succeed, the measurand shows no reduction and the hypothesis fails on its own
terms. If `FULL` never reads `M` at all, the measurand shows there was nothing to reduce and the
experiment reports no effect rather than a benefit. And it is the canonical craft definition's own
quantity — repository discovery context — measured at fixed conceptual size, because both arms
receive the identical task.

## 11. Correctness oracle

Deterministic first: hidden tests that exercise the product behaviour the task adds, plus the
pre-existing suite to catch regressions, plus the boundary tests. No semantic grader is the primary
oracle — the modularity hypothesis must not rest on another unstable architecture judge. Bounded
human review only for whatever tests genuinely cannot express, recorded as such.

## 12. Observables

The smallest set that answers the question:

1. correctness (gate);
2. bytes of `M`'s implementation read (`FULL`) and contract bytes supplied (`CONTRACT`) — the measurand;
3. files opened, and how many were `M`'s;
4. total context or input tokens;
5. tool and search calls;
6. wall time and cost.

Plus **treatment-compliance evidence**: attempts to read the absent implementation, requests for
unavailable detail, out-of-tree access attempts, and abandonment for missing information. A single
probe followed by correct work is evidence of contract sufficiency, not of failure, and is not scored
as one.

**Supplied context and discovered context are separated.** The harness supplies some; the agent
retrieves the rest; only some enters model calls. The canonical definition speaks about *discovery*,
so a `FULL` run that never opens `M` is itself a finding, and prompt length alone is not the answer.

## 13. Experimental unit, pairing, ordering

`fixture instance × task × arm × fresh execution`. The same task and instance run under both arms —
pairing controls task and fixture variance, and pairing is not independence. Arm order is generated
before execution and interleaved, so provider drift over a long run cannot align with an arm.

**Sample budget** is set in MLR-C3's own pre-registration, not here, and derives from measured
variance in MLR-C2 rather than from a convention. Two tasks × two arms × N; no adaptive extension.

## 14. Validity gates, before any model call

| Gate | Question |
|---|---|
| **Entailment** | Does the fixture's accepted intent actually establish the contract and semantics clients rely on? |
| **Exercise** | Does the external task genuinely use the boundary? |
| **Discrimination** | Do the arms differ *only* in inspectability of `M`, with identical runtime bytes? |
| **Contract sufficiency** | Could a competent engineer do the task from the contract alone? |
| **Responsibility validity** | Is the external task genuinely outside `M`'s responsibility, and the control task genuinely inside? |
| **Headroom** | Does `FULL` actually read `M`? If it never does, there is nothing to substitute. |

Headroom is the one gate measurement alone can settle, so MLR-C3 runs `FULL` first and inspects it
before the paired comparison is worth running — the same discipline the craft baseline used, and the
same reason.

## 15. Result shapes, pre-registered

**Substitution works** — correctness comparable, measurand materially smaller. **No effect** —
correctness comparable, measurand similar, because `FULL` barely read `M` or the contract is as large
as what was read. **Contract insufficient** — `CONTRACT` correctness drops, or hidden detail is
repeatedly needed. **Full context helps** — internals carried externally relevant knowledge the
contract omitted, which diagnoses a leaky boundary or an insufficient contract rather than condemning
the architecture. **Both fail** — task or fixture invalid. **High variance** — unresolved.

**Modularity must be able to lose, and the null is stated as the live alternative:** full
implementation access materially improves correctness even for nominally external tasks. If that is
what happens, it is the result.

## 16. The three tests this design must pass

*If `CONTRACT` uses far fewer tokens but produces worse changes* — the conclusion is **the contract
was insufficient or the boundary leaks**, never that modularity helped. Correctness gates the
measurand, so a cheaper wrong answer contributes nothing.

*If `FULL` and `CONTRACT` are equally correct but `FULL` never inspects `M`* — the measurand shows no
reduction was available, and the experiment reports **no effect**. Benefit is never claimed from arm
assignment.

*If `CONTRACT` is equally correct and cheaper only because the contract reproduces most of the
implementation's semantics* — the measurand compares contract size against implementation bytes read,
so this shows up as no reduction, and the leakage audit is designed to catch it before the run.

Only one shape earns the claim: **a substantially smaller representation of `M`'s externally relevant
semantics sufficed for correct reasoning outside `M`.**

## 17. What one fixture cannot show

This design uses **one boundary and two context arms**. It can establish that context substitution is
measurable and whether it holds here. It **cannot** attribute the effect to boundary quality — a
well-documented tangle might allow the same substitution, which is a real possibility and worth
knowing. Architecture-quality variation (entangled / meaningfully bounded / over-fragmented) is
therefore a later stage, not a missing piece of this one: adding it before the instrument is
validated would repeat the craft programme's mistake of measuring with an uncalibrated instrument.

**Alternative-good control** — a structurally different boundary providing equivalent hiding — is
pre-registered as MLR-C4 and must not be forgotten: the notification programme showed how easily one
sound realisation becomes a de facto reference architecture. **Over-modularisation** belongs in the
same stage, because *more modules is not the hypothesis and must be able to lose*. **Implementation
substitution** (two implementations behind one contract, external reasoning invariant) and the
**minimum-sufficient-contract ladder** (signature → behaviour → invariants → full) are stronger
follow-ups once substitution itself is established. **Holdout confirmation** in an uninspected second
domain is what any generality claim would require; nothing here claims generality.

## 18. Diagnosing a failure

If `CONTRACT` fails, two causes must not be conflated: the boundary leaks, or the contract
representation is insufficient. The diagnostic is available from `FULL`'s own evidence — what did
successful `FULL` runs read from `M`, were those facts legitimate external semantics, and did the
contract omit them? Facts that were legitimately external and omitted mean the contract was
incomplete; facts that were internal mechanics mean the boundary leaks and callers depended on
accidents. This may be the most valuable output of the whole programme.

## 19. Substrate

**Reused unchanged:** `run_trial`'s isolated fresh project per trial, evidence retention, the CE1
extraction that already reports files read and tool calls, `_experiment.py`'s manifest discipline
(claim, measurand, frozen variables, guardrails, falsifier, invalidating conditions, adoption rule),
preallocated slots, configuration-identity hashing, atomic checkpointing and non-splicing resume.

**The minimum delta**, stated honestly rather than pretending the closed-world substrate fits: its
arms append a treatment to a *reflector prompt*, whereas here an arm selects a *fixture variant* and
the work is an implementer trial rather than a reflection. So a new executor is needed that maps arm
to fixture and runs implementer trials into preallocated slots, plus retention of absolute-path reads
that `ce1_facts` currently discards as out-of-repository. Both are small and local. No change to
ledger, freeze, execution binding, review purposes, or any authority machinery.

## 20. Sequence

- **MLR-C1** — build the fixture: repository, boundary, out-of-tree module, both arm variants, both
  tasks, hidden tests. Pass the six validity gates deterministically. No semantic call.
- **MLR-C2** — validate measurement mechanics: identical runtime bytes across arms, context isolation
  real, telemetry captures reads and compliance, slots and resume behave.
- **MLR-C3** — `FULL`-only pilot for headroom, then the paired run under its own pre-registration.
- **MLR-C4** — alternative-good and over-fragmented architectures, only if C3 measured something.
- **MLR-C5** — holdout confirmation in an uninspected domain.

## 21. What a successful run would and would not support

**Would:** *under this task, domain, fixture and model configuration, external reasoning stayed
correct when the module's internals were replaced by a smaller sufficient contract, and the
representation of the module that correct reasoning required was materially smaller.*

**Would not:** that modular architecture is universally better; that agents always need less context
with modules; that modularity guarantees correctness; that all implementations should be hidden; that
microservices help; that context should be restricted in general; or that smaller context is better.
Development fixtures support no generality claim at all — that is what MLR-C5 exists for.
