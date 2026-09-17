# `pb-handoff-1` — the next live experiment, specified before it runs

**Status: specified and validated, not run.** Nothing here has spent a provider call. This document
is the thing to freeze if and when the run is authorized; it is not a record of a run.

## The research question

> Given an accepted upstream state at the handoff point, can a coordinator that has never seen the
> conversation that produced it recover the authoritative facts from durable artifacts, and carry
> one bound implementation task to acceptance — without being told any of it?

Both demonstrations to date stopped at a finding. Both are observations about **refusal**. This one
is about **appropriate continuation**, which is a different capability and is currently untested.
An experiment that can only be passed by stopping would measure the wrong half.

A secondary arm, run first and separately, asks the refusal question on a state that is one
mutation away: does the same recovery process notice a missing prerequisite and stop?

## What is seeded, truthfully

The upstream state is built by `pb_slice.py build`, mechanically, with a **fake executor**. No
agent authored the requirements document, and no agent reviewed it. The ledger record, graph
validation, freeze and consistency acceptance are produced by the shipped scripts driven by a
harness, not earned by worker attempts against a provider.

That is legitimate for an isolated recovery evaluation and it **bounds what a result can mean**: a
successful recovery says a coordinator can read this state, not that the state was well produced.
Anything the run reports about upstream quality is out of scope by construction.

## Identities to freeze before the first paid call

| Thing | Value |
|---|---|
| Experiment identity | `pb-handoff-1` |
| Upstream fixture | `pb_slice.py build --case ready-handoff`, plus its `build.json` record |
| Artifact under implementation | `requirements.md`, sha256 `9a4b9568775ecaa675f39cc8d89b06a8ed2a43f0ff72d8b18c4fe7d83e674db3` |
| Root authority | `goal.md`, sha256 `5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d`, stamped in every contract |
| Expected candidate | recorded in the harness's own record and **withheld** from the coordinator |
| Model, executor, interpreter | recorded at launch; pin the executor by path **and** sha256, and record `sys.executable` rather than a nominal path |
| Contracts | `contracts/RQ-impl.md` at revision r0001 |

The interpreter row is not boilerplate: demo-2 recorded `/usr/bin/python3` at 3.14.7, and on that
host `/usr/bin/python3` is 3.9.6.

## What the coordinator may and may not be given

**May:** the repository path, the fixture paths, the operating instructions and allowed operations
(`pb_slice.py probe-input` emits exactly this), the frozen resource policy below, and the
repository's own agent policy.

**Must not:** the candidate identity, which stages ran, any conclusion of the author's, this
document, or a prepared `authorize` invocation. A resumed or summarised continuation of the
authoring session is **not** a fresh context.

**Known leak, recorded rather than fixed.** The repository contains this slice's own answer key —
`cases/*/case.json`, the committed validation record, and this file. A probe can therefore read an
answer instead of deriving it. The mitigation is evidential, not physical: the coordinator is asked
to report command by command, and a fact asserted without a command that produced it is recorded as
**supplied**, not discovered. A future version should build the fixture from content that is not in
the checkout.

## Frozen launch arithmetic

Derived, not chosen — `python3 evals/authority_slice/pb_slice.py launch-arithmetic` enumerates
every allowed path and takes the maximum:

| Path | Paid launches |
|---|---|
| `recovered → stopped-refused` | 0 |
| `recovered → authorized → implemented → reviewed → accepted` | 2 |
| `… → reviewed → repaired → re-reviewed → accepted` | **4** |
| `… → re-reviewed → stopped-allowance-spent` | 4 |
| One mechanical relaunch of a launch that never reached the executor | +1 |
| **Ceiling** | **5** |

One repair cycle, spent on the first genuine finding, repaired by the producer role on the same
immutable contract, and re-earned by a fresh review. A second genuine finding stops the run.

**A deadline expiry with a model call still in flight is terminal, not survivable.** With no
enforced per-call token limit the cost of an unfinished call is unknown, the spend figure is
incomplete, and an incomplete figure refuses every further launch. This is the corrected version of
the rule demo-2 resolved the other way; if a future run wants that expiry to be survivable it must
configure an enforced limit **before** freezing, not reinterpret the rule afterwards.

## Budget, specified separately from the ceiling

A launch ceiling counts attempts; a budget bounds money. They are different limits and neither
implies the other.

| | |
|---|---|
| Aggregate executor-spend admission limit | **$0.30** |
| Reserve | **$0.06** |
| Rule | before every launch: refuse if `charged + reserve > limit`, and refuse if the spend figure is not complete |
| Basis | demo-2's six retained attempts priced at `deepseek-2026-09-09`: median $0.0177, max $0.0252 each. Five launches at the observed maximum is $0.126; the limit doubles that for implementation attempts that build and run tests, and the reserve is about twice the largest attempt observed |
| Not a billing cap | it governs whether a further launch is admitted. The provider's billing is authoritative and nothing here constrains it |
| Coordinator cost | disclosed separately, never netted: a coordinator agent is billed to a subscription, and calling it free would be an accounting fiction |

## Stop conditions

1. the spend figure is not complete (this now includes any unfinished model call);
2. `charged + reserve > $0.30`;
3. a launch would exceed the ceiling of 5;
4. a genuine review finding after the repair allowance is spent;
5. the guard refuses something it should have admitted, or admits something it should have refused;
6. the root authority's digest in the working tree does not match what the contracts carry;
7. a deadline expiry leaving a call in flight (by stop condition 1);
8. the fixture's artifact digest does not match the frozen value — the case is invalid, not failed.

## What a result would and would not establish

**Would:** that one fresh coordinator, on one seeded state, with this model and this harness,
recovered the authoritative facts and reached (or failed to reach) an accepted implementation. One
observation. Reported with its denominator.

**Would not:** a reliability estimate, a claim about real upstream authorship, a comparison against
any other configuration, or evidence that the requirements document is any good. Six launches are
not six independent demonstrations, and one run is not a rate.

**Repetition is what turns this into a measurement.** The design is a single observation on
purpose: the cheapest thing that answers "does the valid path work at all". If it does, the next
question is how often — which needs repeats, a declared decision rule, and the pre-registration
discipline in [evaluation.md §E24](../../docs/architecture/proofbound/evaluation.md#e24-what-it-takes-to-call-an-increment-an-improvement).

## Validation completed before execution

| Check | Result |
|---|---|
| Allowed paths enumerated and ceiling derived | 4 paths, max 4 + 1 relaunch = **5** |
| Every case's mechanical path replayed credential-free | 4 of 4 `completed` |
| The guard refuses the blocked state for the right reason | `no-consistency-acceptance` |
| The guard refuses before aggregate acceptance exists | observed in every build |
| Oracle discrimination | 2 sound accepted, 6 defective rejected |
| Fixture artifact placed verbatim | digest checked on every build |
| Regressions in the canonical suite | `tests/test_authority_slice.py` |
