# Authority-workflow demonstration — successor note

**Dated 2026-09-17.** Corrections and additions relating to `pb-authority-demo-1`, recorded here
rather than by editing that demonstration's records.

`pb-authority-demo-1`'s design, preparation and run records are **unmodified**. Its outcome stands
as it was recorded: the specification challenge found a real defect, and the run stopped there under
its own frozen no-repair rule. That is a genuine result about the workflow — a review that actually
caught something — and it is worth more preserved than overwritten by a successful rerun. Nothing
below retracts it.

What follows is what the successor, `pb-authority-demo-2`, found wrong or missing in the
predecessor's *preparation* when it came to reuse it, plus one stale index row.

## The stale index row

The corpus entry point described `evidence/authority-workflow-demonstration.md` as **"Design, not
yet run — no paid agent has executed it."** That was true when the design was committed at
`e79c944` and stopped being true at `1606267`, where the demonstration ran with real agents and
real spend. The index row is corrected in this change to state the actual outcome. The design
document itself is untouched.

## Corrections to the predecessor's preparation

Each of these was reproduced against the committed predecessor artifact before being repaired in
the successor, so the claim is a measurement rather than a reading.

**Spend accounting reported unsettled figures as settled.** `demo/pb-authority-demo-1/scaffold.py`'s
`spend()` had three distinct defects. It priced whatever usage totals a session happened to hold and
labelled the result complete, so a session with two model calls started and one finished reported
`complete: true`. It treated an absent session database as proof that nothing had been spent,
returning `{"derived": 0.0, "complete": true}` for a run tree that had launched attempts. And it
priced at the moment the report ran rather than the moment the work executed. The reproduction is
exact: absent database gave `{'derived': 0.0, 'complete': True}`; two started against one finished
gave `{'derived': 0.0123, 'complete': True}`; and `admit()` returned `True` in both states, so an
unknown expenditure would have permitted a further paid launch.

The successor reconciles the run tree's launch facts against the session's usage and refuses to call
a figure complete unless both agree, restating the principle the earlier spend work established:
unknown expenditure is unknown, never zero, and it blocks further launches. Regressions for every
defect above are in `tests/test_authority_demo2_accounting.py`.

**The external behavioural suite was blind at the boundary it existed to test.** The predecessor's
suite had one boundary case, at `capacity=1`, `refill_per_second=4.0`, clock base `5000.0`,
advancing by `0.25`. Every one of those values is dyadic and exactly representable in binary
floating point, so the case passed by arithmetic luck — and it therefore missed precisely the defect
the predecessor's own specification reflector found by reasoning about non-representable rates. A
suite whose only boundary case is exactly representable cannot discriminate an exact-boundary claim
from a true one.

The successor suite sweeps deliberately non-dyadic rates across six clock magnitudes, always
advances the injected clock by the delay the implementation itself returned, exercises the
exceptional case the intent defines, and is established as **satisfiable** by a private witness that
also passes the fixture's own unedited suite, and as **discriminating** by failing six defective
variants — including the predecessor's formula — each breaking exactly one requirement.

**The no-I/O assertion was a substring scan.** It read the class source looking for `open(` and
`sleep`, which would reject a harmless comment containing `open(` and would miss
`getattr(time, "sleep")()`. It is replaced by a runtime observation of the calls the query actually
makes, with its limit stated on the test itself: it establishes that the exercised paths did not
sleep or open anything, and says nothing about paths it did not exercise. Whether an implementation
performs I/O in general remains a semantic review question.

**The suite holdout described itself as more than it is.** `chmod 0000` denies an ordinary read and
that is all it does — the file's owner may restore the mode without any privilege escalation and
then read. The successor names the measure **withholding, not isolation**, and its check reports the
observation rather than the label. The repository's real isolation mechanism is the semantic view,
and these demonstration runs are deliberately outside it.

**The rehearsal never exercised the authorization guard.** The predecessor's `rehearse.py` wrote a
candidate identity into a task contract, which is a declaration, and never invoked
`pb_execution.py authorize`, which is the guard. The successor's rehearsal invokes it on both the
clean and the repair path, and additionally verifies that it **refuses** while no durable
consistency acceptance exists — so the guard is observed doing both of its jobs before any paid call
depends on it.

## What the predecessor's plan did not say, and the successor had to decide

**What a repair invalidates.** The predecessor budgeted no repair cycle, so its plan never had to
answer the question. Budgeting one makes the answer load-bearing, and it is not symmetric. A repair
to the implementation invalidates the implementation review that found the defect and requires the
behavioural suites to be rerun, but leaves the specification acceptance, ledger record, graph
validation, candidate freeze and consistency acceptance standing, because none of them describes the
implementation. A repair to the specification invalidates all of them in sequence — the reflection,
the ledger record whose artifact digest no longer matches, the graph validation, the candidate
freeze and therefore the candidate identity, the consistency acceptance recorded against the dead
candidate, and any authorization already obtained. Each must be re-earned by a fresh attempt rather
than re-asserted. The successor's protocol freezes both chains before its first paid call.

**Where parent intent lives when the ledger cannot hold it.** The ledger records project artifacts
produced by accepted tasks. The accepted intent is the input authority, produced by no task, so it
cannot be a ledger entry. Naming it an external authority is necessary but insufficient on its own,
because an external authority whose identity is merely asserted cannot survive a handoff. The
successor stamps the intent's digest into the header of every task contract placed in the run root,
so a coordinator holding only the repository can recompute the digest and compare. A mismatch is a
stop condition.

**That a single-member freeze is a narrow demonstration.** Both demonstrations freeze exactly one
artifact, `spec.md`. That is enough to demonstrate candidate-bound implementation and an
independently derived authorization, and it is *not* enough to demonstrate aggregate coherence:
consistency acceptance over one member is a judgement about one artifact against the intent, not
about agreement among several. The successor states this in its protocol and requires its
consistency reflector to state it in the run's own evidence.

## Where the successor's records live

`demo/pb-authority-demo-2/` holds the successor's intent, frozen protocol, task contracts, fixture,
external suite, witness, suite verification and scaffolding. Its run report will record its own
outcome there. This note is the only place the predecessor's records are corrected, and it corrects
them by addition.
