# Readiness repairs before first paid use

Dated 2026-09-22, against baseline `a119583`. Every defect below was **reproduced first**, on the
supported host, through the real front door, with a credential-free fake worker. No provider
request was made.

## A — the deadline did not terminate the worker, and the front door returned anyway

Driven through `pb_workflow.py start` → `continue` with the real `sandbox-exec` boundary, a **5 s**
deadline, and a fake worker that blocks and leaves a `setsid` grandchild ignoring `SIGTERM`.

The launching `continue` returned after **26.7 s** with `classification: executor-reached` — a
normal-looking result. Immediately afterwards:

| pid | ppid | what |
|---|---|---|
| 66171 | **1** | the worker itself, orphaned and still running |
| 66173 | 66171 | the blocked grandchild, own session, still running |

The chain: the deadline fires *inside* the boundary → the profile denies `signal`, so the monitor
cannot stop what it monitors → the launcher exits anyway → the host's `subprocess.run`, which had
**no `timeout=`**, returns → the attempt is classified as concluded → the worker keeps consuming
provider budget with no slot and no accounting.

**Repair.** `scripts/_attempt_teardown.py` — the ownership and termination mechanism `_mlr_boundary`
already proved out, moved into production. The host controller now holds its own bound
(`deadline + margin`), and *also* sweeps after a normal return, because the launcher exits on its
deadline whether or not the signals it sent could be delivered. Ownership is corroborated before
anything is signalled; an unreadable process table is **unknown, never nothing running**; groups and
individual pids are both signalled under one shared grace with ownership re-derived and merged;
survivors come from a liveness sweep, and `EPERM` counts as alive.

Same reproduction afterwards: **0 survivors**, grandchild terminated, both owned processes confirmed
stopped, and the one recorded pid that could not be corroborated reported rather than signalled.

A timeout records a receipt, reports the clock basis (monotonic, and that a host suspend inflates
wall time), states plainly that local termination says nothing about provider billing, and **does
not create a replacement attempt** — one slot stays one slot.

## B — resume and completion defects, through the public CLI

| | Before | After |
|---|---|---|
| **B1** repeat `start` with a different `--check` | `{"existing": true}`, old command silently kept | refuses, naming every field whose requested value was **not** applied |
| **B2** `decide --decision repair` then a fresh `status` | `adjudicate` again, no trace of the decision | `blocked` carrying `pending_repair`, the reason and the receipt, until a `revise` supersedes it |
| **B3** a sealed delivery | proposed `finish`, which then refused | `complete`, with the patch, handoff and an `apply` command; `next` is null |

## B4 — not in the brief: the acceptance check invalidated the review it was checking

`decide --decision accept` runs the project's check command. For an ordinary Python project that
does not gitignore bytecode, the check wrote `__pycache__/*.pyc` **into the project**; the
stale-review guard then compared the project against the reviewer's scope baseline, saw those bytes
as a change, and refused acceptance. The run could never be accepted or delivered.

Every fixture in this repository dodged it — `tests/test_operator_workflow.py` and
`examples/csv-summary/project/.gitignore` both list `__pycache__/`, and `scope_snapshot.py` honours
`--exclude-standard`. The shipped example and the whole suite passed while an ordinary project could
not finish a run.

**Repair.** The check runs with `PYTHONDONTWRITEBYTECODE=1`, and a regression now uses a project
that deliberately does **not** ignore bytecode.

`check_project` also had no timeout. It now has its own bound, separate from the worker deadline and
the teardown grace, and a check that does not finish is recorded as **unknown — not failed**, with
`returncode: null`.

## What this does not establish

All of the above is credential-free mechanics. **No coordinator and no worker was live-qualified by
this work.** The goal-to-change workflow has still never been run end to end against a real agent;
the support matrix in the README says so per row.
