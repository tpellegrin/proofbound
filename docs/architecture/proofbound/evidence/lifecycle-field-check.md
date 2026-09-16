# `pb-lifecycle-field-check-1` — protocol

**2026-09-16, written before execution.** An engineering validation of the repaired attempt
lifecycle, committed before any paid call so that what it would accept was fixed in advance.

**This is not an experiment and produces no treatment sample.** It has its own identity precisely so
it cannot be mistaken for one: no preregistration, no slot, no measurand, no record under
`evals/results/`, and no relationship to `q1` or `b1`. Those two are closed. What is under test here
is a process-lifecycle mechanism, and the only questions are operational.

## Why a field check at all

The attempt-deadline repair (`ff650ff`, audited in
[`MLR-eventbus-b1-timeout-audit.md`](../../../../evals/craft/modularity-local-reasoning/MLR-eventbus-b1-timeout-audit.md))
is covered by 1,100 deterministic tests that drive the real launcher with fake executors. What none
of them establishes is behaviour against a **real executor holding a real provider connection**,
because the condition the deadline exists for has never been observed: the one time it looked as
though it had, the host was asleep.

So the claim to be established is narrow and stated now, before the evidence exists:

> Under the conditions tested, the controller's deadline expires, the processes this attempt owns —
> including a real executor and a real tool subprocess it started — are terminated, their absence
> is observed, and the attempt is recorded as timed out without becoming eligible for another
> trajectory.

A pass establishes **operation under the tested conditions**. It does not establish universal
process containment, a reliability rate, that provider-side work was cancelled, or that any billing
was avoided.

## What is being exercised, and what is not

The two trials run through `_mlr_boundary.run_bounded_attempt`, which is the repaired controller
path: it owns the monotonic deadline, and on expiry it calls `_stop_attempt` — the ownership scan,
the signalling, and the liveness sweep that were rewritten three times under review.

`run_bounded_attempt` stages its workspace from an MLR fixture, and there is no third fixture to
stage from. **Fixture B's `contract` arm is therefore used as a disposable workspace, with a task of
this protocol's own.** Nothing about b1 is re-run or re-measured: the task the worker receives is
not the MLR task, no slot is consumed, no result record is written, and the grading step that runs
afterwards is fixture B's oracle applied to work that was never asked to satisfy it — its verdict is
meaningless here and is ignored. The workspace is scaffolding, not a fixture under study.

Not exercised, and not claimed: the in-view monitor's own deadline (it cannot act — every signal
inside the view is refused with `EPERM`), suspend/resume behaviour, any platform but this one, and
recovery from a `SIGKILL`ed controller.

## Configuration, fixed now

| | |
|---|---|
| identity | `pb-lifecycle-field-check-1` |
| executor | the frozen build, `~/.proofbound/executors/opencode-1.18.29-darwin-arm64/opencode`, SHA-256 `2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669`, verified by content at launch |
| provider · model | `deepseek` · `deepseek/deepseek-v4-flash`, variant `high` — the qualified configuration |
| interpreter | `/usr/bin/python3` (CPython 3.9.6), as the qualified stack records |
| workspace | fixture B `contract` arm, disposable scaffolding — see *What is being exercised* |
| credential | provider auth file staged into the view's constructed home, destroyed with the view |
| runner | `evals/pb_lifecycle_field_check.py`, committed before execution |

## The two trials

Exactly two paid trials. No others, and no paid retries.

### Trial A — normal completion inside the deadline

A trivial task: create one small file with fixed content and stop. Deadline **300 s**, generous by
design; the point is that an ordinary short attempt is unaffected by the repair.

*Expected:* `validity: valid`, `timed_out: false`, extraction returns a workspace and a session, the
view is destroyed, no owned process survives, and a cost is derived so spend is complete.

### Trial B — a controlled stall that outlives the deadline

The task instructs the worker, as an explicit and declared test condition, to run one long-blocking
command in its workspace:

```
/usr/bin/python3 -c "import time; time.sleep(900)"
```

Deadline **90 s**. The blocking mechanism is part of the task, not an induced provider fault and not
a prompt to evade anything: the worker is asked to run a command that does not return, which is the
ordinary shape of a stuck tool call.

*Expected:* the deadline expires while the executor and that child are both alive;
`validity: harness-failure`, `timed_out: true`, `terminal_status: controller-timeout`;
`termination.stopped: true` with `survivors: []`; extraction still returns the workspace.

## Deadline, clocks and limits — declared

- **Start event:** the assignment `attempt_deadline = time.monotonic() + timeout` in
  `run_bounded_attempt`, immediately before the launcher is entered. Everything before it — view
  construction, staging, the hermeticity preflight — is outside the deadline.
- **Clock:** monotonic. It does not advance across host suspend, which is why *Host conditions* requires the host
  to stay awake and requires that to be verified afterwards rather than assumed.
- **Launch limit:** the deadline itself (A 300 s, B 90 s), shared by the `launch` and `gate` legs.
- **Shutdown grace:** `TERMINATION_GRACE_SECONDS = 10 s`, at most twice — once after `SIGTERM`, once
  after `SIGKILL`. Worst-case overrun is therefore about 20 s past the deadline, and a worker that
  traps `SIGTERM` does keep running during the first of those.
- **Extraction:** bounded by the attempt; the timeout branch extracts before returning.
- **Observation:** after each trial, owned-process absence is polled for at most **60 s**.
- **Total wall-clock ceiling for the run:** 15 minutes. Past that, stop and report blocked.

## Evidence that the executor and tool were really active

Reports alone are insufficient, so processes are observed directly. While trial B runs, the runner
samples `/bin/ps` every 250 ms and retains, secret-free:

- the staged executor's own process, matched by its path under the view's tools directory;
- the blocking `time.sleep(900)` child, matched by its command line;
- `attempt.json`'s `worker_pid` and `launcher_pid`;
- a snapshot of every attempt-signature process immediately before and after expiry.

`worker.log` is retained as independent evidence that the executor issued the tool call, and
`terminal.json` for the monitor's own account. Nothing is reconstructed: what is not sampled is
reported as unobserved.

## Host conditions

- The host must be awake for the whole run, on AC power, and **the lid must stay open** — an
  idle-sleep assertion does not prevent clamshell sleep, which is exactly what confounded b1.
- `pmset -g log` is read before and after, and any `Sleep` transition inside the run window makes
  the affected trial **inconclusive** regardless of its other results.
- The host must be otherwise quiet: no test suite and no other Proofbound run, enforced by
  `tests/_host_serial.py` for the suites and by checking for residue before each trial.

## Budget and accounting

- **Aggregate limit $0.20** for this protocol, including any chargeable probe. There are no
  chargeable probes planned: the preflight contacts no provider, and `opencode session list` is
  local.
- Before trial B, if derived spend plus a **$0.05** reserve would exceed the limit, trial B is not
  launched and the check reports blocked.
- Spend is read through `_mlr_series.spend`, so an attempt that reached the executor without
  recording usage is `unpriced` and the total is reported **incomplete** rather than as zero. A
  timed-out attempt is expected to be unpriced, and that is an honest outcome, not a failure.
- **A local timeout is not a billing cap.** Terminating a local process says nothing about work the
  provider has already accepted. No claim is made that spending stopped when the process did.

## Criteria, fixed before the evidence

**Pass** — all of:

1. Trial A completes inside its deadline, extracts, and leaves no owned process alive.
2. Trial B's deadline expires with the executor **and** the blocking child observed alive
   beforehand.
3. Trial B reports `timed_out: true`, `terminal_status: controller-timeout`,
   `termination.stopped: true`, `survivors: []`, under a successful process enumeration.
4. No process outside the attempt's owned set is terminated: the attempt-signature snapshot after
   expiry contains nothing that was running before the trial began.
5. Trial B's disposition survives a record round trip, and a resume offers no further trajectory.
6. Spend is within the limit and its completeness is reported honestly.
7. No host sleep transition occurred during either trial.

**Fail** — any owned process observed alive after the grace under a successful enumeration; any
process outside the owned set terminated; a timed-out attempt that reads as valid or becomes
eligible for a reroll; or spend reported complete when an executor-reached attempt recorded no
usage.

**Blocked** — the executor cannot be verified, the host cannot be kept awake, or the budget reserve
refuses the launch. Nothing paid has happened and nothing is claimed.

**Inconclusive** — trial B's worker finishes or errors before reaching the controlled stall, a
provider failure prevents the tool call, or a sleep transition intrudes. The mechanism is then
untested by this check, which is a limitation and **not** permission to try again: there are no paid
retries in this protocol.

A defect found here is preserved as a failed check. It may be repaired and tested, but not by
changing the implementation between the two trials and calling the combination a pass.

---

# Outcome

**2026-09-16, 15:26:54 → 15:29:08 local (135 s).** Executed at
`09a9350d4a025af6badba963250b9012f7357dde`, the revision this protocol was committed in. Raw record:
[`lifecycle-field-check-evidence.json`](lifecycle-field-check-evidence.json).

**Verdict: pass, at the scope declared above and no wider.**

Executor verified by content before launch — `2f24593f…0669`, the frozen build. Interpreter CPython
3.9.6. No `Sleep`, `Wake` or `DarkWake` transition in the run window ±30 s, checked directly against
`pmset -g log` and not only by the runner's own scan.

## Trial A — normal completion

Wall 42.95 s against a 300 s deadline. `validity: valid`, `timed_out: false`,
`terminal_status: completed`. Extraction returned both the workspace and the session; the view was
destroyed; cost derived at **$0.005745** from real usage (12,202 uncached input tokens, 163,840 cache
reads, 2,899 output) so spend is **complete**. No attempt-shaped process survived and no residue was
left. Fixture B's oracle scored the work `correct: false`, which is meaningless here and ignored: the
worker was never asked to satisfy that oracle.

An ordinary short attempt is unaffected by the repair.

## Trial B — the controlled stall

Wall 90.779 s against a 90 s deadline. `validity: harness-failure`, `timed_out: true`,
`terminal_status: controller-timeout`, `trajectory_began: true`.

**The real executor was doing real work, and the blocking command really was running.** `worker.log`
shows it read `WORKER_RULES.md`, `COMMON.md`, the implementer skill and the task contract, listed the
attempt directory, wrote its report, ran `date -u` (`2026-09-16T18:27:54Z`), then edited the report
to say *"Command launch: about to execute the exact contract command, blocking"* — and the log ends
there, mid-command. Across 287 process samples the runner caught the blocking child itself alive at
18:27:59Z: pid 97817, `python3 -c import time; time.sleep(900)`, in its own process group.

**Termination, observed rather than asserted.** `stopped: true`, `found: 4`, `survivors: []`,
`escalated: false` — `SIGTERM` was enough. The four owned processes, and why each was owned:

| pid | pgid | recognised as |
|---|---|---|
| 97576 | 97576 | `recorded` — the monitor |
| 97578 | 97578 | `recorded` — the executor |
| 97579 | 97182 | `names-the-view` — the `wait_worker` helper, sitting in the *controller's* group |
| 97817 | 97817 | `descends-from-recorded` — the blocking child |

Three of the four ownership tests fired, each on the shape only it reaches. **No collateral
signalling:** group signals went to `97576` and `97578` only — the two corroborated roots, each its
own group leader — and the controller's group `97182` was never signalled as a group. The
`wait_worker` process inside it and the blocking child were signalled individually. Nothing
attempt-shaped was running before the trial began, and nothing was left running after.

Extraction still returned the workspace and session after termination. No cost was derived, so spend
is reported **incomplete** with one `unpriced` attempt — the honest outcome for a stopped
trajectory, not a failure.

**Partial evidence, honestly partial.** `worker_monotonic_seconds`, `worker_wall_seconds` and
`view_destroyed` are `null` for this trial: the controller stopped the monitor before it wrote its
own terminal event, and the timeout branch returns before the view-destruction flag is set. The
residue check independently confirms the view was destroyed. Nothing here is filled in by inference.

## Disposition, reload and no-reroll

Checked afterwards against the real recorded attempt, not a stand-in:

- written to a series record and reloaded, `timed_out`, `terminal_status`, `validity` and the
  termination record all survive, and `execution_stage` still derives `worker-executed`;
- resuming the series **bought no further trajectory in any arrangement**. With the timed-out slot
  first in the frozen order it stops at the preregistration's **interrupted-trajectory** rule — *preserved; resolve
  deliberately, never automatically* — with and without a budget gate, isolating the rule from the budget. With it
  later in the order, the unestablished spend refuses the launch of *every* slot at the **ceiling rule**, reason
  `unpriced-attempt`. Two independent reasons, zero attempts made.

## Spend

Derived **$0.005745** of the $0.20 aggregate limit, from trial A alone. Trial B is unpriced, so the
total is reported incomplete: what it spent is unknown, not zero. No chargeable probe ran.

**A local timeout is not a billing cap.** Terminating these processes says nothing about work the
provider had already accepted, and no claim is made that spending stopped when the process did.

## What this establishes, and what it does not

Established, under these conditions: a real executor holding a real provider connection, with a real
tool subprocess blocking, is terminated when the controller's deadline expires; the absence of every
process the attempt owned is observed rather than assumed; nothing outside the owned set is
signalled; the attempt is recorded as timed out, keeps its evidence, and cannot become another
trajectory.

Not established, and not claimed: universal process containment; any reliability rate — this is one
observation of each case, not a sample; that provider-side work was cancelled or any charge avoided;
behaviour on any other platform, across host suspend, or after the controller itself is killed. The
residual limitations recorded in the timeout audit stand unchanged.

**One instrument limitation worth recording.** The runner's own watcher never matched the executor
process: it looked for the staged path `/pb-tool-…/opencode` in the command line, and the real
executor is invoked by name through `PATH`, so its `argv[0]` is just `opencode`. The executor's
liveness at expiry is therefore established from the termination record instead — a pid is recorded
as `owned_because: recorded` only if its live command line named the view root, which both recorded
pids did — together with `worker.log` showing active tool calls seconds earlier. The conclusion
holds; the watcher pattern was too narrow, and a future check should match on the view root rather
than the tools path.
