# Long-running autonomy

> **Normative, with rationale.** Why a harness that is correct on every individual task can still degrade
> across a long autonomous run, and what bounds it: the promotion ladder, escalation, decision provenance,
> baseline supersession, erosion versus drift, cumulative coherence, and the threat model `T1`–`T10`.
>
> The principles this document applies (`P7`–`P12`) are defined once in
> [core-model.md](core-model.md). Entry point: [README.md](README.md).

### 40.1 What Part II does not add

No production behavior changes. Nothing here adds a decision record, ledger field, review purpose, drift
detector, architecture classifier, telemetry, freeze, graph, role, or gate. §36's field analysis fixes a
shape; it does not authorize an implementation.


## 35. Local adaptation, escalation, and promotion

### 35.1 The promotion ladder

The single most consequential confusion in a long autonomous run is treating these five as
interchangeable. They are not, and movement between them requires explicit authority.

```
incident / observation
   ->  bounded local response        (within existing authority; needs no decision)
   ->  candidate reusable pattern    (noticed, not yet authoritative)
   ->  explicit engineering decision (proposed, independently reflected, accepted)
   ->  accepted policy / invariant   (constrains future work; may become mechanical)
```

**Nothing is promoted by repetition, age, or presence in the repository.** Code existing is not evidence
that it should exist; three instances of a workaround are three instances of a workaround. This is P7 and
P11 stated as a process rather than as a prohibition.

The concrete failure it prevents: a task hits a provider timeout, adds a retry, and ships. Two milestones
later a worker reads the codebase, infers "this project retries network calls", and adds retries to a
non-idempotent payment submission. No one decided that. No review rejected it. Every individual change
was locally reasonable and independently reviewed.

### 35.2 Escalation reuses `DECISION_REQUIRED`

DSD already has the right control-flow primitive, and Proofbound must not invent a second one.

`worker/COMMON.md` line 22: a worker facing *"a consequential authority/product/safety decision you cannot
legitimately make"* keeps evidence current and returns a bounded `DECISION_REQUIRED` carrying the
question, consequences, recommendation, and evidence pointers. `dsd_attempt.py --resume-session` then
continues *the same session* once the parent decides.

Three properties make it correct for architectural escalation, unchanged:

- **It is prose, consumed by the parent.** No Python parses it (`COMMON.md` line 20 is explicit that
  report formatting is not a machine protocol). Escalation therefore cannot become a classifier — P1 holds
  for free.
- **It is bounded.** The worker states the question, not a policy.
- **It is cheap.** Same-session resume means escalation costs a round-trip, not a restart. This is the
  main reason escalation can be required without destroying throughput (§35.4).

So there is **no `ARCHITECTURE_ESCALATION_REQUIRED`**. What Proofbound adds later is not a second signal
but a durable representation of the *outcome*:

| Concern | Mechanism | Status |
|---|---|---|
| Runtime escalation | `DECISION_REQUIRED` + `--resume-session` | **Inherited, exists** |
| Durable accepted decision | Decision provenance (§36) | Deferred |

### 35.3 Significance is decided semantically

Proofbound must not classify diffs. There will be no architecture classifier, because "does this change
architectural policy" is a semantic question and P1 forbids Python answering it.

The control flow instead:

```
worker recognizes a broader implication
   ->  DECISION_REQUIRED
   ->  parent evaluates significance
   ->  decision proposal, if warranted
   ->  independent reflection
   ->  accepted, scoped decision
   ->  implementation resumes (same session)
```

Mechanical signals may *surface candidates* for the parent's attention — changes touching cross-cutting
configuration, dependency policy, retry/backoff defaults, global logging, authn/authz, persistence
strategy, caching, concurrency, public APIs, dependency-direction rules, shared middleware, or
framework/tooling policy. These are prompts to look, never findings. A change touching none of them can
still be architecturally significant, and a change touching several can be entirely routine.

### 35.4 Why this does not become bureaucracy

Adversarially: an architecture that routes every `if` statement through a decision record would be worse
than no architecture, because it would be abandoned.

The defenses are structural, not exhortative:

1. **The default is to execute.** Escalation is the exception, triggered by the worker recognizing a
   boundary or the parent noticing a signal. Silence is the normal path.
2. **The worker decides only whether to *ask*.** It never authors policy, which is a much lower bar than
   asking it to assess architectural significance.
3. **Escalation is a round-trip, not a restart** (§35.2). This is what makes the cost bearable.
4. **The parent decides whether a decision artifact is warranted.** Most escalations should end in a
   direct answer, not a decision record. A decision record is for the case where the answer will
   constrain *future* work.
5. **Scope is bounded by default** (§36). A decision that applies to one client is cheap to accept and
   cheap to ignore elsewhere.

The design target: architectural escalation is **possible and enforceable without being universal**.

### 35.5 Worked example — a network timeout

**Incident.** An implementation task integrating payment provider X hits a 30-second timeout on a status
query. The task's acceptance criteria cannot be met.

**The branch that matters** is not "should we retry" but *"does responding require establishing a rule
beyond this task?"*

```
timeout observed
      |
      v
is a bounded response within existing accepted authority?
      |                                        |
     yes                                       no
      |                                        |
      v                                        v
retry this idempotent status query      DECISION_REQUIRED:
per an existing accepted decision       "Provider X status queries time out under load.
that already covers this client          A retry policy is needed. I can retry this call,
      |                                  but I cannot determine whether this project
      v                                  wants retry behavior for provider clients
continue; no decision record             generally. Consequences / recommendation /
                                         evidence: <attempt, log, scope>."
                                                      |
                                                      v
                                        parent evaluates significance
                                                      |
                                                      v
                                        decision proposal authored, independently
                                        reflected, accepted:

                                          Trigger:   repeated 30s timeouts on X status
                                                     queries under load  <evidence ref>
                                          Decision:  bounded exponential backoff, max 3
                                                     attempts, idempotent requests only
                                          Scope:     the provider-X client
                                          Rationale: X publishes no SLA for this endpoint;
                                                     the query is idempotent by contract
                                          Alternatives: raise timeout (rejected: hides
                                                     load); circuit breaker (deferred:
                                                     no evidence of sustained failure)
                                                      |
                                                      v
                                        implementation resumes, same session
```

**The part that pays for the ceremony** is what a *future* worker does. Six months later, a task
integrates provider Y, hits a timeout, and reads the codebase. It finds a retry helper in the X client.

- Under **P11**, that helper is A6 evidence — what was done — not authority.
- Under **P8**, the accepted decision carries `scope: provider-X client`. The worker can determine that
  the accepted policy does not extend to Y.
- Under **P7**, adopting retries for Y is therefore a *new* bounded response, and if it would establish a
  general rule it is a new `DECISION_REQUIRED` — not an inference from existing code.
- Under **None[§28.4](context-economy.md#284-a-future-capability-in-two-modes)/None[§34](core-model.md#34-authority-and-how-knowledge-acquires-it)**, the worker was given the X decision only because its scope intersected the task's
  scope. It was not handed every decision the project ever made.

Without the recorded scope, the honest reading of the repository is "this project retries provider
calls", and the generalization happens silently and reasonably. **The scope, not the conclusion, is what
makes the decision safe to leave lying around.**


## 36. Decision provenance (direction; deferred)

Not designed here in implementable detail and explicitly not in M2B. What follows fixes the *shape*, so
that M2B's graph does not foreclose it.

### 36.1 The field test, applied

M2A's field test — *which invariant becomes impossible or materially harder without this field?* — is
applied to ADR practice rather than adopting ADR templates wholesale.

| Candidate | Verdict |
|---|---|
| **decision** | **Keep.** The conclusion. |
| **scope** / `applies_to` | **Keep — the load-bearing field.** Without it P8 fails outright: a later worker cannot determine whether an accepted policy governs its task. It is also what makes progressive disclosure possible (None[§36.3](artifacts-and-provenance.md#363-applicability-is-not-a-dependency-edge)). |
| **trigger** | **Keep, as a compact reference.** Not an incident narrative. The invariant that depends on it is *retirement*: "is the condition that justified this still true?" is unanswerable without it (§36.4). |
| **rationale** | **Keep.** Perry & Wolf treat rationale as a first-class component of architecture, not commentary. The dependent invariant is supersession review: without rationale a later reviewer can check whether a decision is being *followed*, but not whether it should still *stand*. |
| **consequences** | **Drop as a field.** Real content, but it is rationale prose, not a separately checkable fact. |
| **alternatives considered** | **Drop as a field.** Same: valuable, and it belongs inside rationale. Nothing checks it. |
| **review purpose / role / gate** | **Drop — already provided.** A decision record should *be* a ledger artifact (§36.2), so its review provenance comes from its ledger entry. Duplicating it would create a second, divergable copy. |
| **status: accepted / superseded** | **Drop as a stored status** (P3). Derived: a decision is in force iff nothing supersedes it. |
| **supersedes** | **Keep — and note the reversal.** M2A *rejected* `supersedes` for artifacts because Git already supplies a version chain. For decisions the field test comes out the other way: D-007 replacing D-003 is not a new version of one artifact, it is one artifact retiring another, and Git's history of `D-003` cannot express it. Recording it on the *new* decision keeps the old one untouched and append-only (P9). |
| **expires_at** | **Reject.** Elapsed time almost never determines architectural validity; a date would license either premature removal or false confidence. |

The survivors: **decision, scope, trigger, rationale, and optionally supersedes** — plus everything the
ledger already records about how it was accepted. The same discipline that reduced the artifact record to
four keys applies here, and produced a different answer for one field. That is the test working, not a
template being copied.

### 36.2 A decision is an artifact

The strong default is that decision records are ordinary Proofbound artifacts: content-addressed, with
dependencies, accepted through the same mutation → independent reflection → acceptance path, and recorded
in the same ledger. No parallel store, no second acceptance engine (P1, and the M2A prohibition).

This matters for M2B: **the artifact graph must stay generic enough to carry them.** M2A's `depends_on` is
already a plain path→identity map with no kind semantics baked in, which is the right shape.


### 36.4 Retirement

Architecture accumulates obsolete defensive rules even when every rule was justified when adopted. A
decision system that can only add is a scar-tissue generator with better formatting.

Retirement must be explicit and immutable: a new decision supersedes the old, the old remains readable as
history, and its authority drops from A2 to A7 (None[§34.2](core-model.md#342-the-knowledge-lifecycle)). The old record is never edited — editing an
accepted artifact makes it structurally invalid until re-accepted, which is exactly the right pressure.

`review_when: <condition>` — "revisit when provider X ships feature Y" — is attractive and introduces
condition semantics Proofbound cannot mechanically evaluate. **Unresolved; deferred.** The captured
requirement is narrower and firmer: *Proofbound must eventually make it possible to retire an obsolete
architectural adaptation explicitly, rather than letting it become permanent by default.* The trigger
reference is what makes that possible, which is why it survived the field test.

### 36.5 Does decision review need its own purpose?

Open, and deliberately not answered here. **No change is made to the five-value registry in this pass.**

The argument for a distinct `architecture-decision-reflection`: the review question genuinely differs. A
design reflection asks whether an approach is sound. A decision reflection must primarily ask *whether
the scope is correctly bounded* — over-generalization is the failure mode P7 exists to prevent, and it is
not what `design-reflection` is aimed at.

The argument against: the mechanics would be identical (`spec-reflector`), and purpose-vocabulary
inflation has its own cost.

None[§27.1](execution-and-review.md#271-decision-resolved--the-review-purpose-vocabulary-is-fine-grained) already settled the tie-breaking rule — purposes with identical mechanics stay distinct when their
engineering meaning differs — which leans toward adding one. **Recorded for the milestone that implements
decision provenance, not for M2B.**


## 37. Baseline, erosion, and drift

### 37.1 Baselines evolve by supersession

Both extremes are wrong. A continuously mutable baseline cannot measure anything. An immutable-forever
baseline guarantees that a correct system is eventually judged non-conforming.

```
accepted baseline F1
      ->  new evidence or requirement
      ->  proposal  ->  independent reflection  ->  accepted
      ->  accepted baseline F2
```

F1 remains immutable historical truth; F2 becomes authoritative. This is P9, and it is the same
content-addressed, append-only shape as M2A's ledger — supersession is a new accepted identity, never an
edit to an accepted one.

> **The critical invariant:** the ruler used to measure drift may change only through an explicit accepted
> engineering decision.

Without it, the baseline drifts alongside the implementation and drift measurement becomes a tautology —
the system silently redefines conformance to mean whatever it currently does (T5).

### 37.2 Erosion and drift are different failures

Perry & Wolf's 1992 distinction is precise and Proofbound should not blur it: **erosion** results from
*violating* architectural principles; **drift** results from *insensitivity* to the architecture.

The consequence is sharp and load-bearing:

| | Erosion | Drift |
|---|---|---|
| What happened | A change contradicts accepted architecture | Changes were made without reference to it |
| Shape | A violation — something present that should not be | An absence — no relation to the architecture at all |
| Detectable mechanically? | **Partly.** A violated invariant is checkable; a contradicted decision is sometimes checkable | **No.** You cannot detect the absence of reference by checking for violations |
| Primary defense | Executable invariants (§37.4), accepted decisions | Cumulative coherence review (§38) — semantic, unavoidably |

This is why mechanical invariants, however good, cannot be the whole answer. They detect erosion.
Drift produces a repository where every rule passes and nothing coheres — the T9 case.

### 37.3 What counts as a drift finding

Drift is **not** "differs from older code". Architecture must evolve, and a system forbidden to differ
from its past is not an architecture but a museum.

The objective comparison is:

```
accepted baseline  +  accepted subsequent decisions        (what is authorized)
                        versus
current repository reality                                  (what exists)
```

A difference is a **candidate finding** when repository behavior or structure cannot be reconciled with
accepted intent plus the decisions that authorize divergence from it. Authorized divergence is not drift;
that is the entire purpose of recording decisions.

Mechanical tooling may surface differences. Whether a difference is justified evolution or erosion is
semantic (P1), and is decided by a fresh evaluator (P12).

### 37.4 Executable invariants — accepted decisions, made operative

When an accepted decision can be expressed mechanically, enforcing it beats asking every future agent to
remember it. Repeated semantic recollection is the weakest possible enforcement: it degrades with context
pressure, it is invisible when it fails, and it competes with everything else in the prompt.

```
accepted decision
      |
   mechanically expressible?
      |            |
     yes           no
      |            |
      v            v
  invariant   semantic guidance
      |
      v
  CI / integrity gate
```

Candidates: forbidden dependency directions, module boundaries, layering constraints, required API
shapes, schema constraints, generated-file boundaries, import restrictions, security requirements.

Two constraints:

- **Not every rule can or should become lint.** Forcing a semantic constraint into a mechanical check
  produces a rule that is either trivially satisfiable or constantly wrong, and teaches agents to work
  around it. "No rule left unmechanized" is not the goal.
- **An invariant must reference the decision it projects.** An unattributed mechanical rule is a
  cross-cutting policy with no provenance — exactly T2, arriving through the tooling instead of the code.
  It also cannot be retired, because nothing records what it was for.

This is also the answer to "why not just add a linter": a linter without decision provenance is
unfalsifiable policy, and Proofbound's whole thesis is that policy needs attribution.


## 38. Cumulative coherence

### 38.1 Two mechanisms, not one

Long-horizon failure is routinely explained as context-window overflow. That is at most half of it, and
treating it as the whole story produces defenses that cannot work.

**Context degradation.** Original rationale becomes unavailable, compressed, stale, or hard to retrieve.
The system still *could* be coherent; it has lost the information needed to stay so.

**Decision compounding.** Each local decision changes the environment in which the next is made. A
retry helper becomes the pattern; the pattern becomes the assumption; the assumption shapes the next
design. Every step is locally rational and independently reviewed.

The distinction matters because **perfect memory would not prevent compounding.** An agent with total
recall of every prior decision still faces a repository whose accumulated shape makes the next locally
reasonable change slightly worse than the last. Context defenses do not address this; only comparison
against a fixed external standard does.

| Mechanism | Defenses |
|---|---|
| Context degradation | Durable artifacts (L4); bounded worker context (`I7`); explicit accepted decisions; progressive disclosure (None[§36.3](artifacts-and-provenance.md#363-applicability-is-not-a-dependency-edge)); fresh reviewers (P12) |
| Decision compounding | Immutable baselines (P9); decision provenance with scope (P8); escalation before policy (P7); cumulative coherence review (§38.2); executable invariants (§37.4) |

Note that most of the first column already exists and most of the second does not. That is the honest
current position, and §39 states it as residual risk rather than as coverage.

### 38.2 The cumulative coherence audit

Per-task independent review is necessary and insufficient (P10). A sequence of individually valid changes
can compose into an incoherent system, and no amount of reviewing the latest change detects it, because
the latest change is fine.

The audit's question is therefore different in kind:

> Does the current repository remain coherent with the accepted architectural baseline plus the
> explicitly accepted decisions that authorize divergence from it?

Not "was the last task done correctly". That has already been answered, by a review that was competent to
answer it.

**Inputs** — the accepted/frozen baseline; accepted subsequent decision provenance; relevant current
repository structure; a cumulative structural summary; mechanical invariant results; relevant
specifications.

**Deliberately not inputs** — worker transcripts, failed tool calls, accumulated execution reasoning,
historical noise. This is not only context economy. An evaluator that inherits the reasoning which
produced the drift will find that reasoning persuasive, because it was persuasive; each step really was
locally justified. **Fresh context is an independence property, not just a budget** (P12). It is the M1
independence rule generalized from one task to a whole run.

The honest caveat: **fresh context alone does not eliminate long-horizon drift.** It removes contamination
from the evaluator. It does nothing about a baseline that was wrong, a scope that was recorded too
broadly, or drift that is genuinely ambiguous. It is a necessary condition, not a solution.

### 38.3 When audits happen

Not on wall-clock intervals. "Every 300 hours" is unmeasurable in any way that matters — agent lifetime is
not the unit of architectural change, and a run that does nothing for 300 hours needs no audit while one
that lands forty changes in an afternoon does.

Prefer **event and contract boundaries**: before creating a new freeze; after a phase closes; after N
accepted changes; when the accepted-decision count crosses a threshold; when mechanical invariants report
new violations; before release; on explicit request.

Final trigger policy is deliberately unresolved — it should be chosen when there is evidence about which
boundaries actually correlate with incoherence, not now.

### 38.4 Final audit is two audits

The eventual final audit must not collapse into "all tasks passed".

| Audit | Question | Evidence |
|---|---|---|
| **Completion** | Did every bounded task satisfy its evidence requirements? | Per-task gates and acceptances |
| **Coherence** | Does the resulting repository conform to the accepted engineering contract and applicable decisions? | Baseline + decisions versus repository reality |

These are different questions, likely different review purposes, and plausibly different surfaces. A run
can pass completion perfectly and fail coherence — that is precisely T9, and a single undifferentiated
final step is structurally incapable of detecting it. Role and purpose mapping are not decided here.


## 39. Long-running autonomy threat model

### 39.1 Research discipline

The motivating account for this section — an agent accumulating defensive "scar tissue" over a long
autonomous run — is an **anecdotal report from an online forum**. It is not evidence, it is not cited
here as support, and no part of Part II depends on it being true.

That is a deliberate quality test: **the architecture must stand if the anecdote were fabricated.** It
does, because each threat below is derivable either from mechanisms already observed in this repository
(M0's silent snapshot invalidation, M1's interchangeable reviewers, M2A's non-transitive-closure trap) or
from established software-engineering literature about human-maintained systems:

- D. E. Perry and A. L. Wolf, *Foundations for the Study of Software Architecture*, ACM SIGSOFT Software
  Engineering Notes 17(4), 1992, 40–52 — architectural erosion versus drift, and rationale as a
  first-class architectural component. <https://dl.acm.org/doi/10.1145/141874.141884>
- G. Edwards-Alexander, *The Economic Benefit of Refactoring*, martinfowler.com, 2026 — one controlled
  experiment on repository context cost (None[§28.1](context-economy.md#281-the-empirical-result-being-incorporated)), with its limits stated there.

Both predate or sit outside the agent-specific claim. The classical literature describes these failures in
*human* systems; the hypothesis that autonomous agents encounter them faster, and with less friction
because they neither tire of a bad pattern nor feel its cost, is **plausible and unproven**. Proofbound
should not assert it. The mitigations are worth building regardless, because they are the same mitigations
the human case has always needed.

### 39.2 Threats

| ID | Threat |
|---|---|
| **T1** | **Context rationale loss** — original rationale becomes unavailable, compressed or unretrievable |
| **T2** | **Local workaround promotion** — a bounded adaptation silently becomes global convention |
| **T3** | **Pattern imitation** — agents reproduce historical code patterns that were never authoritative |
| **T4** | **Decision compounding** — individually reasonable changes compose into poor architecture |
| **T5** | **Baseline drift** — the standard the system evaluates itself against moves with it |
| **T6** | **Reviewer contamination** — the evaluator inherits the reasoning that produced the change |
| **T7** | **Stale defensive policy** — a workaround outlives the condition that justified it |
| **T8** | **Guidance accumulation** — instructions grow until authoritative rules cannot be retrieved |
| **T9** | **Local-pass / global-fail** — every task passes; the aggregate violates architectural intent |
| **T10** | **Metric gaming** — drift and context metrics become targets and are optimized instead of quality |

The full mitigation matrix, including what is *not* mitigated today, is in the implementation plan
alongside the roadmap that would close each gap. It is kept in one place deliberately: duplicating it here
would create two copies that disagree within a milestone.

Two threats deserve a note because they are self-inflicted by this very document.

**T8 was live in this repository, and the split is the response.** The architecture had grown into a
single ~195 KB document in which a research hypothesis and a proven invariant were typographically
indistinguishable. It is now a routed corpus with explicit authority classes
([../README.md](README.md)), and a bounded task reads the documents its work touches. That is a real
mitigation rather than a reading convention, but it is not a permanent one: the corpus can grow again, and
nothing mechanically bounds the size of a normative document. The residual risk is recorded in the plan.

**T10 is a risk created by None[§28](context-economy.md#28-context-economy-and-refactoring-economics) and §37.4.** The moment Proofbound measures repository context cost or
invariant violations, those numbers become optimizable — and an agent can reduce "bytes read" by reading
less than it should, or satisfy an invariant by routing around it. This is why P1 and P13 forbid a metric
from becoming a verdict, why None[§37.5](context-economy.md#375-coherence-and-context-economy-are-different-measurements) rejects a composite debt score, and why every drift signal terminates in
a semantic evaluator rather than a gate. It is mitigated by construction, not by monitoring.
