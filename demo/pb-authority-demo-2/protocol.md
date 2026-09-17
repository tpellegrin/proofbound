# pb-authority-demo-2 — frozen execution protocol

Written and committed **before the first paid worker call**. Frozen thereafter: the run either
follows this document or stops, and any departure is recorded as a departure rather than absorbed.

`pb-authority-demo-1` stopped after a real specification finding under its frozen no-repair rule.
That outcome is preserved untouched. This successor exists because the same workflow has never been
carried through implementation, review and acceptance, and has never crossed a genuine
fresh-context handoff. It is a separate demonstration with a separate identity, not a rerun.

## 1. What is being demonstrated

That accepted engineering intent survives, unchanged in substance and checkable in identity, across
eight stages: specification, independent specification challenge, ledger record, dependency
validation, candidate freeze, aggregate consistency acceptance, **a fresh-context handoff**,
candidate-bound implementation, independent implementation review, and acceptance.

The handoff is the point of the exercise. Everything before it is preparation for the question
*can a coordinator that has never seen this conversation recover the authority state from the
repository and act on it correctly?*

## 2. Fixed identities

| Thing | Identity |
| --- | --- |
| Model | `deepseek/deepseek-v4-flash`, variant `high` |
| Executor | `/Users/thiago/.proofbound/executors/opencode-1.18.29-darwin-arm64/opencode`, sha256 `2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669` |
| Interpreter | `/usr/bin/python3` (3.14.7) |
| Repository base | the commit that carries this protocol; recorded in `execution-record.json` |

The executor is deliberately the **same pinned build the predecessor used**, not the newer
`1.18.30` on `PATH`. Holding the executor identical is what makes the two demonstrations
comparable; upgrading it mid-comparison would confound the one variable under test.

Artifact digests — `intent.md`, the fixture tree and source, the fixture's own suite, the external
suite, the private witness, the contracts tree, and this protocol — are produced by
`scaffold.py identities` and recorded in `execution-record.json` before the first paid call.

## 3. Authority, and where it lives

`intent.md` is the accepted parent authority for this demonstration. **It cannot be recorded in the
ledger**: the ledger records project artifacts produced by accepted tasks, and the intent is the
input authority, produced by no task. It is therefore named as an *explicitly identified external
authority*, and its identity is made checkable rather than asserted:

* `intent_sha256` is recorded in `execution-record.json`;
* the same digest is written into the header of every task contract placed in the run root.

A coordinator that has only the repository can recompute the digest of
`demo/pb-authority-demo-2/intent.md` and compare it against the digest the contracts carry. If they
disagree, the intent in the working tree is not the intent the run was launched against, and that
is a stop condition. This is the whole mechanism by which intent identity crosses the handoff.

The intent's seven numbered requirements are frozen at that digest. **A repair may change `spec.md`
or the implementation; it may not change the intent.** If a finding shows the intent itself to be
defective, the run stops and records that: re-freezing parent authority mid-run would dissolve the
thing being demonstrated.

## 4. What the candidate binds, and how narrow that is

The freeze has exactly one member: `spec.md`. So the demonstration does establish
candidate-bound implementation — the implementation contract names one candidate identity and the
authorization guard derives it independently — but it **does not** establish multi-artifact
aggregate coherence. A single-member freeze's consistency acceptance is a judgement about one
artifact against the intent, not a judgement about agreement among several artifacts.

This narrowness is stated here, and `RG-consistency.md` requires the consistency reflector to state
it too, so the limit appears in the run's own evidence and not only in the coordinator's report.

## 5. The five worker roles, and the information each may see

Five paid roles. Every one is a separately launched attempt, visible in the run tree, and none is
the coordinator.

| # | Task | Role | Review purpose | Sees |
| --- | --- | --- | --- | --- |
| 1 | `design/RG-spec` | `spec-author` | — | `intent.md`, the project tree, its contract |
| 2 | `design/RG-spec` | `spec-reflector` | `specification-reflection` | the **same immutable contract** + the author's `report.md` as an exact `--input` |
| 3 | `design/RG-consistency` | `spec-reflector` | `consistency-reflection` | the candidate-bound contract + the frozen members |
| 4 | `build/RG-impl` | `implementer` | — | `spec.md`, `intent.md`, the project, bound to the exact candidate |
| 5 | `build/RG-impl` | `reviewer` | `implementation-review` | the same contract + the implementer's `report.md` as an exact `--input` |

A review is a **later attempt on the same task and the same immutable contract**, never a new task.
That is what makes "the reviewer read exactly the producer's report" mechanically checkable.

No worker, at any stage, sees: the external behavioural suite, the private witness,
`verify_suite.py`, this protocol, any other worker's session, or any coordinator reasoning. The
external suite is withheld at mode `0000` for the duration of every worker run and the withholding
is verified per run — and `scaffold.check_withholding` reports what that measure actually is:
**withholding, not isolation**, because the owner may restore the mode without privilege. These
runs are deliberately outside the semantic view, which is the repository's real isolation
mechanism.

## 6. Accounting scope, and what the $0.40 rule is

* **Aggregate executor-spend admission limit: $0.40. Reserve: $0.10.**
* Before every launch: refuse if `derived + reserve > limit`, and refuse if the spend figure is not
  complete.
* **The $0.40 rule is a launch-admission guard, not a guaranteed provider billing cap.** It decides
  whether a *further* launch is permitted. An attempt already admitted may bill more than the
  headroom that admitted it; the provider's billing is authoritative and nothing here constrains
  it. Any claim in the final report must be phrased as derived spend, not as a proven charge.
* A spend figure is *complete* only when the run tree's launch facts reconcile against the session's
  usage — every launched attempt has a terminal record, every terminal record is `completed`, every
  one carries a session id, and calls started equal calls finished. Otherwise the figure is
  incomplete, the unaccounted part is **unknown and never zero**, and further launches are refused.
* **In scope:** every paid executor call made by any attempt launched under this protocol,
  including repair attempts.
* **Disclosed but not netted against the $0.40:** the coordinating agents themselves. Coordinator 1
  and coordinator 2 are Claude Code sessions billed to a subscription, not to the executor
  provider; coordinator 2 is *separately launched* and its existence, inputs and cost basis are
  disclosed in the final report. Neither makes a provider call except through
  `dsd_attempt.py launch`, which is already counted above.
* **Out of scope, and explicitly not treated as zero:** the unknown charge from the earlier
  accidental real-executor invocation. It stays in its own dated record.

## 7. Launch limits

| Case | Paid attempt launches |
| --- | --- |
| Clean run | 5 |
| + one implementation repair | 7 |
| + one specification repair | 8 |
| Hard ceiling | **8** |

A launch that never reached the executor — transport failure, no session created, no usage — may be
relaunched once for that role slot. That is a **mechanical** relaunch of a failed launch, not a
reroll of a semantic outcome, and it still counts against the ceiling. There is no unplanned
reroll: a semantic result the coordinator dislikes is a result.

Attempt deadline: **900 seconds**. One host timeout without terminal evidence is a non-event and
the gate is re-checked. Two deadline expiries on the same role slot *with* terminal evidence that
the executor was reached is a stop condition.

## 8. The one shared semantic repair cycle

**One repair cycle for the whole run, shared between the specification and the implementation.** It
is spent on whichever genuine finding arrives first. It cannot be spent twice and it cannot be
split.

**Trigger.** A review attempt reports a task-relevant defect, and the coordinator holding parent
authority judges the finding genuine against the frozen intent. Judging is reading the finding and
the artifact; it is not negotiating with the reviewer and not re-prompting for a softer verdict.
A finding judged not genuine is recorded with its reasoning and does not consume the allowance.

**Repairer.** The **producer role on the same task and the same immutable contract** — `spec-author`
for a specification defect, `implementer` for an implementation defect. Never the reviewer that
found it, and never the coordinator. The repair attempt receives the reviewer's `report.md` as an
exact `--input`.

**What the repair invalidates.** This is where the predecessor's plan was silent, and it is not
symmetric. A repair invalidates every downstream judgement that was made about the artifact it
changed, and those judgements must be *re-earned by fresh attempts*, not re-asserted.

*Implementation repair* (`build/RG-impl`):

1. the implementation review that found the defect — a **fresh** `implementation-review` attempt on
   the repaired attempt's report is required;
2. the external behavioural suite and the project's own suite must be rerun against the repaired
   implementation;
3. **not** invalidated: the specification acceptance, the ledger record, the graph validation, the
   candidate freeze, the consistency acceptance, or the launch authorization — none of them
   describes the implementation, and the candidate binds `spec.md` alone (§4).

Cost: 2 launches.

*Specification repair* (`design/RG-spec`) — the upstream case, with a dependency chain:

1. the specification reflection that found the defect → a **fresh** `specification-reflection`
   attempt on the repaired author's report;
2. the **ledger record** of `spec.md` — the recorded artifact digest no longer matches the artifact
   → re-record;
3. the **graph validation** → re-validate;
4. the **candidate freeze** → a new freeze with a **new candidate identity**; the old candidate is
   dead and must not be carried forward;
5. the **aggregate consistency acceptance**, which was recorded against the old candidate → a
   **fresh** `consistency-reflection` attempt and a new `pb_consistency record` against the new
   freeze;
6. any **launch authorization** already obtained → re-authorize against the new candidate.

Cost: 3 launches (fresh author, fresh reflector, fresh consistency reflector) plus the mechanical
re-derivation in steps 2–4 and 6.

**After the allowance is spent**, a further genuine finding stops the run and is recorded as a
partial demonstration — exactly as the predecessor's no-repair rule produced its outcome. A second
repair cycle is not available for any reason.

**How coordinator 2 learns whether the allowance is still available** without being told: the
allowance is spent if and only if the run tree contains more than one producer attempt on any
single task. That is derivable from `state.json` and the attempts directory. It is a mechanical
derivation from repository facts, not a conclusion handed across the handoff.

## 9. Stop conditions

Finite and enumerated. Any one of these ends the run; the coordinator records it and does not
improvise around it.

1. The spend figure is not complete — unknown expenditure blocks further launches.
2. `derived + reserve > $0.40`.
3. A launch would exceed the ceiling of 8.
4. A genuine review finding arrives after the repair allowance is spent.
5. Two deadline expiries on one role slot with terminal evidence the executor was reached.
6. A guard refuses something it should have admitted, or admits something it should have refused.
7. The project's own suite or the external suite fails against an accepted implementation — the
   acceptance is withdrawn, and if the repair allowance is spent, the run stops.
8. The intent's digest in the working tree does not match the digest the contracts carry.
9. A finding shows the frozen intent itself to be defective.
10. **A genuine fresh context is unavailable at the handoff** — report that capability limit; do not
    simulate one.

## 10. The handoff

**Point.** Immediately after `pb_consistency record` succeeds, and **before** any call to
`pb_execution.py authorize`. Coordinator 1 then stops. A resumed, compacted or summarised
continuation of coordinator 1's conversation is **not** a fresh context and does not satisfy this.

**Coordinator 2 may be given:**

* the repository path and the run-tree locations — run root, ledger, graph, freezes directory,
  consistency directory, session database, the demo directory;
* standing operational instructions: the repository's agent policy, the command surface, how to
  launch and gate an attempt, the withholding requirement;
* this frozen resource policy — limit, reserve, ceiling, deadline, the repair rule, the stop
  conditions.

**Coordinator 2 must not be given:**

* the candidate identity;
* any account of which stages ran or succeeded;
* coordinator 1's conclusions, judgements, or findings;
* coordinator 1's conversation, in whole, in summary, or in compacted form;
* a prepared `pb_execution.py authorize` invocation that contains the answer.

**Coordinator 2 must independently recover, from repository facts:**

1. the candidate identity;
2. that the candidate has a durable consistency acceptance;
3. the provenance state of the recorded artifact;
4. where the parent intent's authority lives and that its identity still checks;
5. the remaining budget and whether the repair allowance is spent;
6. what the next action is.

**Before launching implementation it must invoke `pb_execution.py authorize` itself and retain the
result.** A candidate string copied into a contract is a declaration; the guard is the three derived
checks in `pb_execution` — graph and ledger derive exactly that candidate, that candidate has a
durable consistency acceptance, and provenance is not `contradicted`. The predecessor's rehearsal
never exercised it. This one does, in both the clean and the repair path, and verifies that the
guard **refuses** before consistency acceptance exists.

Coordinator 2 then owns: implementation, independent review, the repair if the allowance is
available, and acceptance. It retains its own initial input verbatim and its own evidence, and
discloses any assistance it received.

## 11. Successor runbook

Verified end to end by `rehearse.py` against a credential-free fake executor, on both the clean and
the repair path, before any paid call.

```bash
# 0. preparation (coordinator 1, unpaid)
python3 demo/pb-authority-demo-2/scaffold.py identities
python3 demo/pb-authority-demo-2/verify_suite.py
python3 demo/pb-authority-demo-2/rehearse.py --into <scratch> --path clean
python3 demo/pb-authority-demo-2/rehearse.py --into <scratch> --path repair
python3 demo/pb-authority-demo-2/scaffold.py setup --into <workdir>

# before and after every worker run
python3 demo/pb-authority-demo-2/scaffold.py withhold
python3 demo/pb-authority-demo-2/scaffold.py admit --into <workdir>

# 1-2. specification, then its independent challenge
python3 scripts/dsd_state.py bind-contract --run-root <run> --phase-id design \
    --task-id RG-spec --contract <run>/contracts/RG-spec.md
python3 scripts/dsd_attempt.py launch --run-root <run> --phase-id design --task-id RG-spec \
    --role spec-author --detach
python3 scripts/dsd_attempt.py gate --run-root <run> --phase-id design --task-id RG-spec
python3 scripts/dsd_attempt.py launch --run-root <run> --phase-id design --task-id RG-spec \
    --role spec-reflector --input <author-event>/report.md --detach
python3 scripts/dsd_state.py accept-task --run-root <run> --phase-id design --task-id RG-spec \
    --evidence-gate <reflector-event>/evidence-gate.json

# 3-5. record, validate, freeze
python3 scripts/pb_ledger.py record --run-root <run> --phase-id design --task-id RG-spec \
    --artifact <project>/spec.md --ledger <ledger>
python3 scripts/pb_graph.py validate --graph <graph> --ledger <ledger> --project-root <project>
python3 scripts/pb_freeze.py create --graph <graph> --ledger <ledger> \
    --project-root <project> --into <freezes>

# 6. aggregate consistency (the candidate is written into RG-consistency.md)
python3 scripts/dsd_attempt.py launch --run-root <run> --phase-id design \
    --task-id RG-consistency --role spec-reflector --detach
python3 scripts/pb_consistency.py record --run-root <run> --phase-id design \
    --task-id RG-consistency --freeze <freezes>/<candidate>.json --into <consistency>

# === HANDOFF: coordinator 1 stops here ===

# 7. coordinator 2, from repository facts, exercises the guard and retains the result
python3 scripts/pb_execution.py authorize --graph <graph> --ledger <ledger> \
    --project-root <project> --consistency <consistency> --run-root <run> \
    --contract <run>/contracts/RG-impl.md

# 8-9. implementation and its independent review
python3 scripts/dsd_attempt.py launch --run-root <run> --phase-id build --task-id RG-impl \
    --role implementer --detach
python3 scripts/dsd_attempt.py launch --run-root <run> --phase-id build --task-id RG-impl \
    --role reviewer --input <impl-event>/report.md --detach
python3 scripts/dsd_state.py accept-task --run-root <run> --phase-id build --task-id RG-impl \
    --evidence-gate <reviewer-event>/evidence-gate.json

# 10. the coordinator's own checks, after the suites are released
python3 demo/pb-authority-demo-2/scaffold.py release
python3 demo/pb-authority-demo-2/scaffold.py project-suite --into <workdir>
python3 demo/pb-authority-demo-2/scaffold.py external --into <workdir>
python3 demo/pb-authority-demo-2/scaffold.py spend --into <workdir>
```

## 12. Preparation defects repaired before this run

Named because the predecessor's records are preserved unchanged, so the corrections have to live
here and in the dated successor note rather than by editing history.

* **`scaffold.spend()`** priced whatever usage a session held and called it complete; treated an
  absent database as proof of no expenditure; and priced at report time rather than execution time.
  Now reconciled against the run tree's launch facts, with a regression per defect in
  `tests/test_authority_demo2_accounting.py`.
* **The external suite's boundary blindness.** Its single boundary case used `capacity=1`,
  `refill=4.0`, base `5000.0`, advancing `0.25` — every value dyadic and exactly representable, so
  it passed by luck and missed the very defect its own reflector found. The successor suite sweeps
  non-dyadic rates at six clock bases, always advances by the delay the implementation returned,
  exercises the exceptional case, and is proved **satisfiable** by a private witness and
  **discriminating** against six defective variants including the predecessor's formula.
* **The substring no-I/O test**, which would have flagged a comment containing `open(` and missed
  `getattr(time, "sleep")()`, is replaced by a runtime observation with its limits stated on the
  test itself.
* **The chmod-0000 holdout** is now described as withholding rather than isolation.
* **`rehearse.py`** now invokes `pb_execution.py authorize`, rehearses the repair path, and verifies
  its fake executor by resolved path *and content* in a constructed credential-free environment
  passed explicitly to every call.
