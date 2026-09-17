# Execution and review model

> **Normative.** The inherited DSD mechanics Proofbound relies on and must not break: the mechanical
> invariants `I1`–`I15`, the review-purpose registry enforced at acceptance, what a repair iteration is,
> and the boundary of the parent's authority.
>
> Background on how DSD works is in [evidence/original-rfc.md §2](evidence/original-rfc.md).
> Entry point: [README.md](README.md).

## 3. Existing invariants that must be preserved

These are load-bearing. Any proposal that violates one is wrong until proven otherwise.

| # | Invariant | Where it lives |
|---|---|---|
| I1 | Python proves only objective facts; it never adjudicates prose or assigns PASS/FAIL | `evidence_gate.py` docstring; `test_v15_3_semantic_boundary.py` |
| I2 | A clean gate means "safe to interpret", never "the engineering passed" | `SKILL.md`, `WORKSPACE.md`, `README.md` |
| I3 | One attempt = one immutable reservation; reservations/prompts/contracts/rules/gates never mutate after creation | `run_worker.py:reserve_attempt`, `evidence_gate.py` `open("x")` |
| I4 | Project mutation requires **fresh independent review provenance** before acceptance | `dsd_state.py:_assert_fresh_reviewer` |
| I5 | Read-only roles that move project state fail integrity, mechanically | `evidence_gate.py` `READONLY-SCOPE-MOVED` |
| I6 | `Allowed source changes`, when present, is a hard mechanical boundary; `NONE` means no writes | `_contract.py`, `evidence_gate.py` `WRITE-RESTRICTION` |
| I7 | Worker context = run facts + COMMON + exactly one role + one contract (+ proof patterns only if named) | `render_worker_prompt.py` |
| I8 | Worker reports are natural language; no machine grammar is required for acceptance | `README.md`, `PROMPTS.md`, `COMMON.md` |
| I9 | State stores facts, not routing heuristics, counters, or barrier machines | `WORKSPACE.md`; `test_v15_5_adversarial.py::test_new_phase_state_does_not_create_barrier_machine` |
| I10 | Exactly one `next_action`; resume reads live state first and never reconstructs the run | `SKILL.md`, `COMPACTION.md`, `check_state.py` |
| I11 | Waiting is quiescent; a timeout without terminal evidence is a non-event; no model-visible polling | `SKILL.md`, `wait_worker.py`, `claude_worker_rewake.py` |
| I12 | Scope-observed mutation is exclusive per checkout; writer + read-only concurrency needs worktrees | `WORKSPACE.md` |
| I13 | Phase evidence is frozen; any later mutation makes it stale and demands fresh verification + audit | `SKILL.md`, `WORKSPACE.md` |
| I14 | Hot doctrine surfaces stay small; detail is cold-loaded on demand | `test_v15_4_consolidation.py` byte caps |
| I15 | The Evidence Clerk is always project-read-only, never recursive, and cannot waive integrity failures | `_contract.py`, `dsd_attempt.py:interpret` |

---


## E1. Attempts are repair history; contract revisions are changes of intent

*Normative.*

When a review returns findings, the repair is a **new attempt under the unchanged contract**, with the
findings passed as an ordinary `--input`. It is *not* a new contract revision. A new revision would be
actively unsafe: acceptance matches attempts to the current contract by hash, so rebinding drops the
earlier mutating attempts from the freshness scan and a stale review could then be accepted.

A new contract revision means the *intent* changed, not that the work needed another round.

Evidence: [evidence/implementation-findings.md §30.2](evidence/implementation-findings.md#302-m1--capability-and-purpose-are-different-questions).

### 27.1 Decision resolved — the review-purpose vocabulary is fine-grained

The open question in [§26.4](evidence/implementation-findings.md#264-review-purpose-model--the-central-m2-decision) was whether to record five purpose names when only two enforcement classes
exist today. **Decision: keep the five.** `purpose != capability != role`.

| Declared purpose | Qualifying roles today |
|---|---|
| `proposal-reflection` | `spec-reflector` |
| `design-reflection` | `spec-reflector` |
| `specification-reflection` | `spec-reflector` |
| `consistency-reflection` | `spec-reflector` |
| `implementation-review` | `reviewer` |

Four purposes share one role. They stay distinct names because the reason a review existed is not
recoverable from the role that performed it. Collapsing them would discard provenance permanently and
force retro-classification of every historical record the first time a role is added — the same class
of mistake M0 had to repair in the worker-rules manifest, where membership was recorded but order was
not, and the missing fact could only be reconstructed as a hypothesis.

The risk the decision accepts is that a reader mistakes recorded precision for enforcement. The
mitigation is to state the guarantee exactly, everywhere it appears:

> the declared purpose was reviewed by a role authorized for that declared purpose

and never:

> Python proved the reviewer performed a philosophically correct architecture review.

The table is validated at import: every purpose must name at least one role that exists and that is
already in `INDEPENDENT_REVIEW_ROLES`. A typo cannot silently authorize a writer role.


### 38.5 The parent does not become the auditor

The parent's authority is unchanged (`I<n>` §3, plan [§2.5](evidence/original-rfc.md#25-fresh-independent-review-enforced-in-python)). It may identify that a broader decision is
required, route and escalate, select the artifact workflow, choose relevant authoritative context, enforce
that required reflection occurred, and bind execution to accepted artifacts.

It may not substitute its own accumulated judgment for independent reflection. The parent is the least
independent evaluator in the system — it has been present for every decision and is maximally
contaminated by exactly the execution context [§38.2](long-running-autonomy.md#382-the-cumulative-coherence-audit) excludes. An orchestrator that reviews cumulative
coherence itself is the clearest possible violation of P12.

## 51. What each review purpose actually asks

The registry guarantees exactly one thing: *the declared purpose was reviewed by a role authorized for
that declared purpose*. Four of the five purposes name the same role today, and
[§27.1](#271-decision-resolved--the-review-purpose-vocabulary-is-fine-grained) keeps them separate
because the recorded reason for a review is not recoverable from the role that performed it.

What was never written down is what distinguishes them **as questions**. A `spec-reflector` handed a
contract declaring `design-reflection` has, until now, had no canonical statement of what a design
reflection asks that a specification reflection does not. That is a gap in guidance, not in mechanism:
nothing here becomes a field, a kind, or a check.

| Purpose | The question it asks | What a finding looks like |
|---|---|---|
| `proposal-reflection` | Does this expose the decisions the intent actually forces, including the ones it would be convenient not to raise? | A consequential decision the intent implies is neither resolved nor acknowledged as open |
| `design-reflection` | Are those decisions resolved, and are the tradeoffs the resolution accepts stated rather than assumed? | A decision left unresolved, resolved two ways in different places, or resolved with a cost nobody named |
| `specification-reflection` | Is each accepted decision bound to something that could later be shown false? | An accepted decision with no observable consequence, or a consequence that binds a mechanism the decision never required |
| `consistency-reflection` | Do the accepted artifacts agree as one engineering authority? | Two accepted artifacts that are each defensible and jointly contradictory |
| `implementation-review` | Did the implementation satisfy the contract it was bound to? | Work that does not meet its accepted contract |

**These are questions, never checklists.** A reflection is not required to canvass scalability,
security, observability and the rest; `P13` makes generic breadth expensive and generic breadth is what
produces generic prose. The obligation is to the decisions this change actually forces, which is a
property of the change and not of a template.

### 51.1 Bind consequences, not resemblance

The distinction that makes `specification-reflection` a different question from `design-reflection` is
worth stating on its own, because it is the rule that keeps accepted architecture from becoming
architectural fashion.

A specification binds what must be **true**, not what must be **built**. *"Provider endpoint,
credential, payload shape and error vocabulary do not reach the code that decides what to notify a user
about"* is a consequence: it can be shown false, and two quite different architectures can satisfy it —
one hiding the provider behind an explicit contract and an adapter, another behind registration and
dispatch with no interface type at all. *"There must be a `Sender` interface with one adapter per
provider"* binds a mechanism, and rejects the second architecture for its form rather than its effect.

**Mechanism may be bound when the mechanism is itself part of accepted intent** — a wire protocol, a
regulatory requirement, a platform constraint, or a case where naming the mechanism is the only way to
make the consequence falsifiable. The rule is not *never bind mechanism*; it is *do not bind mechanism
that the decision did not require*.

This is `P11` applied to Proofbound's own output. Repository patterns are evidence rather than
authority, and a specification that freezes the shape of one good solution turns a pattern into
authority through the acceptance chain instead of through imitation.

### 51.3 A proposed requirements document is an ordinary artifact

Both authority demonstrations stopped at findings that a challenge to the *intent* would plausibly
have caught before any money was spent, and in `pb-authority-demo-2` the defect was in the accepted
intent itself — a document that entered the chain as an input, frozen by assertion, with every
artifact downstream of it independently challenged and nothing challenging it.

Closing that gap needs **no new machinery**, and adding some would be the mistake. A proposed
requirements document is a project artifact: authored under a task contract, challenged by a fresh
`spec-reflector` under the existing `proposal-reflection` purpose, gated, accepted, recorded in the
ledger, and frozen into a candidate like anything else. There is no intent artifact kind, no
mandatory intent role, and no new purpose — a taxonomy would attract behaviour that then depends on
it, which is why artifact kinds were tried and rejected. A worked procedure, with contracts and a
credential-free replay of the whole chain, is in `evals/authority_slice/`.

**The bootstrap boundary.** The owner's goal remains the root authority and is **not** reviewed by
the chain. Somewhere a person says what they want; demanding a reviewed parent for every human
decision is an infinite regress, not a guarantee. What the chain reviews is the proposed
requirements *written to express that goal*. The goal stays external to the ledger — it is produced
by no task — and its identity is made checkable rather than asserted by stamping its digest into
every contract, so a coordinator holding only the repository can recompute and compare.

**What the challenge may conclude.** Whether the proposed requirements faithfully express the goal;
whether they state a usable domain rather than implying they hold everywhere; whether any of them
contradict each other over that domain, named specifically and with a reachable witness; whether
they rest on an assumption the goal does not support. Three conclusions are legitimate: a concrete
defect, **no defect found within declared coverage**, and unresolved uncertainty.

**What it may not do.** Replace the goal, choose between conflicting requirements, or silently
narrow the domain so a conflict disappears. Narrowing a domain is an authority decision; a reviewer
that makes it has substituted itself for the owner. A finding routes back to the authority that can
repair it — the owner for a defect in the goal, the author for a defect in the requirements — and
what becomes stale is what `P9` and the ledger closure already say becomes stale: dependents of a
superseded artifact are `needs-revalidation`, and a repaired requirements document invalidates the
reflection that examined it, its ledger record, the graph validation, the candidate identity
derived from it, and any consistency acceptance or authorization recorded against that candidate.

**A clean gate proves the permitted process occurred.** It does not prove the requirements are
jointly satisfiable. Where satisfiability is decidable over a declared finite domain it can be
established deterministically and the challenge can carry a proof; where it is not, the honest
report is the coverage actually checked. A reference implementation passing tests is evidence that
the requirements are satisfiable in the cases exercised, not a universal proof.

**Proportion.** Review effort scales with a change's scope and risk. Accepted requirements that a
change does not touch are not re-authored for every implementation edit; an unchanged accepted
artifact stays accepted, which is what the ledger is for. Whether an earlier challenge finds more
defects per unit of effort than a later one is a **hypothesis to evaluate**, not a property of the
diagram. A paid intent reviewer moves detection earlier in the chain; it does not make detection
free, and its cost belongs in the same accounting as every other attempt.

### 51.2 Discovery downstream is repair, not a new workflow

Nothing above implies a waterfall. A design will expose decisions the proposal did not see, and a
specification will occasionally expose that an accepted decision cannot be bound at all. Those are
ordinary outcomes with an existing mechanism: the artifact is repaired under the same contract, or —
when the engineering intent itself has changed — the upstream artifact is superseded (`P9`), which
makes its dependents `needs-revalidation` through the ledger closure that already exists. No new state
records that a decision was discovered late.

Proportionality applies to process as well as to architecture. A change that forces no consequential
decision has a short proposal and a short design, and that is the system working rather than the
system being skipped.
