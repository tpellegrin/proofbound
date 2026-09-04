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
