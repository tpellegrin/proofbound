#!/usr/bin/env python3
"""`pb-lifecycle-field-check-1` — two real-executor trials against the repaired deadline.

> **This spends money.** Two provider-backed attempts, under the aggregate limit the protocol
> declares. It is not part of the deterministic suite and `python3 -m unittest discover` never
> reaches it.

The protocol it implements is
`docs/architecture/proofbound/evidence/lifecycle-field-check.md`, committed before this ran. Read
that for what the trials are, what counts as a pass and what a pass would and would not establish.
Everything here is mechanical: it resolves the configuration, observes processes, and writes down
what happened. It decides nothing.

    /usr/bin/python3 evals/pb_lifecycle_field_check.py \\
        --executor ~/.proofbound/executors/opencode-1.18.29-darwin-arm64/opencode \\
        --credential .local/share/opencode/auth.json=$HOME/.local/share/opencode/auth.json \\
        --keep ~/.proofbound/evidence/lifecycle-field-check \\
        --out <evidence>.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _mlr             # noqa: E402
import _mlr_boundary    # noqa: E402
import _mlr_run         # noqa: E402
import _mlr_series      # noqa: E402
import _semantic_view   # noqa: E402

#: The frozen executor, by content. Verified rather than trusted, as the protocol's configuration section requires.
FROZEN_EXECUTOR_SHA256 = "2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669"

#: The disposable workspace. Fixture B's `contract` arm, used as scaffolding; the protocol's
#: *What is being exercised* section says why that is not a re-run of anything.
FIXTURE = ROOT / "evals" / "craft" / "modularity-local-reasoning" / "fixture-b"
ARM = "contract"

MODEL = "deepseek/deepseek-v4-flash"
VARIANT = "high"

AGGREGATE_LIMIT = 0.20
RESERVE = 0.05

#: The command trial B asks the worker to run. A declared test condition: a tool call that does not
#: return, which is the ordinary shape of a stuck one.
STALL_COMMAND = '/usr/bin/python3 -c "import time; time.sleep(900)"'

TRIVIAL_TASK = """# Task — write one file

Create a file named `FIELD_CHECK.txt` in the root of this workspace containing exactly this line:

```
pb-lifecycle-field-check-1 trial A
```

Do nothing else. Do not modify any other file, do not run the test suite, and stop as soon as the
file exists.
"""

STALL_TASK = f"""# Task — run one long command and wait for it

This is an engineering check of process lifecycle handling, not a software change. The blocking
command below is the point of the task.

Run exactly this command in the workspace and wait for it to finish:

```
{STALL_COMMAND}
```

It will not finish quickly. Wait for it. Do not run it in the background, do not add a timeout, do
not kill it, and do not do anything else while waiting. Report only once it has returned.
"""


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def process_snapshot() -> list[dict[str, Any]]:
    """Every process, with its group and command line, or an empty list if `ps` failed."""
    try:
        done = subprocess.run(["/bin/ps", "-Ao", "pid=,ppid=,pgid=,command="],
                              capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    rows = []
    for line in done.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) >= 3 and parts[0].isdigit():
            rows.append({"pid": int(parts[0]), "ppid": int(parts[1]), "pgid": int(parts[2]),
                         "command": parts[3] if len(parts) > 3 else ""})
    return rows


def sleep_transitions(since: float) -> list[str]:
    """`Sleep` lines the power log recorded after `since`. Verified, never assumed."""
    try:
        done = subprocess.run(["pmset", "-g", "log"], capture_output=True, text=True,
                              check=False, timeout=120)
    except (OSError, subprocess.SubprocessError):            # pragma: no cover
        return ["pmset unavailable"]
    import datetime
    found = []
    for line in done.stdout.splitlines():
        if " Sleep  " not in line and "\tSleep" not in line:
            continue
        stamp = line[:19]
        try:
            when = datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            continue
        if when >= since:
            found.append(line.strip()[:160])
    return found


class Watcher:
    """Samples the process table while a trial runs, so activity is observed and not inferred.

    Two things have to be seen with their own eyes rather than read off a report: that the real
    staged executor was running, and that the tool it started was running, both *before* the
    deadline expired.
    """

    def __init__(self, interval: float = 0.25):
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.executor_sightings: list[dict[str, Any]] = []
        self.stall_sightings: list[dict[str, Any]] = []
        self.last_attempt_signature: list[dict[str, Any]] = []
        self.samples = 0

    def _sample(self) -> None:
        while not self._stop.is_set():
            rows = process_snapshot()
            self.samples += 1
            signature = []
            for row in rows:
                command = row["command"]
                if "/pb-tool-" in command and "opencode" in command:
                    if not self.executor_sightings:
                        self.executor_sightings.append({**row, "at": time.time()})
                    signature.append(row)
                elif "time.sleep(900)" in command:
                    if not self.stall_sightings:
                        self.stall_sightings.append({**row, "at": time.time()})
                    signature.append(row)
                elif "pb-sem-" in command or "wait_worker" in command:
                    signature.append(row)
            if signature:
                self.last_attempt_signature = [
                    {k: row[k] for k in ("pid", "pgid", "command")} for row in signature]
            self._stop.wait(self.interval)

    def __enter__(self) -> "Watcher":
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)


def attempt_signature(rows: list[dict[str, Any]]) -> dict[int, str]:
    """Live processes that look like they belong to some attempt, by pid."""
    keys = ("pb-sem-", "pb-tool-", "wait_worker", "time.sleep(900)", "run_worker.py")
    return {row["pid"]: row["command"][:120] for row in rows
            if any(k in row["command"] for k in keys)}


def residue() -> dict[str, Any]:
    import tempfile
    return {
        "stale_views": [str(p) for p in _semantic_view.stale_views()],
        "ephemeral_arms": [str(p) for p in _mlr.ephemeral_materialisations(
            [Path(tempfile.gettempdir()), Path("/tmp")])],
    }


def run_trial(name: str, task_text: str, *, timeout: int, executor: Path,
              credentials: dict[str, Path], keep: Path,
              watch: bool) -> "tuple[dict[str, Any], dict[str, Any]]":
    """One paid trial, with the processes observed while it runs."""
    task_file = keep / f"{name}-task.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(task_text, encoding="utf-8")

    before_rows = process_snapshot()
    before = attempt_signature(before_rows)
    record: dict[str, Any] = {
        "trial": name, "deadline_seconds": timeout,
        "task_sha256": digest(task_file),
        "residue_before": residue(),
        "attempt_signature_before": before,
        "started_wall": time.time(),
    }

    started = time.monotonic()
    watcher = Watcher() if watch else None
    try:
        if watcher is not None:
            watcher.__enter__()
        attempt = _mlr_boundary.run_bounded_attempt(
            ARM, model=MODEL, variant=VARIANT, executor=executor,
            credentials=credentials, keep=keep, fixture=FIXTURE, task=task_file,
            timeout=timeout)
    finally:
        if watcher is not None:
            watcher.__exit__()
    record["wall_seconds"] = round(time.monotonic() - started, 3)

    if watcher is not None:
        record["observation"] = {
            "samples": watcher.samples,
            "executor_seen_running": watcher.executor_sightings[:1],
            "stall_child_seen_running": watcher.stall_sightings[:1],
            "attempt_signature_at_last_sighting": watcher.last_attempt_signature,
        }

    # Survivors: anything attempt-shaped that was not running before this trial began.
    def leaked() -> dict[int, str]:
        now = attempt_signature(process_snapshot())
        return {pid: cmd for pid, cmd in now.items() if pid not in before}

    deadline = time.monotonic() + 60.0
    while time.monotonic() < deadline and leaked():
        time.sleep(0.25)
    record["leaked_after_observation"] = leaked()
    record["residue_after"] = residue()

    keep_keys = ("validity", "reason", "timed_out", "terminal_status",
                 "attempt_deadline_seconds", "worker_monotonic_seconds", "worker_wall_seconds",
                 "termination", "monitor_termination", "trajectory_began", "launch_returncode",
                 "extraction", "view_destroyed", "evidence", "elapsed_seconds", "cost",
                 "interrupted")
    record["attempt"] = {k: attempt.get(k) for k in keep_keys if k in attempt}
    record["execution_stage"] = _mlr_series.execution_stage(attempt)
    record["spend"] = _mlr_series.spend([attempt])
    outcome = attempt.get("outcome")
    if isinstance(outcome, dict):
        # Recorded, and meaningless here: fixture B's oracle judging work that was never asked to
        # satisfy it. The protocol says why it is ignored.
        record["oracle_verdict_ignored"] = {k: outcome.get(k) for k in
                                            ("correct", "gate_passed", "regression_passed")}
    return record, attempt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--executor", type=Path, required=True)
    ap.add_argument("--credential", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--keep", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--trial-a-deadline", type=int, default=300)
    ap.add_argument("--trial-b-deadline", type=int, default=90)
    args = ap.parse_args()

    executor = args.executor.expanduser().resolve()
    observed = digest(executor)
    if observed != FROZEN_EXECUTOR_SHA256:
        print(json.dumps({"blocked": "the staged executable is not the verified executor",
                          "observed": observed, "required": FROZEN_EXECUTOR_SHA256}, indent=2))
        return 2

    credentials: dict[str, Path] = {}
    for pair in args.credential:
        name, _, path = pair.partition("=")
        if not name or not path:
            raise SystemExit(f"--credential expects NAME=PATH, got {pair!r}")
        credentials[name] = Path(path).expanduser()

    keep = args.keep.expanduser()
    keep.mkdir(parents=True, exist_ok=True)

    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=False)
    report: dict[str, Any] = {
        "identity": "pb-lifecycle-field-check-1",
        "protocol": "docs/architecture/proofbound/evidence/lifecycle-field-check.md",
        "execution_commit": head.stdout.strip() or None,
        "executor": {"path": str(executor), "sha256": observed, "verified": True},
        "interpreter": _mlr.interpreter_identity(),
        "model": MODEL, "variant": VARIANT,
        "aggregate_limit": AGGREGATE_LIMIT, "reserve": RESERVE,
        "started_wall": time.time(),
        "trials": [],
    }
    window_start = time.time()

    first = residue()
    if first["stale_views"] or first["ephemeral_arms"]:
        report["blocked"] = "host residue present before the first trial"
        report["residue"] = first
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"blocked": report["blocked"], "residue": first}, indent=2))
        return 2

    attempts: list[dict[str, Any]] = []

    a_record, a_attempt = run_trial("trial-a-normal-completion", TRIVIAL_TASK,
                                    timeout=args.trial_a_deadline, executor=executor,
                                    credentials=credentials, keep=keep, watch=False)
    report["trials"].append(a_record)
    attempts.append(a_attempt)

    account = _mlr_series.spend(attempts)
    report["spend_after_trial_a"] = account
    if not account["complete"] or account["derived"] + RESERVE > AGGREGATE_LIMIT:
        report["trial_b"] = ("not launched: spend after trial A is "
                             + ("incomplete" if not account["complete"] else "too close to the "
                                f"limit ({account['derived']} + {RESERVE} > {AGGREGATE_LIMIT})"))
        report["verdict"] = "blocked"
    else:
        b_record, b_attempt = run_trial("trial-b-controlled-stall", STALL_TASK,
                                        timeout=args.trial_b_deadline, executor=executor,
                                        credentials=credentials, keep=keep, watch=True)
        report["trials"].append(b_record)
        attempts.append(b_attempt)

    report["spend_total"] = _mlr_series.spend(attempts)
    report["sleep_transitions_during_run"] = sleep_transitions(window_start)
    report["finished_wall"] = time.time()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    printable = {k: v for k, v in report.items() if k != "trials"}
    printable["trial_summaries"] = [
        {"trial": t["trial"], "wall_seconds": t["wall_seconds"],
         "validity": t["attempt"].get("validity"), "timed_out": t["attempt"].get("timed_out"),
         "stage": t["execution_stage"], "leaked": t["leaked_after_observation"]}
        for t in report["trials"]]
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
