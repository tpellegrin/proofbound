# Proofbound core model

> **Normative.** This document defines Proofbound's truth model, the three orthogonal dimensions of an
> artifact, the canonical principles `P1`–`P13`, and the authority ordering of evidence. Every other
> document references these definitions rather than restating them.
>
> Entry point: [README.md](README.md). Section numbers are inherited stable identifiers, not positions.

## 31. The truth model — four layers

Proofbound was using one word, "state", for four different things that fail in different ways and are
proved by different means. They are now named separately.

| Layer | Name | What it is | Lives in | Can prove | Cannot prove |
|---|---|---|---|---|---|
| L1 | **Intent** | What *should* be true: proposal, design, specification, accepted decisions, constraints, task definitions, future freeze | Project source, version-controlled | What was accepted as the goal | That anything implements it |
| L2 | **Repository reality** | What *is* true now: artifact bytes, implementation, dependency structure, configuration, tests | Working tree / Git | What the system currently is | That this is what was intended |
| L3 | **Execution evidence** | What *happened*: reservations, scope movement, gates, reports, verification output, reviewer role | Run tree, machine-local, deletable | That a bounded reviewed process occurred | What is true now, or what should be |
| L4 | **Durable provenance** | Which *relationships* were established: accepted artifact identity, dependency identity, declared review purpose, gate reference | Project source (the ledger) | That L2 content matches what L3 accepted, and what it depended on | That the review was good; that it happened, once L3 is gone |

L4 is the load-bearing invention. It is deliberately not a summary of L3 — it is the minimum needed to
connect L1, L2 and L3 without duplicating execution history. That is why the field test for a ledger
field is *which invariant becomes impossible without it*, and why timestamps, attempt identifiers and
model identity all failed that test ([artifacts-and-provenance.md](artifacts-and-provenance.md#a1-the-durable-change-ledger-v1)).

Two consequences worth stating explicitly:

- **L3 is expendable by design.** Deleting a run tree must lose provenance verification and nothing else.
  If losing L3 changed an artifact's validity, the ledger would not be durable.
- **L4 cannot replace L3.** Anything L4 asserts about L3 is a *reference*, checkable only while L3 exists.
  This is the honest limit, and `unavailable` is how it is reported.

## 32. Three independent dimensions

M2A exposed a conflation that would have propagated into every later milestone. An artifact has three
dimensions, and they are orthogonal.

**Structural validity** — `valid` / `invalid` / `needs-revalidation`. Derived from current content
identity, accepted content identity, and dependency closure. Computable from L2 + L4 alone.

**Provenance status** — `verified` / `unavailable` / `contradicted`. Derived from whether L3 is retained
and consistent with L4. Says nothing about whether the artifact is currently correct.

**Semantic correctness** — no enum, no field, no Python value. It is the judgment an accepted independent
review established at a point in time. Proofbound records *that a qualifying review occurred for a
declared purpose*; it never records a verdict, because there is no verdict field anywhere in the system
and adding one would recreate the PASS/FAIL machinery DSD deliberately deleted.

The combinations that legitimately occur:

| Structural | Provenance | Meaning |
|---|---|---|
| valid | verified | The normal healthy case: content matches, evidence retained and consistent. |
| valid | unavailable | **The expected steady state of an old repository.** Content still matches what was accepted; the run tree is long gone. Not a defect, and must never be reported as one. |
| valid | contradicted | Content matches, but retained evidence disagrees with the record — tampering, corruption, or a bug. Serious: the record's own provenance claim is false even though the artifact is intact. |
| invalid | verified | Someone edited an accepted artifact after acceptance. The review genuinely happened; the artifact is no longer the thing that was reviewed. |
| invalid | unavailable | Content drifted and the evidence is gone. Requires re-authoring and re-review; nothing can be recovered by inspection. |
| needs-revalidation | verified | The artifact is intact and its own review is sound, but ground it depended on moved. Re-review, not re-authoring. |

The trap this prevents: reading `valid` as "correct", or `verified` as "good". A structurally valid,
provenance-verified artifact can be terrible engineering. Proofbound has never claimed otherwise, and no
future milestone may introduce a value that implies it.


## 33. Consolidated principles

**On numbering.** `I<n>` had come to mean four different things: [§3](execution-and-review.md#3-existing-invariants-that-must-be-preserved)'s inherited DSD invariants, the
implementation plan's list, [§26](evidence/implementation-findings.md#26-m2-design-check)'s design-check list, and M2A's task list. `I4` variously meant "fresh
independent review", "same contract, multiple attempts", and "artifact state is derived". That is a rule
graveyard, and it is exactly the retrieval failure [§28](context-economy.md#28-context-economy-and-refactoring-economics) warns about.

From here: **`I1`–`I15` in [§3](execution-and-review.md#3-existing-invariants-that-must-be-preserved) are the inherited DSD mechanical invariants and keep their meaning
unchanged.** Proofbound's own principles are `P1`–`P13` below, and this table is their single canonical
statement. Other sections cite `P<n>`; they do not restate it.

Thirteen, consolidated from seventeen candidates — because a principle set that grows monotonically
stops being read, which is the failure it is supposed to prevent.

| # | Principle | Why it exists | Falsified if… |
|---|---|---|---|
| **P1** | **The semantic boundary.** Python proves objective facts. Humans and agents judge engineering quality. Mechanical signals inform semantic review; they never replace, pre-empt or summarize it. | The whole harness. Absorbs "deterministic facts are mechanically enforced" and "mechanical signals inform rather than replace" — they are one boundary seen from both sides. | Any code path assigns PASS/FAIL, parses worker prose for meaning, or converts a threshold into a verdict. |
| **P2** | **Purpose ≠ capability ≠ role.** Why a review existed, whether a role *can* review, and which doctrine ran are three separate facts. | M1 found roles interchangeable at acceptance; M2A found purposes that share a role. | Two purposes are merged because their mechanics coincide, or a purpose is inferred from a role, path or prose. |
| **P3** | **Artifact state is derived.** Validity is computed from content identity and dependency closure; no mutable state enum is authoritative. | A stored state becomes a second truth that silently disagrees with the content. | Any persisted field records `valid`/`invalid`/`needs-revalidation`, or validation trusts a stored state over recomputation. |
| **P4** | **Durable provenance and execution evidence are separate trust layers** (§31). Losing execution evidence must cost provenance verification and nothing else. | The run tree is large, machine-local and deletable; the record must outlive it. | Deleting a run tree changes an artifact's structural validity, or absent evidence is reported as verified or as invalid. |
| **P5** | **Hashes establish integrity, not authority.** A committed digest proves content did not drift. It proves nothing about who wrote it or whether a review occurred. | Proofbound has no signing keys and no trust roots. | Any document or message describes a SHA-256 as authentication, signature, or proof of authorship. |
| **P6** | **Historical formats are verified under the semantics they recorded**, never reinterpreted under the current registry. Every input to an identity is recorded from v1. | M0: an order-dependent fingerprint whose order was never recorded. | A format is verified using present-day defaults for something it did not record, or old evidence is regenerated to make it pass. |
| **P7** | **Local adaptation is not global policy** ([§35](long-running-autonomy.md#35-local-adaptation-escalation-and-promotion)). A bounded task may solve its problem within its authority; it may not silently establish, broaden or replace a cross-cutting rule. | The primary defense against cumulative drift. | A bounded worker establishes a repository-wide rule with no escalation and no decision record, and later workers treat it as authoritative. |
| **P8** | **Architectural decisions carry explicit, bounded provenance** ([§36](long-running-autonomy.md#36-decision-provenance-direction-deferred)). A decision states its scope, not only its conclusion. | Conclusions generalize; boundaries do not travel with them unless recorded. | A future worker cannot determine the scope under which an accepted policy was adopted. |
| **P9** | **Accepted baselines change by supersession, never by mutation** ([§37](long-running-autonomy.md#37-baseline-erosion-and-drift)). | If the ruler moves with the thing it measures, drift becomes unmeasurable. | Current accepted intent can be edited in place without producing a new accepted identity, or history is rewritten to match the present. |
| **P10** | **Local correctness does not imply global coherence** ([§38](long-running-autonomy.md#38-cumulative-coherence)). Per-task independent review is necessary and insufficient. | 100 individually valid changes can compose into an incoherent system. | The architecture treats "every task passed" as equivalent to "the system is sound". |
| **P11** | **Repository patterns are evidence, not authority** (§34). Existing code shows what was done, not what is required. | Agents imitate the repository strongly; debt is as imitable as design. | A worker adopts a convention solely because it is frequent, against authoritative guidance, without surfacing the conflict. |
| **P12** | **Fresh independent evaluation at semantic boundaries**, and evaluators do not inherit the execution context that produced what they judge. | M1's independence rule, generalized: an evaluator carrying the reasoning that produced a change cannot independently assess it. | A drift or coherence evaluator is handed the execution narrative of the work it evaluates, or the parent substitutes its own accumulated judgment for a required reflection. |
| **P13** | **Context is an economic resource, on two surfaces** ([§28.2](context-economy.md#282-two-context-surfaces)): harness context, which Proofbound supplies, and repository discovery context, which architecture quality determines. Refactoring value is assessed through cost-of-change evidence, never through a size metric alone. | The Fowler result: total code barely moved while the readable surface collapsed. | A size threshold is treated as an architectural verdict, or a durable record is inflated with telemetry that has no invariant depending on it. |


## 34. Authority, and how knowledge acquires it

### 34.1 The evidence hierarchy

Agents resolve conflicts by whichever source is nearest, most numerous, or easiest. Proofbound needs an
explicit ordering so that resolution is a decision rather than an accident.

| Class | Source | Authority |
|---|---|---|
| **A1** | Accepted engineering contract for the change — proposal/design/spec/tasks, eventually the freeze | Normative. What must be true. |
| **A2** | Accepted architectural decisions applicable to this scope | Normative constraints on *how*. |
| **A3** | Mechanically enforced invariants ([§37.4](long-running-autonomy.md#374-executable-invariants--accepted-decisions-made-operative)) | Operative. The executable projection of A1/A2 and of inherited DSD mechanics. |
| **A4** | The current task contract | Bounded authority for this unit of work. |
| **A5** | Approved repository guidance — `AGENTS.md`, role protocols, `CONTRIBUTING.md` | Standing convention. |
| **A6** | Repository implementation patterns | **Evidence only.** What was done. |
| **A7** | Historical execution artifacts — old reports, logs, superseded decisions | Evidence about the past only. |
| **A8** | Worker inference and assumption | Lowest. Must be surfaced, never silently promoted. |

Three placements deserve defence, because the obvious ordering is wrong.

**A4 below A2, deliberately.** A task contract is more specific and more immediate than an architectural
decision, which tempts an ordering that puts it higher. But a contract that can only be satisfied by
violating an accepted decision is either an authoring error or an unrecorded architectural change — which
is precisely P7's failure mode. The two rarely compete in practice because they govern different axes:
**the contract governs scope, accepted decisions govern constraints.** When they genuinely conflict, that
conflict *is* the escalation trigger ([§35.2](long-running-autonomy.md#352-escalation-reuses-decisionrequired)), not a ranking problem to be resolved silently.

**A3 below A2, though A3 is what actually blocks.** An invariant is a mechanical projection of a decision
and cannot outrank its source. If an invariant disagrees with the decision it encodes, the invariant is
stale or buggy — it is not a new policy. (Inherited DSD invariants `I1`–`I15` have no Proofbound decision
behind them; they are accepted architecture by inheritance, and sit at A2/A3 jointly.)

**A6 above A7 but both far below A5.** Current code is better evidence than an old log, and neither is
authority. This is the ordering that stops "the code already does X" from defeating "accepted
architecture requires Y".

**The conflict rule: surface, do not choose.** When a worker finds sources in genuine conflict, the
correct action is to report the conflict — with both sources cited — not to pick the more convenient one
and proceed. Silent resolution is how an unrecorded policy is born.

### 34.2 The knowledge lifecycle

Authority is acquired, not inherent. A fact moves up this ladder only through an explicit step:

```
observation  ->  evidence  ->  proposal  ->  accepted decision  ->  enforced invariant
                                                                    or standing guidance
                                                                          |
                                                                          v
                                                                  superseded decision
```

Each level is a different kind of thing, not a stronger version of the same thing. An observation that a
timeout occurred is not evidence that timeouts are systemic; evidence of that is not a proposal; a
proposal is not accepted; and an accepted decision is not automatically mechanically enforced.

A **superseded** decision does not vanish — it remains visible as history (P9) and keeps its value as
rationale — but it loses authority entirely. It drops from A2 to A7. This is the distinction that lets
Proofbound retire obsolete rules without erasing why they existed.


### 40.2 Falsification

Each principle in §33 carries its own falsifier in the table; they are not restated here. Three
system-level claims need more than a line, and are the ones to watch:

1. **"Escalation is possible without being universal."** Falsified if, in practice, either almost no
   `DECISION_REQUIRED` escalations occur on architecturally significant changes (the boundary is not
   recognizable to workers) *or* they occur on routine changes at a rate that degrades throughput. Both
   directions are observable; neither is currently observed, because neither is instrumented.
2. **"Coherence review is a distinct capability."** Falsified if the audit, once built, produces findings
   indistinguishable from per-task code review — i.e. it cannot use the baseline-plus-decisions comparison
   and falls back to reading diffs.
3. **"Scope makes decisions safe to leave lying around."** Falsified if workers routinely need decisions
   whose scope is not path-shaped, making mechanical applicability selection useless and returning the
   system to "read all decisions", which recreates T8.
