# `pb-authority-demo-1` — the run

> **Added 2026-09-17, after this report was written. The report below is unchanged.** Corrections to
> this demonstration's *preparation* — spend accounting, the external suite's boundary blindness, the
> no-I/O assertion, the holdout's description, and the unexercised authorization guard — are recorded
> in
> [`authority-workflow-successor.md`](../../docs/architecture/proofbound/evidence/authority-workflow-successor.md).
> Every terminal record here carries `session_id: null` from a defect found later, so this run's
> completeness claim rested on an attribution check that could not have been performed.

**2026-09-17.** Executed at `faae1cf`, whose parent `0a1d749` is the preparation the plan was frozen
in. Plan: [`execution-record.json`](execution-record.json). Design:
[`authority-workflow-demonstration.md`](../../docs/architecture/proofbound/evidence/authority-workflow-demonstration.md).
Preparation findings: [`design-to-execution-check.md`](design-to-execution-check.md).

**Verdict: partially demonstrated.** Two of the five planned paid runs executed. The independent
specification challenge found a real defect in the specification, the parent rejected it on that
evidence, and the frozen plan does not budget a repair cycle — so the live run stopped there. The
remaining stages are demonstrated mechanically only, with a fake executor, and are reported as
such.

**$0.017183 of $0.40**, accounting complete: 26 model calls started, 26 finished, nothing unpriced.

## What ran live, with real agents

| # | task · role | purpose | outcome | evidence |
|---|---|---|---|---|
| 1 | `design/RG-spec` · `spec-author` | — | wrote a 5,931-byte specification | [`spec.md`](evidence/spec.md), [report](evidence/spec-author-1-report.md), [gate](evidence/spec-author-1-gate.json) |
| 2 | `design/RG-spec` · `spec-reflector` | `specification-reflection` | **FAIL**, one blocking finding | [report](evidence/spec-reflector-1-report.md), [gate](evidence/spec-reflector-1-gate.json) |

Both gates `integrity_ok: true`, no errors. The reflector ran project-read-only
(`writes_project: false`) and its scope diff is empty in both directions: it changed nothing and
added nothing. The only project source addition in the whole run is `spec.md`.

Nothing was accepted. `RG-spec` is `gated`, not `accepted`; the ledger is empty; no candidate was
frozen; no consistency record exists. That is the correct state for a rejected specification, and it
is the state on disk rather than a claim about it.

## The finding, and why the parent accepted it as a defect

The reflector reported that the specification's requirement R1 contradicts itself: it mandates
returning `(1.0 - available) / refill_per_second` *and* asserts that after waiting exactly that
long, `allow` admits. It then did the work to show that is false — wrote a throwaway
specification-faithful implementation, swept capacity 1–5 against nine refill rates at several drain
depths, and found 45 of 135 exact-advance cases where `allow` still refuses, because
`elapsed = now - last` loses precision when the clock base is not zero. It located the boundary
precisely: the claim holds only for a clock base of exactly `0.0`. It also found a minor over-claim,
that the return value is "always finite", which fails for a subnormal `refill_per_second`.

**Independently reproduced** before the parent decided anything, against the private reference
implementation rather than the reflector's:

| check | result |
|---|---|
| exact-advance cases at clock base `1000.0` | **15 of 45 refused** |
| the same cases at clock base `0.0` | **0 of 45 refused** — exactly as reported |
| `retry_after` with `refill_per_second = 1e-310`, bucket drained | `inf` — "always finite" is false |

And the finding lands on the preparation too. The external suite's own boundary test uses capacity
1, rate 4.0, clock base 5000.0 and advances 0.25 — all dyadic, so it is exactly representable and
**passes by luck**. A hidden suite written to catch exactly this class of defect did not catch it.
That is the most useful single result of the run.

This is a genuine semantic finding by an independent reviewer, on work a real agent produced, that
neither the producer nor the orchestrator's own hidden checks caught. Nobody asked it to find
anything and nothing was planted.

## Why the run stopped rather than revising

The frozen plan records `repair_cycle_budgeted: false` and *"a reviewer finding a defect is a
legitimate outcome; recorded and the run stops"*. A revision would be a second author attempt plus a
fresh reflection — two more paid runs, taking the total to seven against five planned. The budget
had $0.28 of headroom and the attempt model would have permitted a second attempt on the task, so
this stop is the frozen rule being honoured, not a resource limit being hit.

Stated plainly because the temptation ran the other way: continuing would have produced a fuller
demonstration, and the reason not to is that the plan said so before the evidence existed.

## Stages not demonstrated live

Ledger acceptance and dependency validation, candidate derivation and freeze, aggregate consistency
review and acceptance, the fresh-context handoff, candidate-bound implementation, implementation
review, and final acceptance. **All are unexercised by real agents.**

They were exercised mechanically, unpaid, with a fake executor
([`rehearse.py`](rehearse.py)) — which is evidence that the *command sequence* composes and nothing
about whether an agent can do the work:

- author, then the author's own gate refused as its own review, then reflect, then accept against
  the reflector's gate;
- `pb_ledger record` → `pb_graph validate` satisfied → `pb_freeze create` yielding candidate
  `9d7d87b0…`;
- consistency accepted and `pb_consistency status` readable for that candidate;
- candidate-bound implementation, a fresh reviewer attempt, acceptance against the reviewer's gate;
- the external suite passing 11/11 and the project's own 5/5 on the fake implementation.

**The handoff did not happen.** No fresh orchestrator was given the artifacts and asked to continue,
because the workflow stopped before the handoff point. Nothing here should be read as evidence about
resumption.

## Mechanical enforcement observed

Four refusals, each derived and each for its intended reason. Three were exercised on isolated
disposable copies by [`controls.py`](controls.py); one fired live and free during the run.

| control | refusal | where |
|---|---|---|
| a producer's own gate cannot be its own review | `declared review purpose 'specification-reflection' requires role spec-reflector, but the accepted integrity gate records role 'spec-author'` | **live** |
| a review predating a later project-mutating attempt | `fresh independent-review requirement violated: accepted review predates later project mutation in spec-author-2` | isolated |
| a review of one contract, for a task bound to another | `source gate is not bound to task.current_contract` | isolated |
| the project no longer derives the accepted candidate | `candidate-not-computable` from `pb_freeze compare` | isolated |

**These say nothing about whether semantic reviewers detect defects.** A refusal is derived; a
judgement is not. That the reflector found a real defect is separate evidence, and it is the
reflector's, not the gates'.

Two of the three isolated controls only fired after the test setup was corrected: staleness is
measured against later attempts that *actually changed* the project, so a second attempt writing
identical bytes proves nothing; and candidate binding compares the contract **path** the gate
recorded, so rewriting one file in place proves nothing either.

## Manual decisions

| question | actor and authority | evidence consulted | decision and action |
|---|---|---|---|
| What is the accepted intent? | coordinating agent as parent (deviation D1) | the `rateguard` fixture and the change being demonstrated | authored `intent.md`; recorded its digest in the plan before any launch |
| Which artifacts constitute this change? | parent | `pb_ledger`'s record precondition; `pb_graph`'s member rules | declared `spec.md` alone. The intent cannot be a member: every ledger record needs an accepted clean gate and a review, and parent authority has neither |
| Is the specification acceptable? | parent | the reflector's report, then independent reproduction of both findings | **rejected.** The blocking finding is real; `allow` refuses after waiting exactly `retry_after` in a third of sampled configurations |
| Is the reflector's finding a defect or a preference? | parent | reproduced 15/45 refusals at a non-zero clock base, 0/45 at base zero, and `inf` for a subnormal rate | a defect. Not style, not a matter of taste |
| Continue with a repair cycle? | parent, bound by the frozen plan | `repair_cycle_budgeted: false`; five planned runs; $0.28 headroom unused | **stop.** Budget permitted it; the plan did not |
| Accept the aggregate; accept the implementation | — | — | never reached |

## Manual orchestration required — the deliverable

Separated by kind, because "a human had to do something" is not by itself a defect.

**Legitimate semantic judgement** — the parent authoring the intent, choosing the declared artifact
set, judging the reflector's finding, and deciding whether to revise. None of this is automatable
and none of it should be.

**Expected parent orchestration** — binding each contract, launching each role with its permitted
inputs, gating, and accepting against the right gate. All of it is existing documented commands.

**Missing documented procedure**, and the honest finds:

1. **The ledger cannot hold parent authority.** The design's first step —
   `pb_ledger record --artifact intent.md` — is not executable. No document says where accepted
   intent lives if not the ledger; the answer had to be derived from `pb_ledger`'s preconditions.
2. **Reviews are attempts, not tasks.** The design modelled each review as its own task with its own
   contract, which the binding check refuses. The correct shape — later attempts on the same task
   and contract, with the producer's report as an exact `--input` — is visible only in a test slice,
   not in the architecture documents.
3. **Several exact command signatures in the design were wrong** and were corrected only by running
   them: `--artifact` resolves against the caller's working directory, the graph must live inside
   the project, contracts must live inside the run root, a contract needs a
   `Contract revision: rNNNN` line, and `pb_consistency status` takes `--candidate` rather than a
   freeze path.
4. **The design's two refusal controls were described in terms no mechanism implements** (see
   above).

**Avoidable intervention caused by an integration defect** — none observed. Every refusal
encountered was correct, and every correction was to the design's description or to my own test
setup, not to the harness.

## Corrections to earlier records

One claim from the previous milestone's preparation is withdrawn here: that a read-only reviewer
following a mutating attempt requires the mutation to be committed first. It does not. That appeared
to be a harness finding and was my fake executor branching on task id when the reviewer runs on the
*same* task, so it re-ran the producer's mutation during the review. `READONLY-SCOPE-MOVED` caught
it and was right.

## Verification limits

- **One observation of each stage that ran**, and no observation at all of six stages. Nothing here
  is a rate.
- **The external suite is withheld by filesystem permission, not isolation.** Mode `0000` for the
  duration of each run, verified per run and denying the owner (uid 501, errno 13), with compiled
  copies removed first. A worker that escalated privileges, or a mode restored early, would defeat
  it. These runs are deliberately outside a semantic view.
- **`retry_after` was never implemented by a real agent**, so the external suite has never run
  against real implementation work. Its only live use was reproducing the reflector's finding.
- **Two tests in the lifecycle module are timing-flaky under load** at their one-second deadline —
  clean in four runs alone, failing once in a loaded full-suite run. Not a mechanism defect, not
  touched, recorded so it is not rediscovered as news.
- The reflector's own throwaway implementation lived in the executor's temp directory and was not
  retained; its findings were reproduced independently rather than trusted.
