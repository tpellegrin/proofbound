# `pb-authority-demo-1` — design for the first real-agent authority run

**2026-09-16. A design, not a run.** No paid agent is launched by this milestone. It is written now
so the workflow's shape is fixed before any model is asked to participate, and so the manual
decisions it needs are visible in advance rather than discovered halfway through.

**Nothing like it exists yet.** The mechanisms are all implemented and individually tested —
`pb_ledger`, `pb_graph`, `pb_freeze`, `pb_consistency`, the review-purpose vocabulary, candidate
binding — and M2C-B proved candidate binding end to end *as a deterministic slice*, with fake
workers. What has never happened is the whole chain with real agents holding the semantic roles.
That is the gap this design closes, and integration feasibility is all one run of it could
establish.

## What one successful run would and would not show

Would: that the eight steps compose; that the mechanical gates admit a genuinely authorized
sequence and refuse the two malformed ones tested separately; that a second orchestrator can resume
from the artifacts alone; and where manual work is still required.

Would not: that the output is good, that reviewers are reliable, that the workflow scales, or
anything about long-running autonomy. One run is one observation, and a clean review is one
reviewer's opinion recorded under a purpose — never a proof of quality.

## The project and the change

A disposable project, created for this and thrown away: **`rateguard`**, a token-bucket rate
limiter of perhaps 120 lines, with its own test suite.

Starting state: `RateGuard.allow(key)` returns `True` or `False`.

**Accepted intent:** *a caller told "no" cannot tell whether to retry in a millisecond or a minute,
so refusal must carry the wait.*

**The coherent change:** `allow(key)` keeps its meaning, and a new `retry_after(key)` returns the
seconds until the next token would be available — `0.0` when a call would be admitted. The
refill arithmetic that currently lives inside `allow` has to be factored out so both can use it
without drifting, which is what makes this a real change rather than an addition.

**Acceptance criteria**, fixed here and checked by the orchestrator, not by any agent's report:

1. `rateguard`'s existing suite passes unchanged — no test edited, no test deleted;
2. an **external** suite the implementer never sees passes: monotone refill, `retry_after` is `0.0`
   exactly when `allow` would admit, the value decreases as time passes, and burst capacity is
   respected at the boundary;
3. `retry_after` performs no I/O and sleeps for nothing;
4. `pb_freeze.py compare` still derives the accepted candidate from the project, so the
   implementation did not silently change what was frozen.

## The chain, with the exact commands

Each step names who decides, how that authority is established mechanically, and what artifact it
leaves. `RUN` is the run root, `LEDGER` the accepted-artifact ledger, `GRAPH` the declared change
graph, `FREEZES` the content-addressed freeze directory.

### One — accepted intent, held by the human

`intent.md`, human-authored. Authority is ownership: nothing derives it, and no agent may author it.
Recorded so later steps can depend on it:

```bash
python3 scripts/pb_ledger.py record --run-root "$RUN" --phase-id design \
    --task-id RG-intent --artifact intent.md --ledger "$LEDGER"
```

### Two — specification, then a fresh challenge (`dsd-spec-author`, then `dsd-spec-reflector`)

The author gets the intent and the project, and nothing else — no reviewer output, no
implementation. The reflector gets the specification and the intent, and **not** the author's
reasoning or session:

```bash
python3 scripts/dsd_attempt.py launch --run-root "$RUN" --phase-id design \
    --task-id RG-spec --role spec-author --timeout 900
python3 scripts/dsd_attempt.py gate  --run-root "$RUN" --phase-id design --task-id RG-spec
```

The reflector's contract declares its purpose, which is what makes the review checkable:

```
## Review purpose
- specification-reflection
```

`_review_purpose` then guarantees one thing and no more: the declared purpose was reviewed by a role
authorized for it. Whether the reflection was any good stays semantic, and stays the human's to
judge.

**Decision: the human accepts or rejects the specification**, having read the challenge. A
reflector that reports no defect does not accept anything.

### Three — ledger and dependency validation, mechanical

```bash
python3 scripts/pb_ledger.py record --run-root "$RUN" --phase-id design \
    --task-id RG-spec --artifact spec.md --depends-on intent.md --ledger "$LEDGER"
python3 scripts/pb_ledger.py validate --ledger "$LEDGER" --project-root "$PROJECT"
python3 scripts/pb_graph.py validate --graph "$GRAPH" --ledger "$LEDGER" \
    --project-root "$PROJECT"
```

`GRAPH` declares which artifacts this change consists of. **Choosing that set is a human decision**
and is listed as such below.

### Four — candidate freeze, mechanical

```bash
python3 scripts/pb_freeze.py create --graph "$GRAPH" --ledger "$LEDGER" \
    --project-root "$PROJECT" --into "$FREEZES"
```

Output: the candidate identity `C1`. Members are exactly the graph's declared artifacts.

### Five — aggregate consistency acceptance (`dsd-spec-reflector`, purpose `consistency-reflection`)

A mechanically satisfied graph of individually reflected artifacts is not the same as a coherent
whole, which is the entire reason this step exists. The reflector sees the frozen members together
and is asked whether they cohere.

```
## Review purpose
- consistency-reflection
```

**Decision: the human accepts the aggregate.** Then, and only then:

```bash
python3 scripts/pb_consistency.py record --run-root "$RUN" --phase-id design \
    --task-id RG-consistency --freeze "$FREEZES/<C1>.json" --into "$CONSISTENCY"
```

### Six — the fresh-context handoff, a deliberate discontinuity

**Here, between consistency acceptance and implementation.** The first orchestrator stops and writes
nothing but a pointer: the run root, the ledger, the graph, the freeze directory, the consistency
directory.

A second orchestrator, with no transcript and no memory of the above, must work out unaided: which
candidate is current, that it has been challenged and accepted, and what the implementer must
therefore be bound to. The commands that must suffice:

```bash
# which candidate does the project currently produce, and is it the accepted one?
python3 scripts/pb_freeze.py compare "$FREEZES/<current>.json" --graph "$GRAPH" \
    --ledger "$LEDGER" --project-root "$PROJECT"
# what does that freeze say about itself, from the file alone?
python3 scripts/pb_freeze.py validate "$FREEZES/<current>.json"
# has it been challenged and accepted as an aggregate?
python3 scripts/pb_consistency.py status --into "$CONSISTENCY" --candidate "<current>"
# and is the declared graph still satisfied by accepted records?
python3 scripts/pb_graph.py validate --graph "$GRAPH" --ledger "$LEDGER" \
    --project-root "$PROJECT"
```

This is the point chosen because it is where resumption is most likely to go wrong: an orchestrator
that guesses the candidate binds the implementer to the wrong thing, and the mechanical gate in the
next step is what catches it. **What the second orchestrator cannot derive is an observation of the
demonstration**, and is recorded as one.

### Seven — candidate-bound implementation, then a fresh review

The implementer's contract binds the candidate:

```
## Proofbound candidate
- <C1>
```

Because the whole contract file is hashed and bound at launch, naming the candidate here is what
makes a review of one candidate unusable for another.

```bash
python3 scripts/dsd_attempt.py launch --run-root "$RUN" --phase-id build \
    --task-id RG-impl --role implementer --auto-flag=--auto --timeout 900
python3 scripts/dsd_attempt.py gate  --run-root "$RUN" --phase-id build --task-id RG-impl
```

Then a **fresh** `dsd-reviewer`, purpose `implementation-review`, bound to the same candidate, given
the specification and the diff — not the implementer's session, and not its self-assessment.

### Eight — acceptance, held by the human

The orchestrator runs the four acceptance criteria above. **The human accepts**, and the
implementation is recorded as depending on the specification:

```bash
python3 scripts/pb_ledger.py record --run-root "$RUN" --phase-id build \
    --task-id RG-impl --artifact rateguard/ --depends-on spec.md --ledger "$LEDGER"
```

A model-generated `PASS` authorizes nothing. No step may be skipped to reach the end: if a gate
refuses, the run stops and the refusal is the finding.

## Product behaviour, checked independently of any agent

The external suite of the second acceptance criterion is written **before** the implementer runs, kept outside the
project tree and outside the worker's evidence surface, and executed by the orchestrator afterwards.
It is the only correctness signal that does not pass through an agent. The implementer's own report,
the reviewer's verdict and the project's own suite are all evidence about the *workflow*; only the
external suite is evidence about the *software*.

## Deterministic refusal checks — separate, unpaid, and not part of the live run

Two mechanical refusals must be demonstrated, and neither needs a model. They run as ordinary tests
with fake workers, kept apart from the live semantic evaluation so a refusal is never confused with
a judgement:

1. **Stale review.** Accept a review bound to `C1`, then change a declared member so the project
   derives `C2`. Acceptance must refuse: the accepted review is not a review of the current
   candidate.
2. **Wrong-candidate binding.** Launch an implementation contract naming `C2` while the accepted
   review is bound to `C1`. The gate must refuse with *source gate is not bound to
   `task.current_contract`*.

Both are existing guarantees; the point is to show them firing in this workflow's shape.

## Observations to record, separated by kind

The value of the run is in this separation, so it is planned rather than improvised:

| kind | what is recorded |
|---|---|
| **mechanical enforcement** | every gate that fired, what it checked, and what it refused. Derived, not judged. |
| **semantic judgement** | what each reflector and reviewer actually said, and whether the human agreed. Kept as prose, never scored. |
| **manual orchestration** | every command a person had to choose, every decision no artifact determined, and everything the second orchestrator could not derive. |

The third column is the deliverable. A workflow that composes only because a human silently supplied
the missing link has a gap, and this is where it becomes visible.

## Manual decisions this design requires — stated honestly

Not incidental, and not to be automated by this demonstration:

1. authoring and accepting the intent;
2. choosing the change graph's declared artifact set;
3. accepting or rejecting the specification after reading the challenge;
4. accepting the aggregate consistency reflection;
5. accepting the implementation after reading the review;
6. deciding, if a reflector or reviewer raises something, whether it is a defect.

Every one is a semantic decision held by the human parent. The mechanisms establish that an
authorized role reviewed a declared purpose against an exact candidate; none of them establishes
that the answer was right.

## Budget, stopping conditions, retained evidence

- **Five paid agent runs**: spec-author, specification reflector, consistency reflector, implementer,
  implementation reviewer. Frozen executor, `deepseek/deepseek-v4-flash` at `high`.
- **Aggregate limit $0.40, reserve $0.10**, checked before each launch. At observed rates five
  bounded runs sit near $0.10; the headroom is for the implementer, which does real work.
- **Per-attempt deadline 900 s**, passed to `dsd_attempt.py launch`. Worth noting because it
  differs from the MLR path: these runs are *not* inside a semantic view, so the monitor that
  owns the worker can signal it and `run_worker`'s own deadline is the one that takes effect.
  Inside a view every signal is refused and only the controller can act. The field check
  covered the second arrangement; this demonstration exercises the first, and that is a
  difference to record rather than an equivalence to assume.
- **Stop** on: any gate refusing outside the two deliberate checks; a role producing no report; the
  reserve refusing a launch; or two failed attempts at any one step. No paid retries beyond the
  bounded attempts a step already allows.
- **A reviewer finding a defect is a legitimate outcome**, recorded and stopped on. The design must
  not be adjusted to produce a clean review, and a reviewer is never asked to find something. If
  whether reviewers *can* detect defects becomes the question, that is a different study and needs
  its own design.
- **Retained**: the run tree, the ledger, the graph, every freeze and consistency record, each
  role's contract and report, the gates, the external suite's output, and the three-column
  observation log. Credentials never; raw sessions outside the repository.

## Deliberately out of scope

No new orchestrator — the second orchestrator is a person running the commands above. No durable
implementation provenance beyond what the ledger already records. No promotion of fixture
mechanisms into core policy. No MLR fixture, and no relationship to `q1` or `b1`.
