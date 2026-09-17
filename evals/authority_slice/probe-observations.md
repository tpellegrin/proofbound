# Fresh-context recovery probes — what was observed

**2026-09-17. Two observations, not a reliability estimate.** Each case was attempted once, by one
fresh coordinator, on one mechanically seeded state. Two runs are two runs.

## Execution and accounting scope, stated rather than assumed

Each probe was a **Claude Code subagent launched by the author's session**. It began with no
inherited conversation and received only the text below — that is a genuine fresh *context*. It is
not an independent party:

* launched by the author, on the same model family, inside the same session's tooling;
* **billed to the same subscription as the author's session.** Model work is not free, and calling
  a subagent zero-cost would be the same accounting fiction as treating an unmeasured provider call
  as zero. No executor-provider call was made and nothing was charged to the demonstration budget;
* token use is recorded by the harness, not by this repository: 95,635 and 91,894 subagent tokens,
  31 and 27 tool calls, 237 s and 260 s respectively;
* it can read the whole repository, including this slice's own answer key (see the leak below).

This is a **recovery observation**. It is not a completed implementation, not a reliability
estimate, and not evidence that the seeded upstream state was well produced.

## What was supplied, and what was discovered

Supplied, verbatim and identically to both probes (`pb_slice.py probe-input`): the repository path,
six fixture paths, the five facts to establish, the instruction to invoke the guard itself, the
allowed read-only operations, and the instruction to report command by command. Withheld: the
candidate identity, which stages had run, the expected verdict, the author's conclusions, this
file, and any prepared invocation.

| Fact to recover | `ready-handoff` | `blocked-handoff` |
|---|---|---|
| Candidate the project produces | **recovered** — `b665b146…`, via `pb_freeze compare`, reported `equivalent: true` | **recovered** — same identity, via `authorize`'s independently derived `current` |
| Durable consistency acceptance | **recovered** — `state: accepted`, via `pb_consistency status` | **recovered** — `state: absent`, directory empty |
| Provenance of the recorded artifact | **recovered** — `verified`, and checked that dropping `--run-root` turns it to `unavailable`, so `verified` is earned | **recovered** — `verified`, and separated from the *consistency* record's `unavailable` in the authorize output |
| Root authority and its identity check | **recovered** — recomputed `goal.md` to `5c784039…`, matched it against all three contracts, and noted no tool does this for you | **recovered** — same, against all three contracts |
| Next permitted action | **recovered** — launch `RQ-impl`'s implementer, then its independent review | **recovered** — record the durable consistency acceptance; refused to launch implementation |
| Guard invoked, output retained | **yes** — `authorized: true` | **yes** — `authorized: false`, `no-consistency-acceptance` |
| Stopped at the refusal | n/a | **yes**, explicitly: "a refusal is the answer" |

Both went beyond the five questions in ways worth recording. The ready probe derived, by reading
`_freeze.py` and `_execution.py` rather than by running anything, that recording `dispatch.py` will
change the candidate and that the current authorization will not carry over — and labelled that as
read, not run. It also noticed that the accepted `requirements.md` is **untracked in git**, existing
only as working-tree bytes. The blocked probe verified every mechanical precondition of the
`pb_consistency record` command it recommended, then declined to run it because recording asserts a
parent's acceptance and writing was not permitted.

## What the probes found that the author had not

**Both, independently: the fixture's consistency attempt answered the wrong question.** The fake
worker branched on `role` only, so the `consistency-reflection` attempt emitted the
`proposal-reflection` text byte for byte — identical sha256 on both reports. Its contract's AC-002
(state the single-member narrowness) was unmet, AC-001 arguably so, and the acceptance was recorded
and verified anyway, because an integrity gate never reads a report body.

That is a defect in this harness, and it is also the sharpest available demonstration of a boundary
the architecture already states: a clean gate means *safe to interpret*, never *the question was
answered*. Both probes drew exactly that conclusion unprompted.

**Repaired**, after the probes and therefore after the reports above were written: the fake now
reads the task contract the prompt hands it and branches on the **declared review purpose**, which
is what a real worker is given. Branching on the purpose is the worker doing its job; branching on
the task's name would be the fixture answering its own question. The consistency attempt now judges
joint coherence and states its narrowness, with a regression in `tests/test_authority_slice.py`.
The probe reports describe the **pre-repair** fixture.

## The leak, disclosed by the probe that used it

The blocked probe read `evals/authority_slice/README.md` and `pb_slice.py`, which describe this
exact fixture and its expected refusal, and it said so unprompted — adding that it had reached the
finding from the run tree first, and that the documents could not settle the one question it could
not answer (whether the consistency record was deleted or never written).

So the repository is an answer key for its own recovery cases. The mitigation here is evidential
rather than physical: a fact asserted without a command that produced it is recorded as supplied.
For a live experiment that is not enough, and
[`next-live-experiment.md`](next-live-experiment.md) records it as a known limitation to fix by
building the fixture from content that is not in the checkout.

## What these observations do not establish

* **Not a reliability estimate.** One attempt per case. The denominator is 1.
* **Not evidence about upstream quality.** The accepted state was seeded mechanically by this
  harness with a fake executor; no agent authored or reviewed the requirements document.
* **Not the live experiment.** Both probes were read-only and launched no worker. Whether a fresh
  coordinator can carry an implementation through to acceptance remains **not observed**.
* **Not independent of this repository's documentation.** Both probes read repository files
  describing the fixture, one of them the answer.
