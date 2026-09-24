"""A run-owned supervisor for one admitted launch, so the launch outlives the caller that asked.

The host controller — containment, the host deadline, the post-exit ownership sweep, ledger
classification and receipts — used to run inside the process that called `continue`. On 2026-09-24
a coordinator host ran `continue` in the background and then exited, which killed that controller.
The worker and its in-boundary monitor survived. The monitor can detect the deadline but not enforce
it, because the boundary denies it `signal`, and the reserved slot was left unclassified.
Reproduced credential-free through the front door, the same shape followed every time.

Now `continue` starts a supervisor in its own process session and waits for it. The supervisor
admits, reserves, launches and finalizes exactly as the in-process controller did; the caller only
waits:

- **The caller exits.** The supervisor carries on.
- **A new caller runs `continue`.** It waits for the same supervisor instead of launching.
- **The supervisor itself is lost** (SIGKILL, host restart). `recover` diagnoses the run from
  retained evidence, and `recover --apply` resumes supervision of a worker still running or
  finalizes one that has ended. It never invents an outcome, a cost or an acceptance, and it never
  starts another attempt.

A supervisor is known by a token in its own command line and its process start time. A pid alone is
never trusted, because a pid can be reused.

What this does not survive:
- **A host restart during an attempt.** The worker dies with the host, and `recover` finds the
  evidence the attempt left.
- **A supervisor that is alive but hung.** It is reported as running.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any, Iterator
import uuid

SCRIPTS = Path(__file__).resolve().parent
RECORD_FORMAT = "proofbound-launch-supervision-v1"

#: Deterministic failure injection for the regression suite only. When set, the supervisor kills
#: itself with SIGKILL on reaching the named stage. It has no effect when unset.
FAULT_ENV = "PB_TEST_SUPERVISOR_FAULT"
STAGES = ("admitted", "reserved", "running", "finalizing")

#: The launcher returncode a slot records when the process that could have observed it was lost.
UNOBSERVED_RETURNCODE = -1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def directory(run: Path) -> Path:
    return Path(run) / "supervision"


def active_path(run: Path) -> Path:
    return directory(run) / "active.json"


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.partial")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_active(run: Path) -> "dict[str, Any] | None":
    path = active_path(run)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"unreadable": str(path)}


def _ps(pid: int, field: str) -> "str | None":
    try:
        cp = subprocess.run(["/bin/ps", "-o", f"{field}=", "-p", str(pid)], capture_output=True,
                            text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return cp.stdout.strip() if cp.returncode == 0 and cp.stdout.strip() else ""


def alive(record: "dict[str, Any] | None") -> "bool | None":
    """Is this record's supervisor running? `None` means the process table could not be read.

    The pid must be alive, started at the recorded time, and name the record's token in its command
    line. A reused pid fails the last two.
    """
    if not record or not isinstance(record.get("pid"), int) or not record.get("token"):
        return False
    pid = record["pid"]
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    started, command = _ps(pid, "lstart"), _ps(pid, "command")
    if started is None or command is None:
        return None
    return bool(started) and started == record.get("process_start") and record["token"] in command


@contextmanager
def run_lock(run: Path, *, timeout: float = 30.0) -> Iterator[None]:
    """The run's short decision lock: who launches, who attaches, who recovers. Never held while a
    worker runs."""
    import fcntl
    path = Path(run) / ".launch.lock"
    with path.open("a") as handle:
        ends = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= ends:
                    raise ValueError("another command holds this run's launch lock; retry, or run "
                                     "`status`") from None
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _spawn(run: Path, mode: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Start a supervisor in its own process session and record who it is. Call under `run_lock`."""
    token = uuid.uuid4().hex
    log = directory(run) / f"{token}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as out:
        proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "supervise",
                                 "--run", str(run), "--token", token],
                                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True)
    record = {"format": RECORD_FORMAT, "token": token, "mode": mode, "pid": proc.pid,
              "process_start": _ps(proc.pid, "lstart"), "created_at": _now(),
              "caller_pid": os.getpid(), "stage": "starting", **payload}
    _write(active_path(run), record)
    return record


def update(run: Path, token: str, fields: dict[str, Any]) -> None:
    record = read_active(run)
    if not record or record.get("token") != token:
        raise RuntimeError("this supervisor no longer owns the run's supervision record")
    _write(active_path(run), {**record, **fields, "updated_at": _now()})


def _result_path(run: Path, token: str) -> Path:
    return directory(run) / f"{token}.result.json"


def _close(run: Path, record: dict[str, Any], result: dict[str, Any]) -> None:
    """The result first, then the record archived: a reader never sees neither."""
    _write(_result_path(run, record["token"]), result)
    _write(directory(run) / f"{record['token']}.record.json",
           {**(read_active(run) or record), "ended_at": _now()})
    try:
        active_path(run).unlink()
    except FileNotFoundError:
        pass


def wait(run: Path, record: dict[str, Any], *, poll: float = 0.5) -> dict[str, Any]:
    """Wait for a supervisor's result. The supervisor does the work; this only waits for it."""
    result = _result_path(run, record["token"])
    checks = 0
    while True:
        if result.is_file():
            try:
                return json.loads(result.read_text(encoding="utf-8"))
            except ValueError:
                pass                          # being written; read again
        checks += 1
        if checks % 4 == 0 and alive(record) is False and not result.is_file():
            time.sleep(poll)                  # a result written as it exited
            if result.is_file():
                continue
            return {"launched": None, "admitted": None, "unresolved": True,
                    "why": [f"the launch supervisor (pid {record['pid']}) is no longer running "
                            "and recorded no result; run `pb_workflow.py recover --run "
                            f"{run}` to see what it left"]}
        time.sleep(poll)


def launch(run: Path, request: dict[str, Any]) -> dict[str, Any]:
    """`continue`'s launch: start a supervisor, or wait for the one already running."""
    run = Path(run).resolve()
    with run_lock(run):
        record = read_active(run)
        if record is not None:
            state = alive(record)
            if state is not True:
                return {"launched": False, "admitted": False, "unresolved": True,
                        "why": ["this run has a launch supervision record whose supervisor is "
                                + ("not running" if state is False else "unverifiable")
                                + f"; nothing new was launched. Run `pb_workflow.py recover --run "
                                  f"{run}`"]}
            attached = True
        else:
            record = _spawn(run, "launch", {"request": request})
            attached = False
    result = wait(run, record)
    return {**result, "supervisor": {"token": record["token"], "pid": record["pid"],
                                     "mode": record["mode"], "attached": attached}}


def _fault(stage: str) -> None:
    if os.environ.get(FAULT_ENV) == stage:
        os.kill(os.getpid(), signal.SIGKILL)


def supervise(run: Path, token: str) -> int:
    """The supervisor's own body. It acts only on a record that names its token and its pid."""
    run = Path(run).resolve()
    record = None
    for _ in range(100):
        record = read_active(run)
        if record and record.get("token") == token and record.get("pid") == os.getpid():
            break
        time.sleep(0.1)
    else:
        return 3
    import _supervised_launch

    def progress(fields: dict[str, Any]) -> None:
        update(run, token, fields)
        _fault(fields.get("stage", ""))

    try:
        if record["mode"] == "adopt":
            result = _supervised_launch._adopt(run, record["adopt"], progress=progress)
        else:
            request = record["request"]
            result = _supervised_launch._launch(run, phase=request["phase"], task=request["task"],
                                                role=request["role"], inputs=request.get("inputs"),
                                                progress=progress)
    except Exception as exc:                  # recorded, never swallowed: recover sees what is left
        result = {"launched": None, "admitted": None, "unresolved": True,
                  "why": [f"the supervisor failed: {type(exc).__name__}: {exc}; run "
                          f"`pb_workflow.py recover --run {run}`"]}
    _close(run, record, result)
    return 0


# -- diagnosis and recovery ----------------------------------------------------------------------

def _config(run: Path) -> "tuple[dict[str, Any], dict[str, Any]]":
    from _worker_profiles import of
    config = json.loads((run / "run-config.json").read_text(encoding="utf-8"))
    return config, of(config)


def _ledger(run: Path, config: dict[str, Any], settings: dict[str, Any]):
    from _launch_budget import LaunchLedger
    policy = config["policy"]
    return LaunchLedger(run / "launch-ledger.json", limit=policy["aggregate_limit"],
                        reserve=policy["reserve"], ceiling=policy["launch_ceiling"],
                        repair_cycles=policy.get("repair_cycles", 1), billing=settings["billing"],
                        output_token_allowance=settings["resources"]["output_token_allowance"])


def _read_json(path: Path) -> "tuple[dict[str, Any] | None, str | None]":
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return (data, None) if isinstance(data, dict) else (None, "not a JSON object")
    except (OSError, ValueError) as exc:
        return None, f"unreadable: {type(exc).__name__}"


def _attempt(event: Path) -> dict[str, Any]:
    attempt, attempt_error = _read_json(event / "attempt.json")
    terminal, terminal_error = _read_json(event / "terminal.json")
    recorded = [attempt[k] for k in ("worker_pid", "launcher_pid")
                if attempt and isinstance(attempt.get(k), int)]
    return {"event_dir": str(event), "reservation": (event / "launch-reservation.json").is_file(),
            "attempt": bool(attempt), "attempt_error": attempt_error,
            "started_at": (attempt or {}).get("started_at"), "recorded_pids": recorded,
            "terminal": (None if terminal is None else
                         {"status": terminal.get("status"), "exit_code": terminal.get("exit_code"),
                          "timed_out": terminal.get("timed_out"),
                          "worker_stopped": terminal.get("worker_stopped")}),
            "terminal_error": terminal_error}


def diagnose(run: Path) -> dict[str, Any]:
    """Read-only: what an interrupted launch left, and what `recover --apply` would do about it."""
    from _attempt_teardown import _owned_processes
    from _launch_budget import spend
    run = Path(run).resolve()
    config, settings = _config(run)
    runtime_root = Path(config["home"]).parent
    ledger = _ledger(run, config, settings)
    record = read_active(run)
    supervisor = None
    if record is not None:
        supervisor = {k: record.get(k) for k in ("token", "mode", "pid", "process_start",
                                                 "created_at", "stage", "slot")}
        supervisor["running"] = alive(record) if "unreadable" not in record else False
        if "unreadable" in record:
            supervisor["unreadable"] = record["unreadable"]
    unresolved = [s for s in ledger.unresolved()]
    claimed = {str(Path(s["event_dir"]).resolve()) for s in ledger.slots if s.get("event_dir")}
    unclaimed = sorted(p.parent for p in run.rglob("launch-reservation.json")
                       if str(p.parent.resolve()) not in claimed)
    attempts = [_attempt(p) for p in unclaimed]
    recorded = [pid for a in attempts for pid in a["recorded_pids"]]
    processes = _owned_processes(runtime_root, recorded)
    owned = [{"pid": r["pid"], "why": r["owned_because"], "command": r["command"][:120]}
             for r in processes["owned"]]
    account = spend(run, config["paths"]["session_db"], event_dirs=ledger.own_event_dirs(),
                    limit=config["policy"]["aggregate_limit"], reserve=config["policy"]["reserve"],
                    billing=settings["billing"])
    out: dict[str, Any] = {
        "run": str(run), "supervisor": supervisor,
        "unresolved_slots": [{k: s.get(k) for k in ("slot", "role", "phase", "task", "reserved_at")}
                             for s in unresolved],
        "unclaimed_attempts": attempts,
        "processes": {"owned": owned, "table_available": not processes["table_unavailable"]},
        "accounting": {"derived_classified": account.get("derived"),
                       "complete": account.get("complete"),
                       "note": "derived from classified slots only; an unresolved attempt's usage "
                               "is counted once it is classified"},
        "read_only": True}

    def verdict(state: str, apply: "str | None", why: str) -> dict[str, Any]:
        return {**out, "state": state, "apply_would": apply, "why": why}

    if supervisor and supervisor.get("running") is True:
        return verdict("supervised", None, "a supervisor is running this launch; `continue` waits "
                                           "for it. Nothing to recover")
    if supervisor and supervisor.get("running") is None:
        return verdict("unknown", None, "the process table could not be read, so whether the "
                                        "supervisor runs is unknown; nothing is changed")
    if processes["table_unavailable"]:
        return verdict("unknown", None, "the process table could not be read; whether a worker "
                                        "still runs is unknown; nothing is changed")
    if len(unresolved) > 1 or len(attempts) > 1:
        return verdict("contradictory", None,
                       f"{len(unresolved)} unresolved slot(s) and {len(attempts)} unclaimed "
                       "attempt(s); one launch leaves at most one of each. Preserve the run and "
                       "inspect it; nothing is changed")
    if not unresolved:
        if attempts:
            return verdict("contradictory", None, "an attempt holds a reservation no ledger slot "
                                                  "claims, yet no slot is unresolved; nothing is "
                                                  "changed")
        if supervisor:
            return verdict("supervisor-ended", "archive the supervision record",
                           "the supervisor is gone but every slot is classified; only its record "
                           "remains")
        return verdict("clear", None, "no interrupted launch")
    attempt = attempts[0] if attempts else None
    if owned:
        return verdict("worker-running-unsupervised",
                       "start a supervisor that adopts this attempt: containment, the recorded "
                       "deadline, teardown, the post-exit sweep and classification",
                       "processes this attempt owns are running and no supervisor is watching "
                       "them")
    if attempt is None:
        return verdict("pre-executor", "classify the slot as a pre-executor failure",
                       "the slot was reserved but no attempt reservation exists and nothing this "
                       "attempt owns is running; the executor was never reached")
    if attempt["terminal_error"] or attempt["attempt_error"]:
        return verdict("contradictory", None, "the attempt's records are unreadable: "
                       f"{attempt['attempt_error'] or attempt['terminal_error']}; nothing is "
                       "changed")
    if attempt["terminal"]:
        return verdict("terminal-unrecorded", "sweep, then classify the slot from the attempt's "
                                              "reservation and terminal record",
                       "the attempt ended and wrote its terminal record, but its slot was never "
                       "classified")
    return verdict("no-terminal", "sweep, then classify the slot as executor-reached with its "
                                  "outcome unknown; the run stays blocked on the attempt",
                   "the attempt reached the executor and nothing it owns is running, but it left "
                   "no terminal record")


def recover(run: Path, *, apply: bool) -> dict[str, Any]:
    """`recover`: diagnosis, and with `apply` the one change the diagnosis names. Idempotent."""
    run = Path(run).resolve()
    if not apply:
        return diagnose(run)
    with run_lock(run):
        found = diagnose(run)
        state = found["state"]
        if found["apply_would"] is None:
            return {**found, "applied": None}
        if state == "worker-running-unsupervised":
            record = _spawn(run, "adopt", {"adopt": _adoption(run, found)})
        else:
            return {**found, "applied": _finalize(run, found)}
    result = wait(run, record)
    return {**found, "applied": {"adopted": True, "result": result,
                                 "supervisor": {"token": record["token"], "pid": record["pid"]}}}


def _adoption(run: Path, found: dict[str, Any]) -> dict[str, Any]:
    """What an adopting supervisor needs, taken from the lost supervisor's record where it exists
    and otherwise re-derived from the attempt's own evidence."""
    lost = read_active(run) or {}
    slot = found["unresolved_slots"][0]
    attempt = found["unclaimed_attempts"][0] if found["unclaimed_attempts"] else None
    return {"slot": slot["slot"], "reserved_at": slot["reserved_at"],
            "event_dir": attempt["event_dir"] if attempt else None,
            "started_at": attempt["started_at"] if attempt else None,
            "host_deadline_at": lost.get("host_deadline_at"), "watch": lost.get("watch"),
            "lost_supervisor": {k: lost.get(k) for k in ("token", "pid", "process_start",
                                                         "stage")} if lost else None}


def _finalize(run: Path, found: dict[str, Any]) -> dict[str, Any]:
    """Classify an interrupted slot from retained evidence. Invents no outcome and no cost."""
    from _attempt_teardown import stop_attempt
    from _receipts import receipt
    import _supervised_launch
    config, settings = _config(run)
    runtime_root = Path(config["home"]).parent
    ledger = _ledger(run, config, settings)
    record = read_active(run)
    state = found["state"]
    applied: dict[str, Any] = {"state": state}
    if state != "supervisor-ended":
        slot = found["unresolved_slots"][0]
        attempt = found["unclaimed_attempts"][0] if found["unclaimed_attempts"] else None
        grace = config["deadline"].get("teardown_grace_seconds",
                                       _supervised_launch.TEARDOWN_GRACE_SECONDS)
        sweep = stop_attempt(runtime_root, run, grace=grace)
        classified = ledger.classify(
            slot["slot"], run_root=run, event_dir=attempt["event_dir"] if attempt else None,
            launcher_returncode=UNOBSERVED_RETURNCODE,
            launcher_output=("not observed: the process that launched this attempt was lost "
                             f"before classifying it; classified by `recover` from retained "
                             f"evidence ({state})"))
        if attempt and settings["executor"].get("startup"):
            _supervised_launch._record_state(Path(attempt["event_dir"]), settings, config,
                                             before=None, launcher_returncode=None, sweep=sweep)
        terminal = (attempt or {}).get("terminal") or {}
        applied.update(slot=classified["slot"], classification=classified["classification"],
                       terminal_status=classified.get("terminal_status"),
                       sweep=sweep.get("summary"),
                       outcome=terminal.get("status") or "unknown: no terminal record")
        receipt(run, "launch reconciliation", {
            **applied, "evidence": {"reservation": bool(attempt and attempt["reservation"]),
                                    "terminal": (attempt or {}).get("terminal"),
                                    "owned_processes": found["processes"]["owned"]},
            "lost_supervisor": record and {k: record.get(k) for k in ("token", "pid", "stage")},
            "by": "pb_workflow.py recover --apply"},
            phase=slot.get("phase"), task=slot.get("task"), role=slot.get("role"))
    if record is not None:
        token = record.get("token") or f"unreadable-{int(time.time())}"
        _close(run, {**record, "token": token},
               {"recovered": applied, "why": "the supervisor was lost; `recover --apply` "
                                             "finalized from retained evidence"})
    return applied


def main(argv: "list[str] | None" = None) -> int:
    import argparse
    sys.path.insert(0, str(SCRIPTS))
    ap = argparse.ArgumentParser(description="run-owned launch supervisor (internal)")
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("supervise")
    s.add_argument("--run", type=Path, required=True)
    s.add_argument("--token", required=True)
    args = ap.parse_args(argv)
    return supervise(args.run, args.token)


if __name__ == "__main__":
    raise SystemExit(main())
