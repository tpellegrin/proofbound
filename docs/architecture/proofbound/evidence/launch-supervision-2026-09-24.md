# Launch supervision — 2026-09-24

**Repaired and rehearsed, credential-free.** A supervised launch now outlives the session that
started it, and an interrupted launch has a supported recovery path. Two defects were reproduced
through the real front door before the repair and are closed by it. This milestone made no
provider request and started no metered coordinator session.

## The failure, precisely

The first-use handoff session ran `continue` as a background command and then exited. The retained
records are:
- the handoff commands and session outputs;
- the interaction log;
- the process listing taken at 12:35;
- the restored-watch record;
- the ledger and its receipts.

From those, and from the code:

| Control | Owned by, before this repair | After the caller exited |
|---|---|---|
| Worker (`opencode`) | the in-boundary monitor `run_worker.py`, in its own session | **ran on** |
| Terminal record, deadline *detection* | the same monitor | **ran on**; could not signal the worker, because the boundary denies `signal` |
| Containment: request cap, incomplete responses, derived spend | the host controller, i.e. the `continue` process | **gone** |
| Host deadline and teardown | the host controller | **gone** |
| Post-exit ownership sweep | the host controller | **gone** |
| Ledger classification and receipts | the host controller | **gone**; the slot stayed `unresolved` |
| In-boundary launcher and `wait_worker` | the controller's process group | **gone** |

- **What still held.** The ledger's rule that an unclassified reservation refuses the next launch,
  and the workflow's refusal to relaunch an attempt without a terminal record. No duplicate worker
  could start.
- **What did not hold.** Nothing could enforce the deadline or containment until 12:36:08, when
  the watch was restored by hand. That watch then held containment, but not the deadline. The
  gap was 93 to 111 s: the controller's death time was never recorded.

**The worker finished before its deadline** (133 s against 900). **No surviving controller could
have enforced the deadline if it had not.**

**Reproduced before the repair**, on `ccf53f3`, credential-free. The rig used the DeepSeek
profile with a dummy key, the provider redirected to a scripted loopback endpoint, the real pinned
executor, and the real boundary. Killing the caller meant SIGKILL to its whole process group, as a
coordinator host's exit does.

| | Result |
|---|---|
| R1: caller killed while the worker ran | Monitor and worker survived under init; slot `unresolved`. After the worker ended, the next launch was refused as "launch intent is unreconciled", with no supported way to reconcile it |
| R2: caller killed while the worker stalled; deadline 15 s | Monitor's SIGTERM and SIGKILL refused (`EPERM`); terminal `timeout` with `worker_stopped: false`; **worker still running at 75 s** |
| R3: caller alive, same stall, host margin larger than the monitor's give-up time (as in production) | Monitor gave up at 37 s; the host's post-exit sweep found nothing; launch reported `timeout`, not unresolved; **worker still running at 75 s** |

R3 is a second defect, and it does not depend on the caller. The real executor ran as
`opencode run …`. Once its monitor had exited, nothing in its command line tied it to the run, so
the host's ownership test — which never trusts a bare pid — could not recognise it. Every earlier
real-executor attempt ended inside its deadline, so none of them left a worker behind.

**Session 2's wrapper** (`continue-and-wait.sh`, retained in the first-use evidence):
- **What it did.** It started `continue` in its own process session, so the host controller would
  have survived the caller.
- **Not tested against an exit.** Session 2 never exited mid-launch, so that survival was never
  exercised.
- **Not sufficient:**
  - Its single-flight check trusted a bare pid.
  - Two concurrent calls could both pass that check.
  - `status` knew nothing of it.
  - It could not recover a lost controller.
  - It did nothing about R3.

  It was an operator workaround. The repair replaces it.

**The manual recovery, and what supported each step:**
- **Restored containment.** It used the run's own limits, the implementer session's first part as
  its baseline, and the spend room at admission. That figure came from the accounting read just
  before the launch.
- **The post-exit sweep.** Production `stop_attempt` found nothing owned running.
- **Classification.** It rested on the attempt's immutable reservation and its `completed`
  terminal record. The launcher's return code was never observed and was recorded as such.
- **A receipt** recorded all of the above.

## The repair

**Required behaviour.** Once a launch is admitted and reserved, the calling session's exit must not
leave work running without its declared supervision.

**Design: a run-owned supervisor** (`scripts/_supervision.py`):
- **`continue` starts a supervisor and waits for it.** The supervisor runs in its own process
  session. It admits, reserves, launches, watches, tears down, sweeps and classifies, using the
  same code as before (`_supervised_launch._launch`).
- **Callers only wait.** If a caller exits, the supervisor continues. A later `continue`, from any
  caller, waits for the same supervisor and starts nothing. `status` reports `running`.
- **Identity is never a bare pid.** A supervisor is identified by a token in its own command line
  and by its process start time. A short run lock (`flock`) decides who starts and who waits, so
  concurrent callers start one supervisor.
- **What it records for recovery.** The supervisor records its stage, the reserved slot, the host
  deadline as wall-clock time, and the containment baseline and spend room.
- **The worker is recognisable without its monitor.** `run_worker.py` starts the executor by its
  resolved path. In a supervised run that path lies in the run's runtime directory, so the host's
  ownership test recognises the worker even after the monitor has exited. This closes R3.

**Recovery: `pb_workflow.py recover --run R`.** Without `--apply` it is read-only. It names one
state from retained evidence:
- the ledger;
- unclaimed attempt reservations;
- attempt and terminal records;
- the process ownership scan;
- the supervision record;
- accounting.

`--apply` makes exactly the change that state names, under the run lock:

| State | `--apply` |
|---|---|
| `supervised` | nothing: `continue` waits for it |
| `worker-running-unsupervised` | starts an adopting supervisor. It holds the recorded deadline (else the attempt's own start plus deadline and margin), containment from the recorded baseline, teardown, the sweep and classification |
| `terminal-unrecorded` | sweep, then classify from the reservation and terminal record |
| `no-terminal` | classify as executor-reached with the outcome **unknown**; the run stays blocked on the attempt |
| `pre-executor` | classify as a pre-executor failure (no reservation exists, and nothing owned is running) |
| `supervisor-ended` | archive the record |
| `clear` | nothing |
| `contradictory` or `unknown` | **nothing**; preserve the run and ask the owner |

Recovery never:
- launches, retries or accepts;
- invents an outcome or a cost;
- signals a process whose ownership is not corroborated.

A second `--apply` reports `clear`. Historical runs keep their recorded semantics: `recover` reads
any run, and nothing is backfilled.

**Limits.**
- **A host restart ends the attempt with the host.** `recover` then records what the attempt left.
- **A supervisor that is alive but hung** is reported as `running`.
- **An adopted deadline runs on wall-clock time.** A host suspend counts against it.
- **`ps` must be readable.** Without it, the state is `unknown` and nothing changes.
- **One fault-injection variable exists.** `PB_TEST_SUPERVISOR_FAULT` is for the regression suite
  only and does nothing when unset.

## Verified

| | Result |
|---|---|
| R1 after | The supervisor survived the caller and classified the slot itself; `status` gave `gate`; the next launch proceeded |
| R2 after | Nothing running at 75 s; the attempt was finalized with no caller |
| R3 after | The host confirmed the orphaned worker stopped; nothing running |

`tests/test_supervision.py` contains 16 tests on macOS: 14 use the real boundary with a stand-in
worker, and 2 use the real pinned executor. They cover:
- a killed caller;
- a new caller that waits;
- three concurrent callers, which start one supervisor and one slot;
- a stalled worker whose caller is gone, stopped at the deadline;
- a supervisor killed at each boundary (before reservation, after reservation, while running, and
  after the worker ended but before finalization);
- a missing terminal record, left unknown and blocking;
- a corrupt terminal record, which changes nothing;
- a reused pid, neither trusted nor signalled;
- adoption of a running worker, and of a stalled one stopped at the recorded deadline;
- concurrent recoveries, which adopt once;
- recovery refused while a supervisor runs;
- a second attempt after reconciliation.

**Operator rehearsal.** The real executor ran against a scripted endpoint. The new caller had only
the run path and the operator guide. The raw record is private, in
`~/proofbound-evidence/supervision-rehearsal-2026-09-24/`.

| Interruption | Operator commands after it | Manual edits | Outcome |
|---|---|---|---|
| The calling session ended | `status` (`running`) → `continue` (waited for the same supervisor) → `status` (`gate`) → `continue` | 0 | one slot, `executor-reached`, `completed`; nothing running |
| The supervisor was killed | `status` (`blocked`, names `recover`) → `recover` (`worker-running-unsupervised`) → `recover --apply` (adopted, `completed`) → `recover` (`clear`) → `status` (`gate`) → `continue` | 0 | one slot, `executor-reached`; one `supervision adopted` receipt; nothing running |

This is a process-level rehearsal. The caller was scripted, not a fresh agent.

## Costs of the 2026-09-24 work, kept apart

| Participant | Amount | Basis | Authorization |
|---|---|---|---|
| Worker, qualification continuation | $0.072622 | derived from measured usage at `deepseek-2026-09-23` | the owner's continuation authorization |
| Worker, first use | $0.060347 | the same | the carried-forward first-use authorization |
| Worker, earlier experiment | $0.016342 | the same | its own authorization |
| Headless coordinator session 1 (`c70b739e…`) | $0.6301574 | the Claude Code CLI's own figure, at list price | **no explicit budget** |
| Headless coordinator session 2 (`92bd2f47…`) | $1.5023208 | the same | **no explicit budget** |
| This coordinator's own sessions | not measured | — | — |
| Owner and operator effort | not measured | — | — |

- **The headless sessions.** They were started to satisfy the instruction to exercise a genuinely
  fresh coordinator session. That instruction named no budget for metered coordinator sessions,
  and the worker allowance does not cover them.
- **Actual charges.** Whether either figure was charged depends on the account's plan, which is
  not known.
- **Provider billing.** Neither DeepSeek's nor Anthropic's was observed.

Future live proposals name every metered participant ([E26.4](../evaluation-qualification.md)),
and a first-use preparation records them.

## Is another paid handoff observation needed?

**No.** The repair's claims are about process ownership and lifecycle, which the rehearsal and the
real-executor tests establish without a model making decisions. A paid run would observe an agent
following the operator guide — a different claim, and not needed to establish the repair.

The next product step is one bounded change in a real user repository, under supervised-alpha
conditions. That use will exercise the path. Any need it reveals should be acted on then.
