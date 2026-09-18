# The guarded launch path did not enforce authorization

`pb-handoff-1` ran two live conditions on 2026-09-18. The control condition — an accepted state with
its durable consistency acceptance removed — refused correctly: the coordinator invoked
`pb_execution.py authorize`, received `no-consistency-acceptance`, and stopped. The run report says
plainly what that does and does not support, including this:

> **The guarded launch path does not enforce authorization.** [...] In the control condition the
> guard refused and the ledger would still have admitted a paid worker; only the coordinator's
> judgement stopped it.

This document records the reproduction of that defect, and the verification of its repair. **No
provider was reached at any point.** The executor throughout is the slice's local fake.

## Why an exit code could not be the evidence

The defect's shape is that the launcher *succeeds*. A reproduction that reported "the launch
returned 0" would be reporting the same number a correct refusal-free run returns, and a repair
verified against exit codes could be satisfied by a launcher that crashes. So the question asked of
every run below is **did a worker actually run**, answered from the run tree it leaves behind:

| Evidence | What it means |
| --- | --- |
| `attempts/implementer-1/` exists | the launcher created the attempt |
| `launch-reservation.json` | the slot was durably reserved before the executor was reached |
| `terminal.json` | the worker lifecycle completed |
| `report.md` | the worker wrote its report |
| `project/dispatch.py` | **the project was mutated** |

## The fixture

One minimal mutation of a fully prepared, internally consistent state, built by
`evals/authority_slice/_live.py::prepare` in rehearsal mode: the project, change graph, ledger
records, freeze and consistency acceptance are all seeded by a stand-in, and then the durable
consistency acceptance record — and nothing else — is deleted. The candidate remains derivable, so
nothing but the guard can detect the problem. This is the same mutation `pb-handoff-1`'s control
condition used.

## Reproducing it

`evals/authority_slice/bypass_check.py` builds the fixture, asks the guard, and then attempts the
launch by **every route a coordinator has**. It runs at any revision of the repository it sits in and
exits 0 when the outcome matches what was asked for, so the same file demonstrates the defect and
its repair:

```bash
# at or after the repair — every route must refuse
python3 evals/authority_slice/bypass_check.py

# at the defective revision, in a throwaway worktree
git worktree add /tmp/pb-prerepair 60100b7 --detach
cp evals/authority_slice/bypass_check.py /tmp/pb-prerepair/evals/authority_slice/
cd /tmp/pb-prerepair && python3 evals/authority_slice/bypass_check.py --expect-bypass
```

Both were run on 2026-09-18. The fixture is deterministic: both produced candidate
`b665b146…7c0fad`.

## Reproduction, at `60100b7`

The shipped guard was asked first, and refused:

```json
"step_2_guard": {"exit_code": 1, "authorized": false,
                 "findings": ["no-consistency-acceptance"]}
```

`pb_execution.py admit` did not exist. `dsd_state.py bind-contract` bound the contract without
complaint (`returncode: 0`), and the guarded launch path was then invoked — exactly the sequence the
coordinator protocol described:

```json
"step_3_launch": {"admitted_by_launch_ledger": true, "launcher_returncode": 0,
                  "slot_classification": "executor-reached", "terminal_status": "completed"},
"executor_reached": {"attempt_directory_exists": true, "immutable_launch_reservation": true,
                     "terminal_record": true, "worker_report_written": true,
                     "project_mutated": true},
"bypass_reproduced": true
```

The guard refused this exact contract and the project was modified anyway. Nothing in the run tree
records that a refusal had occurred: a refused run and an honoured one are byte-indistinguishable
apart from the guard's own stdout, which is not retained anywhere the launcher reads.

## Why the obvious repair was rejected

Making the launcher call `pb_execution.py authorize` would have checked *currentness at launch*, and
that contradicts A6.4: a task admitted under `C1` must keep running after engineering intent becomes
`C2`. A launcher that re-derives the current candidate on every attempt would fail a task's review or
repair for a reason that has nothing to do with it, converting immutable task authority into whatever
the project happens to be at that moment. It would also re-run the check three or four times per
task, so a moved project mid-task would produce a half-implemented, unreviewable result.

The repair therefore records the *transition*, and the launcher checks the record — not the world.

## The repair

`pb_execution.py admit` runs A6.3's checks and, only if they pass, binds the contract to its task in
**the same atomic state write**, recording `task.admission`. `dsd_attempt.py preflight-attempt` — the
check that already exists to refuse before any worker starts — refuses candidate-bound execution
whose task carries no admission record matching this contract revision, this candidate and this
project.

Two commands would have reproduced the defect: a printed `authorized: true` is not a transition.

## Verification, at the repaired revision

Every route a coordinator has was attempted against the same fixture.

| Route | At `60100b7` | Repaired |
| --- | --- | --- |
| `pb_execution.py admit` | did not exist | refused, `no-consistency-acceptance`, nothing bound |
| `dsd_state.py bind-contract` | **bound it**, exit 0 | refused: candidate-bound execution cannot be bound directly |
| hand-written state entry, then launch | **executor reached**, `completed` | refused at preflight, `not-admitted`, slot classified `pre-executor-failure` |

```json
"executor_reached": {"attempt_directory": false, "launch_reservation": false,
                     "terminal_record": false, "worker_report": false,
                     "project_mutated": false},
"bypassed": false
```

The third route is the one that decides whether this is enforcement or decoration: the first two
could both be closed while the defect survived intact.

The valid path is unaffected — `admit` returns `provenance: verified`, writes the record, and the
launch reaches the executor — and the full lifecycle (implement, independent review, repair,
re-review, external check, acceptance) completes under **one** admission.

## What this does not establish

That the repair was exercised against a real agent. It was not: this milestone made no provider
calls. `pb-handoff-1`'s control refused because its coordinator chose to, and no later change
converts that into an observation of a mechanism that did not yet exist.

That the bypass was ever exploited. Both `pb-handoff-1` coordinators obeyed the refusal.

That nothing can reach an executor outside this path. `P5` still holds at the outer boundary: an
operator can run an executor directly. What is now closed is the supported launch path.
