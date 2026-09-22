# Concepts

What the pieces mean, and why each exists. For *doing* a run see the
[operator guide](operator-guide.md); for the normative definitions see the
[architecture corpus](architecture/proofbound/README.md), which is what the system actually obeys.

## The shape of a change

```
goal ──▶ proposed requirements ──▶ fresh challenge ──▶ accepted authority
                                                              │
                                                              ▼
       sealed delivery ◀── deterministic checks ◀── independent review ◀── admitted implementation
```

Each arrow is a transition something must earn. None of them is a formality.

### Goal

The owner's words, unreviewed on purpose. It is the root authority: every contract in the run
carries its digest, so a run can always say which goal it was working from. Reviewing the goal
would mean the system judging what you asked for.

### Proposed requirements

A worker reads the project and proposes numbered obligations, compatibility constraints, a declared
domain and checks. **Proposed, not accepted** — they have no authority yet.

### Fresh challenge

A *different* worker context challenges those requirements: contradictions, gaps, unstated
assumptions, whether they actually serve the goal. Structural separation, not a claim of statistical
independence — a fresh context has a different view, and that is the whole of what it offers.

### Accepted authority

You accept. From that moment the requirements govern: they enter the ledger with a content identity,
the change graph records what depends on what, and a **candidate** — a content-addressed identity
for the accepted set — becomes derivable.

### Admission

The transition where implementation becomes permitted. `admit` checks that the candidate is what the
project currently derives, that it carries a durable consistency acceptance, and that the retained
evidence does not contradict it — then binds the contract in the **same atomic write**.

This used to be advisory. `authorize` printed an answer and nothing consumed it, so a refused run
and an honoured one left identical state; [`pb-handoff-1`](architecture/proofbound/evidence/admission-bypass-reproduction.md)
found that by running it. Now a launch without a matching admission record is refused.

Authority is **fixed at admission**. A task admitted under candidate `C1` keeps running after the
project moves to `C2` — it is honestly a `C1` task, through review, repair and acceptance.
Rechecking currentness later would either discard correct work or require guessing whether the newer
candidate mattered.

### Independent review

A fresh worker context reviews the delivered bytes against the accepted requirements, with the
producer's report as an input. It cannot accept its own work: the producing and reviewing roles are
separate, and acceptance is a **parent act** you take.

### Deterministic checks

The project's own check command, plus scope verification: did the change touch only what the
contract permitted? These are the parts a program can settle, and they are settled by a program.

### Sealed delivery

A directory containing the patch, the accepted authority, the retained evidence and a handoff
record. It is inspectable without the run, and re-checkable afterwards.

## Evidence, and its four kinds

Retained evidence declares what kind of claim each part is. They do not combine into one verdict:

| Kind | Means |
|---|---|
| **Integrity** | A record exists and its bytes hash to what was recorded |
| **Recompute** | A quantity re-derived from retained inputs — counts, attribution, price |
| **Reported** | A semantic judgment, retained verbatim and attributed. Never confirmed here |
| **Unavailable** | The evidence a check needs is absent. Not a pass, not a failure |

A fifth status, **not-observed**, separates "this did not happen" from "we cannot tell": a run that
launched nothing did not *refuse* — refusing requires a recorded refusal.

## Accounting

Five different facts that are easy to conflate and are kept apart:

1. **Measured usage** — token counts the provider reported, per call.
2. **Derived cost** — that usage priced at a *dated* table. Pinned, so a later price change cannot
   reinterpret a historical run.
3. **Executor-reported cost** — the worker tool's own figure. Known to disagree with (2).
4. **Estimated reserve** — what is held back before admitting another launch.
5. **Provider-confirmed billing** — what you are actually charged. **Never observed by Proofbound.**

Unknown expenditure is **unknown, not zero**. A call that started and did not finish leaves the
figure incomplete, and an incomplete figure admits no further launch — because the alternative is an
infrastructure failure that looks like a remarkably cheap run.

Equal start and finish counts mean the totals balance. They do **not** establish that the same calls
finished, and they do not establish which attempt spent what.

## Boundaries

Workers run inside a macOS `sandbox-exec` boundary: the project is writable, the harness is
readable, evaluator material is not, and the credential staged into the run's own home is only the
one backend's entry.

The boundary denies `signal`, so nothing inside it can stop even its own child. Termination is
therefore the **host controller's** job, outside the boundary — with ownership corroborated before
anything is signalled, groups and individual pids both, and survivors established by a liveness
sweep rather than by signals having been sent. Delivery is not death.

Your coordinator runs **outside** that boundary. What it accessed is reported, not constrained.

## What the words do not mean

- **"Proof"** — objective facts are mechanically checked. Engineering adequacy is judged.
- **"Verified"** — a hash matched, within a trust boundary that includes anyone who can rewrite the
  records.
- **"Independent"** — a separate role in a fresh context. Not a statistical claim.
- **"Complete"** — the required observations were available and passed. Not that nothing was missed.

## Where the rules actually live

This page explains. It does not define. Each rule has exactly one canonical home:

| Topic | Canonical |
|---|---|
| Principles `P1`–`P13`, truth layers | [core-model.md](architecture/proofbound/core-model.md) |
| Invariants `I1`–`I15`, review purpose, roles | [execution-and-review.md](architecture/proofbound/execution-and-review.md) |
| Artifact identity, ledger, provenance, the change graph | [artifacts-and-provenance.md](architecture/proofbound/artifacts-and-provenance.md) |
| Freeze, candidate identity, admission | [freeze-and-binding.md](architecture/proofbound/freeze-and-binding.md) |
| Threats `T1`–`T10`, long-run autonomy | [long-running-autonomy.md](architecture/proofbound/long-running-autonomy.md) |

If this page and one of those disagree, the canonical document is right and this is a bug.
