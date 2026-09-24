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


#: How often the host reads the attempt's session while it runs. Reads are read-only. A limit can
#: be passed by the requests made within one interval: observed, a stand-in that answered as fast
#: as the executor re-requested reached 10 against a limit of 5 at a 1 s interval.
WATCH_POLL_SECONDS = 0.5

#: Finish reasons the pinned executor records when a response ended without one of its own.
INCOMPLETE_REASONS = frozenset({"unknown", "other", "error"})


class AttemptWatch:
    """Host-side containment of one attempt, read from the session database it is writing.

    The pinned executor re-requests a response that ended without a finish reason at once and
    without limit — observed as 4,649 requests in 900 s — and its agent `steps` limit does not
    count those. The deadline alone bounds that only in time. This counts, from the parts written
    since the attempt began: model requests (`step-start`), the trailing run of responses whose
    finish reason is missing or `unknown`, and — for a priced worker — the derived spend of the
    calls that finished. Any one past its limit stops the attempt through the host teardown.

    What it cannot see it does not claim: a call still in flight has no usage yet, and a call the
    executor records with zero tokens has none at all. The derived limit is enforced up to those.
    """

    def __init__(self, db, *, containment, spend_room=None, table=None, price_model=None):
        self.db = Path(db)
        self.limits = dict(containment)
        self.spend_room = spend_room
        self.table, self.price_model = table, price_model
        self.baseline = self._max_rowid()

    def _connect(self):
        import sqlite3
        return sqlite3.connect(f"file:{self.db}?mode=ro", uri=True, timeout=1)

    def _max_rowid(self) -> int:
        import sqlite3
        if not self.db.is_file():
            return 0
        try:
            conn = self._connect()
            try:
                return int(conn.execute("select coalesce(max(rowid), 0) from part").fetchone()[0])
            finally:
                conn.close()
        except sqlite3.Error:
            return 0

    def _parts(self):
        import sqlite3
        if not self.db.is_file():
            return []
        try:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "select p.id, p.message_id, p.data, m.time_created from part p "
                    "join message m on m.id = p.message_id where p.rowid > ? "
                    "order by p.rowid", (self.baseline,)).fetchall()
            finally:
                conn.close()
        except sqlite3.Error:
            return None                         # mid-write or locked: read again next poll
        out = []
        for part_id, message_id, raw, created in rows:
            try:
                part = json.loads(raw)
            except (TypeError, ValueError):
                continue
            out.append((part_id, message_id, part, created))
        return out

    def check(self):
        """The first rule broken, with what was observed, or None."""
        parts = self._parts()
        if not parts:
            return None
        requests = sum(1 for _i, _m, part, _t in parts if part.get("type") == "step-start")
        finishes = [part for _i, _m, part, _t in parts if part.get("type") == "step-finish"]
        trailing = 0
        for part in reversed(finishes):
            if part.get("reason") in INCOMPLETE_REASONS or not part.get("reason"):
                trailing += 1
            else:
                break
        limit = self.limits.get("max_model_requests")
        if limit is not None and requests > limit:
            return {"rule": "max_model_requests", "observed": requests, "limit": limit}
        limit = self.limits.get("max_consecutive_incomplete_responses")
        if limit is not None and trailing >= limit:
            return {"rule": "max_consecutive_incomplete_responses", "observed": trailing,
                    "limit": limit}
        if self.spend_room is not None and self.table is not None:
            import _worker_pricing
            rows = []
            for part_id, message_id, part, created in parts:
                if part.get("type") != "step-finish":
                    continue
                tokens = part.get("tokens") or {}
                cache = tokens.get("cache") or {}
                rows.append({"type": "step-finish", "part_id": part_id,
                             "message_id": message_id, "time_created": created,
                             "input": tokens.get("input"), "output": tokens.get("output"),
                             "cache_read": cache.get("read")})
            priced = _worker_pricing.cost_rows(rows, model=self.price_model, table=self.table)
            amount = priced.get("amount")
            if isinstance(amount, (int, float)) and amount > self.spend_room:
                return {"rule": "derived_spend_during_attempt", "observed": round(amount, 6),
                        "limit": round(self.spend_room, 6)}
        return None

def _ledger(workdir: Path, config: "dict[str, Any]", settings: "dict[str, Any]") -> LaunchLedger:
    return LaunchLedger(workdir / "launch-ledger.json",
                        limit=config["policy"]["aggregate_limit"],
                        reserve=config["policy"]["reserve"],
                        ceiling=config["policy"]["launch_ceiling"],
                        repair_cycles=config["policy"].get("repair_cycles", 1),
                        billing=settings["billing"],
                        output_token_allowance=settings["resources"]["output_token_allowance"])


def _launch(workdir: "str | Path", *, phase: str, task: str, role: str,
           inputs: "list[str] | None" = None, progress=None) -> "dict[str, Any]":
    """The supervised path to the configured worker executor.

    Admit, reserve the slot durably, run the shipped launcher, then classify from evidence. A
    refusal returns without launching anything and says which rule refused. `progress` receives
    the stage reached and what a recovery would need to resume supervision (`_supervision`).
    """
    from _worker_profiles import of
    import time
    from datetime import datetime, timedelta, timezone
    workdir = Path(workdir).expanduser().resolve()
    config = json.loads((workdir / "run-config.json").read_text())
    settings = of(config)
    local = settings["network"]["mode"] == "loopback-only"
    run_root = Path(config["paths"]["run_root"])
    db = Path(config["paths"]["session_db"])
    ledger = _ledger(workdir, config, settings)

    def note(**fields):
        if progress is not None:
            progress(fields)

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

    # How the executor will start. A run whose settings record a start-up policy is refused, before
    # a slot is reserved, from any state in which the executor would start differently: a cached
    # catalogue that deprecates the requested model, an install or lock left by an earlier executor
    # process, configuration it would load and install into. Earlier runs record no policy.
    startup = settings["executor"].get("startup")
    if startup:
        import _executor_startup
        boundary = Path(config.get("boundary_profile") or "/nonexistent")
        started_from = _executor_startup.observe(config["home"], config["paths"]["project"])
        why = _executor_startup.problems(
            started_from, home=config["home"], bounded=bool(config.get("boundary_profile")),
            boundary_text=boundary.read_text() if boundary.is_file() else None)
        if why:
            return refuse("refusing to launch: the executor would not start as this run's "
                          "settings record: " + "; ".join(why))

    if local:
        # The executor must read exactly the configuration recorded at start. A missing or moved
        # file would let OpenCode fall back to its defaults — a hosted model — without anything
        # in the record changing.
        pinned = config.get("opencode_config") or {}
        path = Path(pinned.get("path") or "/nonexistent")
        if (not path.is_file() or digest_file(path) != pinned.get("sha256")
                or (config.get("worker_env") or {}).get("OPENCODE_CONFIG") != str(path)):
            return refuse("refusing to launch: the local worker's executor configuration is "
                          "missing or no longer matches the bytes recorded at start")

    executor_dir = str(Path(config["executor"]["path"]).parent)
    # A local worker gets a minimal environment in every mode: an ambient provider key or
    # `OPENCODE_*` variable must not be able to select a different service.
    env = ({"LANG": "en_US.UTF-8", "TMPDIR": str(Path(config["home"]).parent / "tmp")}
           if config.get("boundary_profile") or local else
           {k: v for k, v in os.environ.items() if not k.startswith("OPENCODE")})
    env["PATH"] = os.pathsep.join([executor_dir, "/usr/bin", "/bin", "/usr/sbin", "/sbin"])
    env["HOME"] = config["home"]
    env.update(config.get("worker_env") or {})
    if startup:
        env.update(_executor_startup.ENV)
    resolved = shutil.which("opencode", path=env["PATH"])
    if resolved != config["executor"]["path"]:
        return refuse(f"refusing to launch: `opencode` resolves to {resolved}, not the frozen "
                         f"executor {config['executor']['path']}")
    if digest_file(resolved) != config["executor"]["sha256"]:
        return refuse("refusing to launch: the resolved executor's bytes are not the frozen "
                         "identity")

    argv = [sys.executable, str(SCRIPTS / "dsd_attempt.py"), "launch",
            "--run-root", str(run_root), "--phase-id", phase, "--task-id", task,
            "--role", role, "--model", config["model"],
            f"--auto-flag={config['auto_flag']}",
            "--timeout", str(config["deadline"]["seconds"])]
    if settings["variant"]:
        # Only a provider that defines the variant receives it; `high` means nothing to a local
        # server and must not be sent as though it did.
        argv += ["--variant", settings["variant"]]
    for path in inputs or []:
        argv += ["--input", str(path)]
    if config.get("boundary_profile"):
        argv = ["/usr/bin/sandbox-exec", "-f", config["boundary_profile"], *argv]
    before = {str(p.parent) for p in run_root.rglob("launch-reservation.json")}
    note(stage="admitted")
    slot = ledger.reserve(phase=phase, task=task, role=role,
                          note=f"{config['mode']} launch of {role} on {phase}/{task}")
    note(stage="reserved", slot=slot["slot"], reserved_at=slot["reserved_at"])

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
    contained = None
    containment = settings["resources"].get("attempt_containment")
    watch = AttemptWatch(
        db, containment=containment,
        spend_room=(config["policy"]["aggregate_limit"] - verdict["derived"]
                    if containment.get("derived_spend_during_attempt")
                    and isinstance(verdict.get("derived"), (int, float)) else None),
        table=_table(settings), price_model=settings["billing"].get("price_model")) \
        if containment else None
    # Wall clock, recorded so a recovery can hold the same bound if this supervisor is lost.
    note(stage="running", host_deadline_at=(datetime.now(timezone.utc)
                                             + timedelta(seconds=outer)).isoformat(),
         watch=({"baseline": watch.baseline, "spend_room": watch.spend_room} if watch else None))
    try:
        if not containment:
            # Runs recorded without containment keep exactly the behaviour they were started with.
            done = subprocess.run(argv, env=env, capture_output=True, text=True, check=False,
                                  timeout=outer)
        else:
            done, timed_out, contained = _watched(argv, env, outer, watch)
            if timed_out or contained:
                termination = stop_attempt(runtime_root, run_root, grace=grace)
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
    swept = None
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
    note(stage="finalizing", event_dir=event_dir)
    classified = ledger.classify(slot["slot"], run_root=run_root, event_dir=event_dir,
                                 launcher_returncode=done.returncode,
                                 launcher_output=(done.stdout + done.stderr).strip())
    if startup and event_dir and Path(event_dir).is_dir():
        _record_state(Path(event_dir), settings, config, before=started_from,
                      launcher_returncode=done.returncode,
                      sweep=termination if termination is not None else swept)
    result = {"launched": True, "admitted": True, "slot": classified,
              "returncode": done.returncode, "event_dir": event_dir,
              "status": (payload or {}).get("status"),
              "stderr": done.stderr.strip()[-800:] if done.returncode else "",
              "ledger": ledger.describe()}
    return _conclude(result, run_root=run_root, phase=phase, task=task, role=role, local=local,
                     settings=settings, deadline=deadline, outer=outer, grace=grace,
                     timed_out=timed_out, contained=contained, termination=termination)


def _conclude(result, *, run_root, phase, task, role, local, settings, deadline, outer, grace,
              timed_out, contained, termination):
    """What every finalized attempt reports about its deadline, containment and teardown."""
    if timed_out:
        result["deadline"] = {
            "worker_seconds": deadline, "host_bound_seconds": outer, "expired": True,
            "teardown_grace_seconds": grace,
            "clock": "monotonic on the host controller; a host suspend inflates it, so elapsed "
                     "wall time alone never establishes that the worker was working",
            "note": "the host terminated the attempt; this says nothing about whether the provider "
                    "stopped billing or cancelled work already in flight"}
    if contained:
        result["containment"] = {
            **contained, "stopped_by": "host controller, before the deadline",
            "note": "the host stopped this attempt; whether the provider billed or kept generating "
                    "for a request in flight is unknown, and a stopped attempt is not a result"}
        result["unresolved"] = True
        result.setdefault("why", []).append(
            f"containment: {contained['rule']} observed {contained['observed']} against "
            f"{contained['limit']}")
        receipt(run_root, "attempt containment", result, phase=phase, task=task, role=role)
    if local and (timed_out or termination is not None):
        # The inference server is shared and long-lived; this attempt never owned it, so teardown
        # never signals it (ownership requires the runtime path in a command line). Stopping the
        # client is not cancellation.
        result["server"] = {
            "owned_by_attempt": False, "signalled": False,
            "cancellation": "unknown: terminating the worker client does not establish that the "
                            "server stopped generating for it",
            "endpoint": settings["provider"]["endpoint"]["url"]}
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


def _record_state(event_dir: Path, settings, config, *, before, launcher_returncode, sweep):
    """Private, beside worker.log: what the executor started from and left behind, and what the
    host found running afterwards. Names, modes, times and digests; no contents."""
    import _executor_startup
    from dsd_state import atomic_json
    atomic_json(Path(event_dir) / "executor-state.json", {
        "format": "proofbound-executor-state-v1", "policy": settings["executor"].get("startup"),
        "before": (before if before is not None
                   else "not observed: the launching supervisor was lost"),
        "after": _executor_startup.observe(config["home"], config["paths"]["project"]),
        "launcher_returncode": launcher_returncode,
        "host_sweep": sweep,
        "executor_log": "worker.log, through OPENCODE_PRINT_LOGS"})



def _table(settings):
    import _worker_pricing
    return _worker_pricing.TABLES.get((settings.get("billing") or {}).get("table"))


def _watched(argv, env, outer, watch):
    """Run the launcher while the host reads its session; stop it on the deadline or a rule.

    Mirrors `subprocess.run(timeout=)` on the deadline — the launcher is killed and reaped before
    teardown — and adds the containment rules. Returns (completed process, timed out, rule broken).
    """
    import time
    proc = subprocess.Popen(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    ends = time.monotonic() + outer
    contained = None
    timed_out = False
    while True:
        try:
            out, err = proc.communicate(timeout=WATCH_POLL_SECONDS)
            return subprocess.CompletedProcess(argv, proc.returncode, out, err), False, None
        except subprocess.TimeoutExpired:
            pass
        if time.monotonic() >= ends:
            timed_out = True
            break
        contained = watch.check()
        if contained:
            break
    proc.kill()
    out, err = proc.communicate()
    return (subprocess.CompletedProcess(argv, 124 if timed_out else 125, out or "", err or ""),
            timed_out, contained)


def launch(workdir, *, phase, task, role, inputs=None):
    """Run one supervised launch in a run-owned supervisor and wait for it (`_supervision`).

    The caller only waits. If it exits, the supervisor finishes the launch; a later `continue` waits
    for that same supervisor rather than launching again.
    """
    import _supervision
    return _supervision.launch(Path(workdir), {"phase": phase, "task": task, "role": role,
                                               "inputs": [str(p) for p in inputs or []]})


def _baseline_before(db: Path, iso: str) -> int:
    """The last session part written before `iso`: where an adopted attempt's own parts begin."""
    import sqlite3
    from datetime import datetime
    try:
        ms = int(datetime.fromisoformat(iso).timestamp() * 1000)
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=1)
        try:
            row = conn.execute("select coalesce(max(p.rowid), 0) from part p join message m "
                               "on m.id = p.message_id where m.time_created < ?", (ms,)).fetchone()
        finally:
            conn.close()
        return int(row[0])
    except (ValueError, TypeError, sqlite3.Error):
        return 0


def _adopt(workdir: "str | Path", adopt: "dict[str, Any]", *, progress=None) -> "dict[str, Any]":
    """Resume host supervision of an attempt whose supervisor was lost, then finalize it.

    The same controls as a launch: containment from the lost supervisor's recorded baseline and
    spend room, or re-derived from the attempt's start; the host deadline it recorded, or else the
    attempt's start plus the run's deadline and margin, else the reservation's; teardown; the
    post-exit sweep; classification from evidence. It never launches and never retries.

    The deadline here is wall clock, since the lost supervisor's monotonic clock is gone. A host
    suspend therefore counts against it.
    """
    from _worker_profiles import of
    from _attempt_teardown import _owned_processes
    from _launch_budget import spend
    import time
    from datetime import datetime, timedelta, timezone
    workdir = Path(workdir).expanduser().resolve()
    config = json.loads((workdir / "run-config.json").read_text())
    settings = of(config)
    local = settings["network"]["mode"] == "loopback-only"
    run_root = Path(config["paths"]["run_root"])
    db = Path(config["paths"]["session_db"])
    runtime_root = Path(config["home"]).parent
    ledger = _ledger(workdir, config, settings)
    deadline = config["deadline"]["seconds"]
    margin = config["deadline"].get("host_margin_seconds", TEARDOWN_MARGIN_SECONDS)
    grace = config["deadline"].get("teardown_grace_seconds", TEARDOWN_GRACE_SECONDS)
    outer = deadline + margin
    since = adopt.get("started_at") or adopt["reserved_at"]
    deadline_at = adopt.get("host_deadline_at") or (
        datetime.fromisoformat(since) + timedelta(seconds=outer)).isoformat()
    slot = next(s for s in ledger.slots if s["slot"] == adopt["slot"])
    containment = settings["resources"].get("attempt_containment")
    watch = None
    if containment:
        recorded = adopt.get("watch") or {}
        room = recorded.get("spend_room")
        if not recorded and containment.get("derived_spend_during_attempt"):
            before = spend(run_root, db, event_dirs=ledger.own_event_dirs(),
                           limit=config["policy"]["aggregate_limit"],
                           reserve=config["policy"]["reserve"], billing=settings["billing"])
            if isinstance(before.get("derived"), (int, float)) and before.get("complete"):
                room = config["policy"]["aggregate_limit"] - before["derived"]
        watch = AttemptWatch(db, containment=containment, spend_room=room, table=_table(settings),
                             price_model=settings["billing"].get("price_model"))
        watch.baseline = (recorded["baseline"] if recorded.get("baseline") is not None
                          else _baseline_before(db, since))
    event_dir = adopt.get("event_dir")
    if progress is not None:
        progress({"stage": "running", "slot": slot["slot"], "event_dir": event_dir,
                  "host_deadline_at": deadline_at,
                  "watch": ({"baseline": watch.baseline, "spend_room": watch.spend_room}
                            if watch else None)})
    claimed = {str(Path(s["event_dir"]).resolve()) for s in ledger.slots if s.get("event_dir")}
    termination, timed_out, contained = None, False, None
    ends = datetime.fromisoformat(deadline_at)
    while True:
        if event_dir is None:
            # The launcher can still create the reservation after its supervisor was lost.
            new = [p.parent for p in run_root.rglob("launch-reservation.json")
                   if str(p.parent.resolve()) not in claimed]
            event_dir = str(new[0]) if len(new) == 1 else None
        recorded_pids = []
        if event_dir and (Path(event_dir) / "attempt.json").is_file():
            try:
                data = json.loads((Path(event_dir) / "attempt.json").read_text())
                recorded_pids = [data[k] for k in ("worker_pid", "launcher_pid")
                                 if isinstance(data.get(k), int)]
            except ValueError:
                pass
        owned = _owned_processes(runtime_root, recorded_pids)
        if not owned["table_unavailable"] and not owned["owned"]:
            break
        if datetime.now(timezone.utc) >= ends:
            timed_out = True
            termination = stop_attempt(runtime_root, run_root, grace=grace)
            break
        if watch is not None:
            contained = watch.check()
            if contained:
                termination = stop_attempt(runtime_root, run_root, grace=grace)
                break
        time.sleep(WATCH_POLL_SECONDS)
    swept = None
    if termination is None:
        swept = stop_attempt(runtime_root, run_root, grace=grace)
        if not swept.get("nothing_was_running"):
            termination = swept
    if progress is not None:
        progress({"stage": "finalizing", "event_dir": event_dir})
    classified = ledger.classify(
        slot["slot"], run_root=run_root, event_dir=event_dir, launcher_returncode=-1,
        launcher_output=("not observed: the launching supervisor was lost; a recovery supervisor "
                         "adopted this attempt, held its controls and finalized it"))
    if settings["executor"].get("startup") and event_dir and Path(event_dir).is_dir():
        _record_state(Path(event_dir), settings, config, before=None, launcher_returncode=None,
                      sweep=termination if termination is not None else swept)
    terminal = {}
    if event_dir and (Path(event_dir) / "terminal.json").is_file():
        try:
            terminal = json.loads((Path(event_dir) / "terminal.json").read_text())
        except ValueError:
            terminal = {}
    result = {"launched": True, "admitted": True, "adopted": True, "slot": classified,
              "returncode": None, "event_dir": event_dir, "status": terminal.get("status"),
              "lost_supervisor": adopt.get("lost_supervisor"), "host_deadline_at": deadline_at,
              "ledger": ledger.describe()}
    if not terminal:
        result["unresolved"] = True
        result.setdefault("why", []).append("the adopted attempt left no readable terminal record; "
                                            "its outcome is unknown")
    receipt(run_root, "supervision adopted", {
        "slot": slot["slot"], "event_dir": event_dir, "host_deadline_at": deadline_at,
        "lost_supervisor": adopt.get("lost_supervisor"), "timed_out": timed_out,
        "contained": contained, "classification": classified["classification"]},
        phase=slot.get("phase"), task=slot.get("task"), role=slot.get("role"))
    return _conclude(result, run_root=run_root, phase=slot.get("phase"), task=slot.get("task"),
                     role=slot.get("role"), local=local, settings=settings, deadline=deadline,
                     outer=outer, grace=grace, timed_out=timed_out, contained=contained,
                     termination=termination)
