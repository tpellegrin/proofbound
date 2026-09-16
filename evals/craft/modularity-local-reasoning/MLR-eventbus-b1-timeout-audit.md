# `eventbus-b1` — audit of the attempt-ceiling question

**2026-09-16.** A dated audit, written after
[`MLR-eventbus-b1-run.md`](MLR-eventbus-b1-run.md) and changing nothing in it. The run report, the
preregistration and the result record are byte-identical to what they were at `55f67a6`; what
follows is the correction, kept separate as history requires.

**Verdict: b1 remains valid and family R1 stands. No frozen requirement was violated.** §9 of the
run report was wrong about why two slots took as long as they did, and wrong to call the result an
unenforced ceiling breach. The real defect is narrower, is not about b1, and is repaired separately.

## 1. What the 1,800 seconds actually bounds

`_mlr_run.ATTEMPT_TIMEOUT_SECONDS = 1800` is an **implementation constant**, not a preregistered
requirement. The frozen preregistration
[`MLR-eventbus-b1-preregistration.md`](MLR-eventbus-b1-preregistration.md) contains no time limit of
any kind: its only ceiling is §19's **$0.50 budget**, §15 lists "elapsed and session time" among
resource dimensions that are **descriptive only** and "never compared between arms", and §11's
missingness table A–J has no condition on duration. Nothing in §11 or §17 is keyed to how long a
slot takes.

At the execution commit `0122b57` the constant reached exactly two places, both in
`evals/_mlr_boundary.py`: it was passed as the `timeout=` of `view.run(...)` for the `launch` call
and again for the `gate` call. Each of those is a `subprocess.run` timeout on **one child process**,
measured on a **monotonic** clock.

| interval | clock | what it covers |
|---|---|---|
| the 1,800 s limit | monotonic | one `subprocess.run` call, from its start until its child's output closes |
| `elapsed_seconds` on a measurement | wall clock (`time.time()`) | the whole attempt: view construction, staging, hermeticity preflight, launch, gate, extraction, grading, profiling, retention |

**These are different intervals on different clocks, and the second is strictly larger.** The run
report compared a wall-clock attempt duration against a monotonic per-call limit and read the
difference as an overrun. It is not one.

## 2. What happened in slots 6 and 7

Measured, from three independent sources that agree.

Per-slot start times are recoverable exactly: `run_bounded_attempt` names each retained evidence
directory `{arm}-{int(started*1000)}`. The twelve slots run back to back with gaps of 0.1–0.3 s, and
the sum of `elapsed_seconds` (11,181.9 s) accounts for the series span (20:58:16 → 00:04:40 local,
11,183.9 s) to within exactly those gaps, so the record's own timing is complete and consistent with
no unexplained interval.

For slot 6 (`contract`, pair 3), from the retained lifecycle evidence at
`~/.proofbound/evidence/eventbus-b1/contract-1789517216468/workspace/DeepSeekAndDestroy/plans/mlr/runs/r1/phases/build/tasks/MLR-external/attempts/implementer-1/terminal.json`:

| fact | value |
|---|---|
| `reserved_at` | 2026-09-16T00:06:57.133 Z |
| `started_at` (worker process) | 2026-09-16T00:06:57.175 Z |
| `process_ended_at` | 2026-09-16T01:37:31.188 Z |
| `ended_at` (terminal written) | 2026-09-16T01:37:32.078 Z |
| `status` · `exit_code` | `completed` · `0` |

Worker process lifetime: **5,434.0 s of wall clock**. The session database agrees
(`session.time_created` → `time_updated` = 5,432.1 s) and the attempt's own `elapsed_seconds` agrees
(5,439.9 s).

**The host was asleep for almost all of it.** From `pmset -g log`, the machine entered Sleep
repeatedly inside slot 6's window — first `'Clamshell Sleep'` (the lid was closed) at 21:07:20 and
21:07:31, then `'Maintenance Sleep'` for 903, 901, 903, 201, 902 and 900 s:

| slot | wall | host asleep | awake |
|---|---|---|---|
| 6 · `contract` pair 3 | 5,440 s | 5,284 s | **156 s** |
| 7 · `contract` pair 4 | 4,779 s | 4,597 s | **182 s** |
| 1 · `full` pair 1 (control) | 110 s | 0 s | 110 s |

macOS `time.monotonic()` does not advance across system sleep, and every deadline in the chain is
monotonic — `subprocess.run`'s timeout and `wait_worker.py`'s alike. So the limit saw 156 s and
182 s — **inside 1,800 s, and in line with the other ten slots' 54.7–144.7 s**. Those two slots were
not slow. They were ordinary attempts on a laptop whose lid was shut.

The clock property is platform behaviour rather than something this audit measured directly, but it
is corroborated arithmetically here and the corroboration is tight: slot 6's worker lived 5,434.0 s
of wall clock with 5,284 s of logged host sleep inside the window, leaving ~150 s of running time
against the ~156 s of awake wall clock the power log independently accounts for. Two separate
sources agree to within seconds, and no deadline firing is exactly what that predicts.

This also explains the one anomaly the run report noticed and misread: `calls_started` exceeding
`calls_finished` (26 against 21, and 29 against 25) is the executor's bookkeeping across
suspend/resume, not evidence of a provider stall.

**Withdrawn.** The run report's §9 attributed these durations to "the outbound-firewall provider
stall this repository has documented before" and said "two stuck workers held this series open for
2.8 hours". Both claims are unsupported. There was no stall and no stuck worker; there was a
sleeping host, and no deadline was reached on the clock any deadline used.

## 3. The four questions, answered

**A · Did execution violate a frozen requirement?** **No.** There is no frozen time requirement to
violate. And the implementation limit that does exist was not exceeded in the interval it governs:
156 s and 182 s of monotonic execution against 1,800 s.

**B · Does it affect slot eligibility, series validity, or only an operational claim?** **Only an
operational claim** — one made in the run report, now withdrawn here. Slot eligibility is untouched:
all twelve attempts were `valid` on the preregistered criteria, and duration is not among them.
Series validity is untouched: no §11 condition is keyed to time.

**C · Does R1 remain supported under the actual frozen rules?** **Yes.** §17 is evaluated in order
and F requires "any instrument or execution validity defect under §11". There is none: the deadline
behaved as implemented, the correctness gate (§12) passed on all twelve, treatment integrity holds
(direct source structurally zero in all six `contract` slots, every route, zero distinct
representations), attribution reported zero unresolved items and components, zero contradictions and
zero uncovered events, profiles are complete, and spend is complete at $0.238762. R3 is excluded
because `full` consumed 6,826–7,824 bytes; R2 because `contract` was correct on 6/6; R4 because
7,474 against 0 is not a close profile. R1 applies.

**D · Which descriptive observations remain supportable regardless?** Correctness (12/12 slots,
6/6 both-correct pairs, oracle-graded on extracted workspaces); treatment integrity; the primary
measurand and its six positive per-pair differences; `source_equivalent_reconstruction` zero in all
twelve; spend complete; every frozen §5 identity holding on all twelve slots.

**Not supportable**, and to be read as withdrawn wherever the run report implies them: that slots 6
and 7 represent ~90 and ~80 minutes of *work*; that a provider stall occurred; that any ceiling was
breached; that two workers were stuck.

**One caveat that is genuinely new.** For slots 6 and 7 the resource dimensions §15 records —
`elapsed_seconds`, `session_span_seconds`, `model_seconds_derived` — are wall clock spanning host
suspension and must not be read as work time. §15 already forbids comparing any resource dimension
between arms, which is what stops two long-looking `contract` slots from being mistaken for a
treatment effect. Nothing in the primary or secondary measurand is affected: both slots are
`contract`, whose direct-source value is structurally zero.

## 4. Scope for q1

Checked, not assumed, from the surviving record.

`craft-mlr-deepseek-v4-flash-high-paired-q1.json` records all twelve slots at **83.1–185.9 s**
`elapsed_seconds`, with session spans consistent with them, running back to back from 12:16:10 to
12:44:03 on 2026-09-14 — 1,673 s for the whole series. The host power log shows **no sleep at all**
in that window. No q1 slot approached 1,800 s on any clock, so the confusion this audit resolves
does not arise for it and no q1 number changes.

**Verification limitation.** q1's raw evidence tree (`~/.claude/jobs/764af897/tmp/q1-evidence/`) no
longer exists, so its per-slot `terminal.json` cannot be re-read and worker process lifetimes cannot
be re-derived independently. The conclusion above rests on the committed record's own timing fields
plus the host power log. q1 is not re-run.

## 5. The real defect, which is not about b1

Looking for a breach turned up something worse than the one alleged: **nothing in the chain could
stop a worker at all.**

| layer | bound, at `0122b57` |
|---|---|
| controller `_mlr_boundary.launch` | `subprocess.run(timeout=1800)` on its own child |
| `dsd_attempt.py launch` | none; forwarded no limit |
| detached `run_worker.py` monitor — **owns the worker** | `rc = proc.wait()`, **no timeout, and no `--timeout` argument existed** |
| `wait_worker.py` | `--timeout` default **3,600 s**, never overridden, and a timeout is documented as "intentionally a non-event" |

The controller's limit stops the controller waiting. It kills `sandbox-exec` and nothing else: the
monitor is detached into its own session and the worker into another, so both keep running — still
calling a provider — while the `finally` destroys the view around them. The one process positioned
to act, the monitor, had no deadline and no way to receive one.

**And it could not have acted even with one.** Measured: inside the semantic view, every signal is
refused. `os.kill` on the monitor's *own direct child* returns `EPERM`, and so does `os.killpg`; the
target survives. The view's profile grants no `signal` rule, and signalling its own group is the only
thing permitted. So in-view enforcement is impossible under the current boundary, and the controller
— the view's parent, not sandboxed — is the only place a deadline can take effect. Verified from
outside: `getpgid` resolves and `killpg` is delivered, and the worker dies.

This did not affect b1. Both long slots completed normally and nothing needed stopping. It is a
future-execution hazard, and it is repaired in the same commit as this audit:

- the controller's own wait **is** the deadline, and on expiry it stops what the attempt owns from
  outside the sandbox: SIGTERM to the whole owned set at once, one bounded grace, SIGKILL to
  whatever is left, then a liveness check per pid. `stopped` is the result of that check and not of
  the signals having been delivered;
- **ownership is decided before anything is signalled, from four complementary observations.**
  They are not four independent proofs of containment and must not be read as redundancy: each
  covers a shape the others miss, and the set is only as strong as its union. The pids
  `attempt.json` records; anything still in their process groups; anything descending from them
  transitively; and anything whose command line names this attempt's view root — a fresh `mkdtemp`
  path no other process can name. A command line naming the view is *ownership evidence* precisely
  because the path is unique to this slot; it is not name similarity, and no test here matches on a
  program name. The ancestry test only
  works before the first signal, because a `setsid` descendant is reparented to pid 1 the moment
  its parent dies, and the view-root test is what catches the processes the launcher never records
  at all: the in-view launcher and the `wait_worker` helper, which inherit the *controller's*
  process group and were being left polling inside destroyed views;
- a recorded pid is trusted only if its command line still names the view. Half an hour can pass
  between the launcher recording a pid and a deadline expiring, and a reused number would otherwise
  be signalled on the strength of the number alone. An uncorroborated pid is reported and never
  signalled;
- the in-view limits are passed but deliberately set *behind* the controller's, so a monitor that
  cannot signal never writes a `terminal.json` saying "timeout" about a worker still running;
- `run_worker.py` gains `--timeout` and `--termination-grace` for callers that are not sandboxed,
  spawns the worker in its own session, takes its process-group id from spawn time, and
  distinguishes `EPERM` from "already exited" instead of reporting both as a stop;
- a timeout disposition is authoritative over anything gradeable, so late-arriving output cannot
  turn a stopped attempt into an ordinary successful slot;
- a timed-out attempt is `harness-failure` with `trajectory_began` true, so §11 C governs, no retry
  follows, and its unpriced spend makes the account incomplete and blocks further launches;
- signals go to the owned pids **and** to the groups the corroborated roots lead, and ownership is
  re-derived and *merged* while the grace is waited. Both are needed: a pid list cannot name a child
  forked after the snapshot, and re-deriving without merging would drop a `setsid` descendant the
  moment its parent died. An earlier revision did each of those wrong in turn;
- an interrupted controller (Ctrl-C, or anything else not an `Exception`) stops the attempt on its
  way out before re-raising, on reduced evidence — see below;
- `launch` and `gate` now share **one** monotonic deadline rather than each receiving the full
  `timeout`, so `attempt_deadline_seconds` describes the real exposure instead of half of it, and a
  deadline that expires during classification stops the attempt rather than falling through to a
  handler that stopped nothing;
- both clocks are recorded per attempt — `attempt_deadline_seconds`, `worker_monotonic_seconds`,
  `worker_wall_seconds` — so the substitution this audit had to unpick cannot recur silently. The
  monitor's own termination record is kept beside the controller's as `monitor_termination`, because
  what it was *refused* is the measurement the design rests on.

### What is still not guaranteed

Stated at this length because the first two versions of this repair each claimed more than they
delivered, and review caught both: one reported "every process was confirmed stopped" while a group
leader's children ran on, the next while a `setsid` grandchild did.

- **Local termination only.** Work already dispatched to a provider is not ours to cancel, and no
  claim is made that stopping a local process stops a provider-side charge.
- **A controller killed outright cannot clean up.** `SIGKILL` to the controller leaves the monitor
  and worker running with the view destroyed around them — the exact pre-repair condition. There is
  no in-view fallback, because nothing inside the view can signal anything. Ctrl-C is handled; a
  `kill -9` is not, and cannot be from inside this design.
- **Interrupt cleanup runs on reduced evidence.** A `with` block exits before an enclosing handler
  is selected, so by the time the Ctrl-C path runs the view — and `attempt.json` inside it — is
  already gone. The recorded pids are therefore unavailable and neither the group nor the ancestry
  test can fire; ownership rests on the command-line test alone. That still reaches the launcher,
  the monitor, the worker and `wait_worker`, each of which carries a path under the view root in its
  argv, and argv outlives the directory. It does not reach a bare tool subprocess. The record says
  `ownership_reduced_to_command_line` when this happens.
- **The grace is real running time.** A worker that traps SIGTERM runs until SIGKILL, so the
  effective bound is the deadline plus at most two grace periods (~20 s), not the deadline exactly.
- **One process shape is not reachable by any of the four tests**: a descendant whose own command
  line does not name the view — an ordinary `git` or `node` invocation — *and* whose link back to a
  root has been broken, because the intermediate that spawned it exited before the scan and it was
  reparented to pid 1. Re-deriving ownership during the grace narrows this to processes orphaned
  before the first scan, but does not close it. Reading each candidate's working directory would;
  that was judged more machinery than the gap warrants, and the gap is recorded here instead.
  Nothing observed it in b1 or in testing.
- **A failed `ps` is reported as unknown, not as clean.** If the process table cannot be read,
  `stopped` is `false` and the prose says nothing could be identified. That is the honest outcome,
  not a stop.


## 6. What this changes about future execution

The repair changes the **execution configuration and an instrument-adjacent behaviour**, not the
frozen b1 design, and b1 is neither amended nor re-run. Specifically:

- The semantic boundary policy is **unchanged** — no `signal` rule was added — so
  `policy.identity()` and the per-slot `boundary_identity` are unaffected. The repair works with the
  boundary as frozen rather than around it.
- The staged harness **does** change: `scripts/` is copied into the view, so `run_worker.py` and
  `dsd_attempt.py` differ from the bytes b1 ran. Any future experiment runs a different instrument
  in this respect, and b1's qualification is qualification of the historical one.
- Attempt records gain fields (`attempt_deadline_seconds`, `terminal_status`, `timed_out`, the two
  clocks, `termination`). Additive; `_repeat.frozen_identity` is computed over configuration, not
  over measurement keys.

**Deterministic tests passing is not a field qualification.** What the new tests establish is that
owned local processes actually stop and their evidence survives, on this platform, with controlled
workers. What they cannot establish is behaviour against a real provider under a real stall — the
condition the deadline exists for has never been observed, because the one time it looked like it
had, the host was asleep.

Minimum additional verification before any future paid execution, based on what the repair touches:

1. a non-paid preflight on the executing host, since the harness bytes changed;
2. one observation that a real executor stopped by this path leaves no live process and no stale
   view — obtainable with a deliberately short deadline on a single throwaway attempt, and cheap;
3. confirmation that a host which may suspend is excluded or kept awake for the duration, because a
   monotonic deadline cannot bound wall-clock exposure and a suspended host silently multiplies it.

Nothing here requires restarting the qualification programme, and no successor study is frozen or
executed in this milestone.

**Supplied, 2026-09-16.** All three were met by `pb-lifecycle-field-check-1`
([protocol and outcome](../../../docs/architecture/proofbound/evidence/lifecycle-field-check.md)):
two real-executor trials at `09a9350`, the second of which stopped a live executor and a live
blocking tool subprocess at its deadline with every owned process confirmed absent, nothing outside
the owned set signalled, and no sleep transition in the window. The lifecycle workstream is closed
on that evidence. What it establishes is operation under those conditions — not universal
containment, not a reliability rate, and nothing about provider-side billing. The residual
limitations listed above are unchanged by it.
