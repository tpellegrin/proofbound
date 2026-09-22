"""Host-controller ownership and termination for a worker attempt.

The worker runs inside a `sandbox-exec` boundary whose profile **denies `signal`**, so nothing
inside it can stop even its own direct child. A deadline enforced from in there is a deadline that
cannot be enforced: the in-boundary monitor exits, the launcher exits, and the host controller
returns a normal-looking classification while the worker and its descendants keep running — orphaned,
unbounded and off the books. That was reproduced through the real front door on macOS with a 5s
deadline: the call returned after 26.7s and left both the worker and a `setsid` grandchild alive.

So termination belongs to the **host controller**, outside the boundary, which is what this module
provides. The logic is not new: it is the mechanism `evals/_mlr_boundary.py` developed and audited
for the MLR timeout work, moved here so production owns it and the experiment imports it rather
than the other way round.

What it insists on, each because the obvious shortcut is wrong:

* **Ownership is corroborated before anything is signalled.** A recorded pid whose command line no
  longer names this runtime may have exited and had its number reused; it is reported and left
  alone.
* **No process table means *unknown*, never *nothing running*.** `None` and `[]` are different
  facts and do not share a representation.
* **Groups and individual pids both.** A group signal reaches a child forked after the snapshot; an
  individual signal reaches a descendant that left the group via `setsid`.
* **One shared grace**, with ownership re-derived and *merged* during it — replacing the watch set
  would lose a descendant the moment its parent died.
* **Survivors come from a liveness sweep, not from signals having been delivered.** Delivery is not
  death: a worker can trap `SIGTERM`, the boundary refuses signals with `EPERM`, and a group leader
  exiting says nothing about the group. `EPERM` counts as alive — it is a process we cannot signal,
  which is the opposite of one that has stopped.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Any, Iterable


def _process_table() -> list[dict[str, Any]] | None:
    """One snapshot of the process table, or `None` if it could not be taken.

    `None` and `[]` are different facts and must not share a representation: an empty table means
    nothing is running, while no table at all means nothing is *known*. Collapsing them let a
    failed `ps` report an attempt as cleanly stopped. Found in review.

    `ps` rather than a ppid walk alone. A descendant that calls `setsid` leaves its parent's group,
    and when its parent dies it is reparented to pid 1 — so for that shape neither the group nor the
    ancestry chain still recognises it.
    """
    try:
        done = subprocess.run(["/bin/ps", "-Ao", "pid=,ppid=,pgid=,command="],
                              capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    rows: list[dict[str, Any]] = []
    for line in done.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 3:
            continue
        try:
            rows.append({"pid": int(parts[0]), "ppid": int(parts[1]), "pgid": int(parts[2]),
                         "command": parts[3] if len(parts) > 3 else ""})
        except ValueError:
            continue
    return rows


def _owned_processes(view_root: Path, recorded: list[int]) -> dict[str, Any]:
    """Every live process this attempt owns, and nothing else.

    Returns the owned rows, the groups they lead, the recorded pids that could not be corroborated,
    and whether the process table was readable at all.

    A recorded pid is trusted only if its own command line still names this view. Between the
    launcher writing `attempt.json` and a deadline up to half an hour later, a recorded pid can
    exit and the number be reused by something unrelated; signalling it on the strength of the
    number alone would reach a process this attempt never owned. Corroborated roots are what the
    group and ancestry tests extend from, so an uncorroborated number cannot drag a stranger's
    group in behind it.

    From those roots, four ways a process is recognised, because no one of them is sufficient:

    * it is a corroborated recorded pid — the worker and its monitor;
    * it is still in the process group one of them leads, which is where the executor's tool
      subprocesses sit;
    * it descends from one of them, transitively, over the live snapshot;
    * its command line names this attempt's view root, which catches the processes the launcher
      never recorded at all — the in-view launcher itself and the `wait_worker` helper polling
      inside it, both of which inherit the *controller's* process group.

    The view root is a fresh `mkdtemp` path belonging to this slot alone, which is what makes the
    command-line test safe rather than reckless: no process outside this attempt can name it. The
    match is refused for an implausibly short root, so a truncated value cannot select the whole
    table. The controller and every process it descends from are excluded by pid, so no positive
    test can select them.

    **Known gap, measured not assumed.** A descendant that leaves the group *and* whose own command
    line does not name the view — an ordinary `git` or `node` invocation — is unrecognisable by any
    of the four once the intermediate that links it to a root has exited. `_stop_attempt` re-derives
    ownership while it works, which catches such a process while its parent still lives, but not
    after. The gap is stated in `MLR-eventbus-b1-timeout-audit.md` rather than papered over.
    """
    marker = str(view_root)
    rows = _process_table()
    if rows is None:
        return {"owned": [], "groups": [], "uncorroborated": sorted(set(recorded)),
                "table_unavailable": True}

    by_pid = {row["pid"]: row for row in rows}
    by_parent: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_parent.setdefault(row["ppid"], []).append(row)

    # Never the controller, and never anything it hangs from. An earlier revision excluded the
    # whole of the controller's *process group* instead, which looked equivalent and was not:
    # `sandbox-exec` is started without a new session, so the in-view launcher and the
    # `wait_worker` helper inherit the controller's group, and excluding the group excluded exactly
    # the processes that were being left behind.
    protected = {0, 1, os.getpid()}
    walker = os.getpid()
    while walker in by_pid:
        walker = by_pid[walker]["ppid"]
        if walker in protected:
            break
        protected.add(walker)

    def names_view(row: dict[str, Any]) -> bool:
        return len(marker) >= 12 and marker in row["command"]

    roots = {row["pid"] for row in rows
             if row["pid"] in recorded and row["pid"] not in protected and names_view(row)}
    uncorroborated = sorted(set(recorded) - roots)

    descendants: set[int] = set()
    frontier = list(roots)
    while frontier:
        for child in by_parent.get(frontier.pop(), []):
            if child["pid"] not in descendants:
                descendants.add(child["pid"])
                frontier.append(child["pid"])

    groups = {row["pgid"] for row in rows if row["pid"] in roots and row["pgid"] == row["pid"]}
    groups -= protected

    owned: list[dict[str, Any]] = []
    for row in rows:
        if row["pid"] in protected:
            continue
        if row["pid"] in roots:
            why = "recorded"
        elif row["pgid"] in groups:
            why = "process-group"
        elif row["pid"] in descendants:
            why = "descends-from-recorded"
        elif names_view(row):
            why = "names-the-view"
        else:
            continue
        owned.append({**row, "owned_because": why})
    return {"owned": owned, "groups": sorted(groups), "uncorroborated": uncorroborated,
            "table_unavailable": False}


def _attempt_processes(run_root: Path) -> list[int]:
    """The pids the launcher recorded for this attempt, if it got as far as recording any."""
    # `rglob`, not a fixed `phases/*/tasks/*/attempts/*` shape. The launcher's event-directory
    # layout is its own business and does vary — a glob that encoded one arrangement would silently
    # return no pids under another, and "no pids" is the input that makes everything downstream
    # conclude there was nothing to stop.
    pids: list[int] = []
    for path in sorted(Path(run_root).rglob("attempt.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for key in ("worker_pid", "launcher_pid"):
            value = data.get(key)
            if isinstance(value, int):
                pids.append(value)
    return pids


def _pid_alive(pid: int) -> bool:
    """Whether a pid is still running. `EPERM` counts as alive: it is a process we cannot signal,
    which is the opposite of a process that has stopped."""
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _signal_all(pids: Iterable[int], groups: Iterable[int], sig: int) -> list[dict[str, Any]]:
    """Signal each owned pid, and each group the attempt's roots lead.

    Both, because neither alone is enough. Individual pids reach a descendant that left the group;
    the group signal reaches a child forked *after* the snapshot was taken, which no list of pids
    can name. The groups are only those led by a corroborated root, so nothing unowned is in them.
    """
    sent: list[dict[str, Any]] = []
    for scope, target, call in ([("group", g, os.killpg) for g in groups]
                                + [("process", p, os.kill) for p in pids]):
        record: dict[str, Any] = {"scope": scope, "target": target}
        try:
            call(target, sig)
            record["delivered"] = True
        except ProcessLookupError:
            record["delivered"] = False
            record["already_exited"] = True
        except PermissionError as exc:
            record["delivered"] = False
            record["refused"] = f"EPERM (errno={exc.errno})"
        sent.append(record)
    return sent


def _stop_attempt(view_root: Path, run_root: Path, *, grace: float) -> dict[str, Any]:
    """Stop everything this attempt owns, then look again and say what is still running.

    Signals go to the whole owned set at once and the grace is waited **once**, not per process: a
    grace paid serially for each pid would multiply the overrun it exists to bound.

    Ownership is re-derived while waiting and **merged** into the watch set, never replaced. Merging
    is what catches a child forked after the first snapshot — the window is the whole grace, during
    which the worker is still alive and still driving tool calls. Replacing would lose a `setsid`
    descendant the moment its parent died, which is why the first version of this refused to
    re-derive at all and so missed the forked children instead. Found in review, twice.

    Survivors come from a liveness sweep, not from the signals having been delivered. Delivery is
    not death: a worker can trap `SIGTERM`, the semantic view refuses signals outright with
    `EPERM`, and a group leader exiting says nothing about the group.
    """
    recorded = _attempt_processes(run_root)
    scan = _owned_processes(view_root, recorded)
    record: dict[str, Any] = {"recorded_pids": recorded}
    if scan["uncorroborated"]:
        # A recorded pid whose command line no longer names this view. Either it exited and the
        # number was reused, or it exited and was reaped. Reported, and deliberately not signalled.
        record["uncorroborated_pids"] = scan["uncorroborated"]
    if scan["table_unavailable"]:
        # Nothing is known, which is not the same as nothing running. Never reported as stopped.
        return {**record, "found": 0, "stopped": False, "table_unavailable": True}

    watch: dict[int, dict[str, Any]] = {row["pid"]: row for row in scan["owned"]}
    groups = set(scan["groups"])
    record["found"] = len(watch)
    record["owned"] = [{k: row[k] for k in ("pid", "pgid", "owned_because")}
                       for row in watch.values()]
    if not watch and not groups:
        # Nothing was running. Said plainly, because it is a different fact from having stopped
        # something, and the two must not share a sentence.
        return {**record, "stopped": True, "nothing_was_running": True}

    def refresh() -> None:
        again = _owned_processes(view_root, recorded)
        if again["table_unavailable"]:
            return
        for row in again["owned"]:
            watch.setdefault(row["pid"], row)
        groups.update(again["groups"])

    def settle(limit: float) -> list[int]:
        deadline = time.monotonic() + max(0.0, limit)
        while time.monotonic() < deadline:
            refresh()
            if not [pid for pid in watch if _pid_alive(pid)]:
                return []
            time.sleep(0.05)
        refresh()
        return [pid for pid in watch if _pid_alive(pid)]

    record["sigterm"] = _signal_all(list(watch), groups, signal.SIGTERM)
    if not settle(grace):
        record["found"] = len(watch)
        return {**record, "stopped": True, "escalated": False, "survivors": []}

    record["escalated"] = True
    record["sigkill"] = _signal_all([pid for pid in watch if _pid_alive(pid)], groups,
                                    signal.SIGKILL)
    left = settle(grace)
    record["found"] = len(watch)
    record["owned"] = [{k: row[k] for k in ("pid", "pgid", "owned_because")}
                       for row in watch.values()]
    record["survivors"] = [{k: watch[pid][k] for k in ("pid", "pgid", "owned_because")}
                           for pid in left]
    record["stopped"] = not left
    return record


def _stop_summary(termination: dict[str, Any]) -> str:
    """The outcome in words, kept in step with what was actually established.

    Every qualification the structured record carries appears here too. The prose is what reaches a
    run report, and a reader of the prose must not end up better informed by reading the JSON.
    """
    caveat = ""
    if termination.get("uncorroborated_pids"):
        caveat = (f"; {len(termination['uncorroborated_pids'])} recorded pid(s) could not be "
                  "corroborated against this view and were not signalled")
    if termination.get("table_unavailable"):
        return ("the process table could not be read, so nothing could be identified or stopped"
                + caveat)
    if termination.get("nothing_was_running"):
        return "no process this attempt owned was still running" + caveat
    survivors = termination.get("survivors") or []
    if termination.get("stopped"):
        return (f"all {termination.get('found')} process(es) this attempt owned were confirmed "
                f"stopped{caveat}")
    return (f"{len(survivors)} of {termination.get('found')} process(es) this attempt owned are "
            f"STILL RUNNING after SIGKILL: {survivors}{caveat}")


# -- the public surface production uses ---------------------------------------------------------

def stop_attempt(runtime_root, run_root, *, grace: float = 10.0) -> dict[str, Any]:
    """Stop everything this attempt owns and report what is *still* running.

    `runtime_root` is the directory whose path corroborates ownership — every process this attempt
    started names it. Returns the structured record plus a `summary` whose prose carries every
    qualification the record does, so a reader of one is never better informed than a reader of the
    other.
    """
    record = _stop_attempt(Path(runtime_root), Path(run_root), grace=grace)
    return {**record, "summary": _stop_summary(record)}


def survivors_remain(termination: dict[str, Any]) -> bool:
    """Whether anything is known to still be running, or whether that is simply unknown.

    Both cases return True. A teardown that could not read the process table has not established
    that nothing survived, and must not be reported as a clean stop.
    """
    return bool(termination.get("survivors")) or bool(termination.get("table_unavailable"))
