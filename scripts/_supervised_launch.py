"""One supervised launch path, shared by operator and evaluation. No fixture imports."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from _attempt_teardown import stop_attempt, survivors_remain
from _launch_budget import LaunchLedger
from _receipts import receipt
SCRIPTS = Path(__file__).resolve().parent

#: How long the host waits past the worker deadline before it starts terminating, and how long it
#: then allows between SIGTERM and SIGKILL. The in-boundary monitor is given its chance to finish
#: cleanly first; the host only acts once that chance has demonstrably passed.
TEARDOWN_MARGIN_SECONDS = 60
TEARDOWN_GRACE_SECONDS = 10

def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _launch(workdir: "str | Path", *, phase: str, task: str, role: str,
           inputs: "list[str] | None" = None) -> "dict[str, Any]":
    """The supervised path to the configured worker executor.

    Admit, reserve the slot durably, run the shipped launcher, then classify from evidence. A
    refusal returns without launching anything and says which rule refused.
    """
    workdir = Path(workdir).expanduser().resolve()
    config = json.loads((workdir / "run-config.json").read_text())
    run_root = Path(config["paths"]["run_root"])
    db = Path(config["paths"]["session_db"])
    ledger = LaunchLedger(workdir / "launch-ledger.json",
                          limit=config["policy"]["aggregate_limit"],
                          reserve=config["policy"]["reserve"],
                          ceiling=config["policy"]["launch_ceiling"],
                          repair_cycles=config["policy"].get("repair_cycles", 1))

    verdict = ledger.admit(phase=phase, task=task, role=role, run_root=run_root, db=db)
    if not verdict["admit"]:
        receipt(run_root, "launch budget", verdict, phase=phase, task=task, role=role)
        return {"launched": False, "admitted": False, **verdict}

    def refuse(reason):
        result = {"launched": False, "admitted": False, "returncode": 2,
                  "executor_reached": False, "why": [reason]}
        receipt(run_root, "launch preflight", result, phase=phase, task=task, role=role,
                executor=config["executor"], interpreter=config["interpreter"])
        return result

    # The interpreter that launches must be the one the run was prepared on. A rehearsal drove an
    # entire continuation under 3.9 while the record said 3.14, and nothing noticed.
    recorded = str(config["interpreter"]["version"]).split(".")[:2]
    running = [str(n) for n in sys.version_info[:2]]
    if recorded != running:
        return refuse(
            f"refusing to launch: this run was prepared on Python "
            f"{config['interpreter']['version']} and is being driven by {'.'.join(running)}. "
            f"Use {config['interpreter']['executable']}, or prepare a new run.")

    executor_dir = str(Path(config["executor"]["path"]).parent)
    env = ({"LANG": "en_US.UTF-8", "TMPDIR": str(Path(config["home"]).parent / "tmp")}
           if config.get("boundary_profile") else
           {k: v for k, v in os.environ.items() if not k.startswith("OPENCODE")})
    env["PATH"] = os.pathsep.join([executor_dir, "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
    env["HOME"] = config["home"]
    env.update(config.get("worker_env") or {})
    resolved = shutil.which("opencode", path=env["PATH"])
    if resolved != config["executor"]["path"]:
        return refuse(f"refusing to launch: `opencode` resolves to {resolved}, not the frozen "
                         f"executor {config['executor']['path']}")
    if digest_file(resolved) != config["executor"]["sha256"]:
        return refuse("refusing to launch: the resolved executor's bytes are not the frozen "
                         "identity")

    argv = [sys.executable, str(SCRIPTS / "dsd_attempt.py"), "launch",
            "--run-root", str(run_root), "--phase-id", phase, "--task-id", task,
            "--role", role, "--model", config["model"], "--variant", config["variant"],
            f"--auto-flag={config['auto_flag']}",
            "--timeout", str(config["deadline"]["seconds"])]
    for path in inputs or []:
        argv += ["--input", str(path)]
    if config.get("boundary_profile"):
        argv = ["/usr/bin/sandbox-exec", "-f", config["boundary_profile"], *argv]
    before = {str(p.parent) for p in run_root.rglob("launch-reservation.json")}
    slot = ledger.reserve(phase=phase, task=task, role=role,
                          note=f"{config['mode']} launch of {role} on {phase}/{task}")

    # The worker's deadline is enforced *inside* the boundary, where the profile denies `signal`,
    # so the in-boundary monitor cannot stop what it is monitoring. The host controller therefore
    # keeps its own bound and owns termination. Reproduced before this existed: a 5s deadline
    # returned after 26.7s having left the worker and a `setsid` grandchild running.
    deadline = config["deadline"]["seconds"]
    # Configurable so a regression can exercise the host bound without waiting a real minute for
    # it. Production leaves it alone; the in-boundary monitor must get its full chance first.
    margin = config["deadline"].get("host_margin_seconds", TEARDOWN_MARGIN_SECONDS)
    grace = config["deadline"].get("teardown_grace_seconds", TEARDOWN_GRACE_SECONDS)
    outer = deadline + margin
    runtime_root = Path(config["home"]).parent
    termination = None
    timed_out = False
    try:
        done = subprocess.run(argv, env=env, capture_output=True, text=True, check=False,
                              timeout=outer)
    except subprocess.TimeoutExpired as expired:
        timed_out = True
        termination = stop_attempt(runtime_root, run_root, grace=grace)
        done = subprocess.CompletedProcess(
            argv, 124,
            (expired.stdout or b"").decode(errors="replace") if isinstance(expired.stdout, bytes)
            else (expired.stdout or ""),
            (expired.stderr or b"").decode(errors="replace") if isinstance(expired.stderr, bytes)
            else (expired.stderr or ""))
    except OSError as exc:
        # subprocess did not create the launcher; retain that observed pre-execution failure.
        ledger.classify(slot["slot"], run_root=run_root, event_dir=None,
                        launcher_returncode=2, launcher_output=str(exc))
        return refuse(str(exc))

    # Even when the launcher exits on its own, it may have left the worker behind: it exits on its
    # deadline whether or not the signal it sent could be delivered. A sweep that finds nothing is
    # cheap; assuming there is nothing to find is how the orphans happened.
    if termination is None:
        swept = stop_attempt(runtime_root, run_root, grace=grace)
        if not swept.get("nothing_was_running"):
            termination = swept
    payload = None
    if done.stdout.strip().startswith("{"):
        try:
            payload = json.loads(done.stdout)
        except ValueError:
            payload = None
    event_dir = payload.get("event_dir") if payload else None
    if not event_dir:
        new = {str(p.parent) for p in run_root.rglob("launch-reservation.json")} - before
        if len(new) == 1:
            event_dir = new.pop()
        elif new:
            return {"launched": True, "admitted": True, "unresolved": True,
                    "reason": "multiple new reservations; preserve and reconcile before resuming"}
    classified = ledger.classify(slot["slot"], run_root=run_root, event_dir=event_dir,
                                 launcher_returncode=done.returncode,
                                 launcher_output=(done.stdout + done.stderr).strip())
    result = {"launched": True, "admitted": True, "slot": classified,
              "returncode": done.returncode, "event_dir": event_dir,
              "status": (payload or {}).get("status"),
              "stderr": done.stderr.strip()[-800:] if done.returncode else "",
              "ledger": ledger.describe()}
    if timed_out:
        result["deadline"] = {
            "worker_seconds": deadline, "host_bound_seconds": outer, "expired": True,
            "teardown_grace_seconds": grace,
            "clock": "monotonic on the host controller; a host suspend inflates it, so elapsed "
                     "wall time alone never establishes that the worker was working",
            "note": "the host terminated the attempt; this says nothing about whether the provider "
                    "stopped billing or cancelled work already in flight"}
    if termination is not None:
        result["termination"] = termination
        if survivors_remain(termination):
            # Not a clean attempt. Saying so is the point: an unreadable process table has not
            # established that nothing survived, and spend attributable to a survivor is unknown.
            result["unresolved"] = True
            result["why"] = [termination["summary"]]
    if timed_out:
        receipt(run_root, "attempt deadline", result, phase=phase, task=task, role=role)
    return result



def launch(workdir, *, phase, task, role, inputs=None):
    import fcntl
    path = Path(workdir) / ".launch.lock"
    with path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("another supervised launch owns this run; inspect status")
        return _launch(workdir, phase=phase, task=task, role=role, inputs=inputs)
