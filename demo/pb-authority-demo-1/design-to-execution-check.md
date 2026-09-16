# `pb-authority-demo-1` — design-to-execution check

**2026-09-16, before the first paid call.** The committed design
([`authority-workflow-demonstration.md`](../../docs/architecture/proofbound/evidence/authority-workflow-demonstration.md))
describes a run. It did not ship the things the run needs, and three of its statements were too
loose to execute against. This records what was checked, what was built, and what changed — so that
none of it happens silently once money is being spent.

Nothing here makes the task harder or more novel than designed. The change is still `retry_after`
on a token-bucket limiter.

## The seven questions

### One — what are `retry_after`'s externally observable semantics?

As designed: *"returns the seconds until the next token would be available — `0.0` when a call
would be admitted."* That is not enough to implement against or to test. It says nothing about
whether the query consumes a token, what happens at the exact refill boundary, or what an unseen
key answers — and the design's own external suite asserts all three.

Now specified in [`intent.md`](intent.md) as six numbered observable requirements: the answer's
meaning and `0.0` condition; that it is **query-only** and changes no later answer; that it agrees
with `allow` at the same instant; that it never increases while the clock advances; that an unseen
key answers `0.0`; and that `allow` keeps exactly its current meaning with the existing suite
passing unedited. Plus: the constructor, per-key independence, burst allowance, refill rate and the
injectable clock are unchanged, and the query performs no I/O and no sleeping.

### Two — is extracting the refill arithmetic a requirement, advice, or an expectation?

As designed it reads like a requirement (*"has to be factored out"*) while none of the four
acceptance criteria checks for it. That is the worst of both: an implementer could be failed for
something never tested, or pass while ignoring something stated as mandatory.

**Resolved as advice, explicitly.** `intent.md` has a section saying so in terms, and saying that
nothing will be rejected for factoring the arithmetic differently or not at all.

### Three — does every hidden check follow from requirements the agents have?

It does now. Each test in
[`external-suite/test_retry_after_external.py`](external-suite/test_retry_after_external.py) names
the numbered intent point it tests, and the file says it asserts nothing an implementer could not
have derived from the intent it was given. Before this pass, at least three assertions —
query-only, boundary, unseen key — had no basis in any disclosed requirement.

### Four — does the suite permit legitimate alternative implementations?

**Checked, not assumed.** The suite was run against two implementations that differ exactly on the
advisory point: one sharing the refill arithmetic between the two methods, one deliberately
duplicating it. Both pass all 11 external tests and all 5 of the project's own. The only structural
assertion in the suite is the no-I/O, no-sleep constraint, which the intent states outright.

### Five — are the external suite and reference implementation unreachable from the workers?

Not by isolation: these runs are deliberately outside a semantic view, so a worker with `--auto`
and a shell shares the filesystem. Two things are done instead.

- The suite and the reference live **outside the working project**, are never copied into it, and
  are named in no contract.
- During every worker run the whole `external-suite/` tree is set to mode `0000`. Verified on this
  host: the owner is denied (`PermissionError`, `errno 13`, uid 501 — not root), so this is real
  permission enforcement and not merely non-disclosure.

Stated plainly as a limitation: this is a filesystem permission, not a sandbox. A worker that
escalated privileges, or a mode restored early by mistake, would defeat it. The lock is applied and
verified per run, and the verification is retained.

### Six — are five paid runs enough, and what are the repair and retry limits?

Five is exactly the declared path with **no repair cycle**: spec-author, specification reflector,
consistency reflector, implementer, implementation reviewer. So:

- **at most two attempts per step**, which is what the attempt model already allows; a second
  attempt spends budget and is counted;
- **no third attempt, and no repair-and-re-review cycle.** If the implementation reviewer finds a
  defect, that is a legitimate outcome: it is recorded and the run stops. The demonstration is of
  the workflow, not of reaching acceptance;
- **aggregate $0.40, reserve $0.10**, the design's rule: before each launch, refuse if derived
  spend plus the reserve would exceed the limit;
- **unknown spend blocks further launches.** If any attempt reached the executor without recording
  usage, remaining budget cannot be established and no further paid launch is permitted. This is
  the rule the b1 spend work established, applied here.
- The lifecycle field check's own unknown charge stays in its own record. It is **not** counted
  against this demonstration and **not** treated as zero.

### Seven — who accepts, and on what authority?

The design assigns every acceptance to *the human*. This milestone's instruction assigns
parent-level decisions for this disposable demonstration to the coordinating agent. That is a real
difference and is recorded as deviation **D1** below rather than absorbed.

Acceptance is never inferred. It is performed with
`dsd_state.py accept-task --evidence-gate <gate>`, and for a mutating contract that gate must be
the **fresh reviewer's**, not the implementer's. So the mechanism binds acceptance to an
independent review of the exact candidate; a passing test suite, a matching hash and a model
writing `PASS` authorize nothing on their own.

## Deviations from the committed design

| | what | why |
|---|---|---|
| **D1** | Parent-level acceptance decisions are made by the coordinating agent, not a human. | Authorized explicitly by this milestone's instruction for this disposable demonstration. Scoped to it: no normative architecture changes, and no explicitly required human decision elsewhere is substituted. |
| **D2** | The fixture, the project's suite, the intent, the external suite, the reference implementation and the scaffold script did not exist; they are created and committed before the first paid call. | The design specified a run without shipping what it runs on. |
| **D3** | `intent.md` discloses considerably more than the design's one-line description of `retry_after`. | Required by question three. No accepted meaning was changed, because nothing had been accepted: this *is* the authoring of the intent the design said a human would author. |
| **D4** | External-suite inaccessibility is permission-enforced rather than sandbox-isolated. | These runs are outside a semantic view by design. Recorded as a verification limit. |

## Fixture identities

Recorded here so the run report can cite them, and so a later reader can tell whether the
demonstration's inputs are the ones reviewed.

Digests are produced by `scaffold.py identities` and written into the run record at execution
time; they are not transcribed here, where they would rot.

## What was verified mechanically, before paying anything

| check | result |
|---|---|
| the project's own suite on the initial fixture | 5 tests, pass |
| the external suite on the initial fixture | 11 tests, **fails** — it discriminates |
| the external suite against a shared-arithmetic implementation | 11 tests, pass — satisfiable |
| the external suite against a duplicated-arithmetic implementation | 11 tests, pass — permits alternatives |
| the project's own suite against both implementations, unedited | 5 tests, pass |
| `chmod 0000` denies the owner on this host | `PermissionError`, errno 13, uid 501 |
