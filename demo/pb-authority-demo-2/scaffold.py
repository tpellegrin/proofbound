#!/usr/bin/env python3
"""Scaffolding for `pb-authority-demo-2`. Not an orchestrator.

Mechanical setup, fixture identities, the external-suite holdout, and spend accounting. It launches
no worker and makes no semantic decision: the workflow is driven by `dsd_attempt.py`,
`dsd_state.py`, `pb_ledger.py`, `pb_graph.py`, `pb_freeze.py`, `pb_consistency.py` and
`pb_execution.py`, run by the coordinator.

The accounting here is a repair. The predecessor's `spend()` had three defects, each reproduced
before being fixed:

* it priced whatever usage totals the session happened to hold and called the result
  `complete: true`, so a session with two calls started and one finished was reported as a settled
  figure;
* it treated an absent database as proof that nothing had been spent, so a launch whose session was
  lost looked free;
* it priced at the moment the report ran rather than at the moment the work executed.

Accounting now reconciles the run tree's launch facts against the session's usage and refuses to
call a figure complete unless both agree. The principle is the one the b1 spend work established:
unknown expenditure is unknown, never zero, and it blocks further launches.

    python3 demo/pb-authority-demo-2/scaffold.py identities
    python3 demo/pb-authority-demo-2/scaffold.py setup --into <workdir>
    python3 demo/pb-authority-demo-2/scaffold.py withhold|release|check-withholding
    python3 demo/pb-authority-demo-2/scaffold.py spend|admit --into <workdir>
    python3 demo/pb-authority-demo-2/scaffold.py external|project-suite --into <workdir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(ROOT / "scripts"))

FIXTURE = HERE / "fixture"
EXTERNAL = HERE / "external-suite"
INTENT = HERE / "intent.md"
CONTRACTS = HERE / "contracts"

MODEL = "deepseek/deepseek-v4-flash"
VARIANT = "high"

#: The launch-admission guard for this demonstration. Not a provider billing cap.
AGGREGATE_LIMIT = 0.40
RESERVE = 0.10

RUN_RELATIVE = Path("DeepSeekAndDestroy/plans/demo2/runs/r1")


def digest_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest_tree(root: Path) -> str:
    acc = hashlib.sha256()
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        acc.update(path.relative_to(root).as_posix().encode()); acc.update(b"\0")
        acc.update(path.read_bytes()); acc.update(b"\0")
    return acc.hexdigest()


def sh(argv: "list[Any]", **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, check=False, **kw)


def identities() -> "dict[str, Any]":
    return {
        "intent_sha256": digest_file(INTENT),
        "fixture_tree_sha256": digest_tree(FIXTURE),
        "fixture_source_sha256": digest_file(FIXTURE / "rateguard" / "__init__.py"),
        "fixture_suite_sha256": digest_file(FIXTURE / "tests" / "test_rateguard.py"),
        "external_suite_sha256": digest_file(EXTERNAL / "test_retry_after_external.py"),
        "witness_sha256": digest_file(EXTERNAL / "witness" / "rateguard" / "__init__.py"),
        "contracts_tree_sha256": digest_tree(CONTRACTS),
        "protocol_sha256": digest_file(HERE / "protocol.md"),
    }


# -- the external-suite holdout ------------------------------------------------------------------
#
# Honest name, because the predecessor's was not. `chmod 0000` denies an ordinary read, and that is
# all it does: the owner may restore the mode without any privilege escalation and then read
# (Apple's chmod(1) — the file owner may always change a file's mode). So this is a *withholding*
# measure against a worker that does not think to look, not a boundary against one that does. The
# real isolation mechanism in this repository is the semantic view, and these runs are deliberately
# outside it. `check-withholding` reports what was actually observed rather than a label.

def withhold() -> "dict[str, Any]":
    for cache in sorted(Path(EXTERNAL).rglob("__pycache__"), reverse=True):
        shutil.rmtree(cache, ignore_errors=True)
    for base, dirs, files in os.walk(EXTERNAL, topdown=False):
        for name in files:
            os.chmod(Path(base) / name, 0o000)
        for name in dirs:
            os.chmod(Path(base) / name, 0o000)
    os.chmod(EXTERNAL, 0o000)
    return check_withholding(expect_withheld=True)


def release() -> "dict[str, Any]":
    os.chmod(EXTERNAL, 0o700)
    for base, dirs, files in os.walk(EXTERNAL, topdown=True):
        for name in dirs:
            os.chmod(Path(base) / name, 0o700)
        for name in files:
            os.chmod(Path(base) / name, 0o600)
    return check_withholding(expect_withheld=False)


def check_withholding(*, expect_withheld: bool = True) -> "dict[str, Any]":
    """What is actually true right now, including what the measure does not prevent."""
    target = EXTERNAL / "test_retry_after_external.py"
    try:
        with open(target, "rb"):
            readable, error = True, None
    except PermissionError as exc:
        readable, error = False, f"PermissionError(errno={exc.errno})"
    except OSError as exc:                                   # pragma: no cover
        readable, error = False, f"{type(exc).__name__}(errno={exc.errno})"
    mode = stat.S_IMODE(os.stat(EXTERNAL).st_mode) if EXTERNAL.exists() else None
    record = {
        "ordinary_read_denied": not readable,
        "read_attempt": error or "succeeded",
        "dir_mode": oct(mode) if mode is not None else None,
        "uid": os.getuid(),
        "owner_can_restore_mode_without_privilege": True,
        "therefore": "withholding, not isolation: an unprivileged owner may chmod and read",
        "as_expected": (not readable) == expect_withheld,
    }
    if not record["as_expected"]:
        raise SystemExit(f"external-suite withholding is not in the expected state: {record}")
    return record


# -- setup ---------------------------------------------------------------------------------------

def setup(into: Path) -> "dict[str, Any]":
    into = into.expanduser().resolve()
    project = into / "project"
    if project.exists():
        raise SystemExit(f"{project} already exists; setup refuses to overwrite a run in progress")
    project.mkdir(parents=True)

    shutil.copytree(FIXTURE, project, dirs_exist_ok=True)
    shutil.copyfile(INTENT, project / "intent.md")
    (project / "PLAN.md").write_text(
        "# Plan\n\nOne accepted change: `retry_after` on `RateGuard`. See `intent.md`.\n",
        encoding="utf-8")

    for argv in (["git", "init", "-q"], ["git", "config", "user.email", "demo@test.invalid"],
                 ["git", "config", "user.name", "pb-authority-demo"],
                 ["git", "add", "-A"], ["git", "commit", "-qm", "initial rateguard"]):
        done = sh(argv, cwd=project)
        if done.returncode != 0:
            raise SystemExit(f"git setup failed: {argv}: {done.stdout}{done.stderr}")

    run = project / RUN_RELATIVE
    run.mkdir(parents=True)
    prep = sh([sys.executable, ROOT / "scripts" / "prepare_worker_rules.py",
               "--project-root", project, "--run-root", run, "--plan", project / "PLAN.md"])
    if prep.returncode != 0:
        raise SystemExit(f"prepare_worker_rules failed: {prep.stderr[:400]}")

    db = into / "session" / "worker.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    (run / "state.json").write_text(json.dumps({
        "project_worktree": str(project),
        "execution_status": "active",
        "next_action": "bind the specification contract",
        "worker_rules": json.loads(prep.stdout),
        "worker_runtime": {"harness": "opencode-cli", "model": MODEL,
                           "opencode": {"run_db": str(db)}},
        "phases": {"design": {"status": "in-progress", "tasks": {}},
                   "build": {"status": "pending", "tasks": {}}},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    from _change_graph import GRAPH_FORMAT, canonical_graph_text
    (into / "ledger.json").write_text(
        json.dumps({"format": "proofbound-change-ledger-v1",
                    "artifact_identity": "proofbound-artifact-text-v1",
                    "artifacts": {}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # `spec.md` alone. The parent intent cannot be a graph member: every ledger record requires an
    # accepted clean gate and a review, and parent authority has neither. It stays external
    # authority, named in each contract and digest-checkable at the handoff. The graph is held
    # stable through implementation — implementation output is deliberately *not* inserted into it
    # to make the ledger look complete.
    (project / "change-graph.json").write_text(
        canonical_graph_text({"format": GRAPH_FORMAT, "artifacts": {"spec.md": []}}),
        encoding="utf-8")

    contracts = run / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONTRACTS / "RG-spec.md", contracts / "RG-spec.md")

    return {"project": str(project), "run_root": str(run), "db": str(db),
            "ledger": str(into / "ledger.json"),
            "graph": str(project / "change-graph.json"),
            "task_contracts": str(contracts),
            "freezes": str(_mkdir(into / "freezes")),
            "consistency": str(_mkdir(into / "consistency")),
            "head": sh(["git", "rev-parse", "HEAD"], cwd=project).stdout.strip(),
            "identities": identities()}


def _mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


# -- correctness ---------------------------------------------------------------------------------

def project_suite(into: Path) -> "dict[str, Any]":
    project = (into / "project").resolve()
    done = sh([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "tests"],
              cwd=project, env={**os.environ, "PYTHONPATH": str(project)})
    return {"returncode": done.returncode, "passed": done.returncode == 0,
            "tail": (done.stderr or done.stdout).strip()[-800:]}


def external(into: Path) -> "dict[str, Any]":
    project = (into / "project").resolve()
    done = sh([sys.executable, "-m", "unittest", "discover", "-s", EXTERNAL, "-t", EXTERNAL],
              env={**os.environ, "PYTHONPATH": str(project)})
    return {"returncode": done.returncode, "passed": done.returncode == 0,
            "tail": (done.stderr or done.stdout).strip()[-2000:]}


# -- accounting ----------------------------------------------------------------------------------

def launch_facts(into: Path) -> "dict[str, Any]":
    """What the run tree says was launched, independent of any session database.

    This is the half the predecessor's accounting lacked. Usage alone cannot say whether a launch
    is missing from it; only the attempts the run tree records can.
    """
    run = (into / "project" / RUN_RELATIVE)
    attempts = []
    for attempt_json in sorted(run.rglob("attempt.json")):
        try:
            data = json.loads(attempt_json.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            attempts.append({"event_dir": str(attempt_json.parent), "readable": False})
            continue
        terminal_path = attempt_json.parent / "terminal.json"
        terminal: "dict[str, Any]" = {}
        if terminal_path.is_file():
            try:
                terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                terminal = {"unreadable": True}
        attempts.append({
            "event_dir": attempt_json.parent.name,
            "readable": True,
            "started_at": data.get("started_at"),
            "session_id": terminal.get("session_id"),
            "terminal_status": terminal.get("status"),
            "terminal_present": bool(terminal),
        })
    return {"attempts": attempts, "launched": len(attempts)}


def _priced_at(facts: "dict[str, Any]") -> datetime:
    """The instant the work executed, not the instant a report happens to run."""
    stamps = [a.get("started_at") for a in facts["attempts"] if a.get("started_at")]
    for raw in sorted(stamps):
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:                                   # pragma: no cover
            continue
    return datetime.now(tz=timezone.utc)


def spend(into: Path) -> "dict[str, Any]":
    """What this run has spent, and whether that figure can be established at all."""
    import _pricing
    import _profile

    facts = launch_facts(into)
    db = (into / "session" / "worker.db").resolve()
    account: "dict[str, Any]" = {"launched_attempts": facts["launched"],
                                 "attempts": facts["attempts"],
                                 "limit": AGGREGATE_LIMIT, "reserve": RESERVE}

    if not db.is_file():
        # An absent database is not evidence of an absent charge. It is only evidence of an absent
        # database, and which of the two it means depends on whether anything was launched.
        if facts["launched"] == 0:
            return {**account, "derived": 0.0, "complete": True,
                    "claim": "nothing has been launched, so nothing has been spent"}
        return {**account, "derived": 0.0, "complete": False,
                "claim": f"{facts['launched']} attempt(s) were launched and no session database "
                         "exists; what they spent is unknown, not zero"}

    stage = _profile.profile(db, stage="implementer", model=MODEL, variant=VARIANT,
                             elapsed_seconds=0.0, verification_seconds=0.0)
    usage = dict(stage.get("usage") or {})
    account["usage"] = usage
    started = usage.get("calls_started")
    finished = usage.get("calls_finished")

    unsettled = []
    if isinstance(started, int) and isinstance(finished, int) and started != finished:
        unsettled.append(f"{started - finished} of {started} model call(s) started and did not "
                         "finish, so their usage is not in these totals")
    missing_terminal = [a["event_dir"] for a in facts["attempts"]
                        if a.get("readable") and not a.get("terminal_present")]
    if missing_terminal:
        unsettled.append(f"attempt(s) without a terminal record: {missing_terminal}")
    unreadable = [a["event_dir"] for a in facts["attempts"] if not a.get("readable")]
    if unreadable:
        unsettled.append(f"attempt(s) whose record is unreadable: {unreadable}")
    interrupted = [a["event_dir"] for a in facts["attempts"]
                   if a.get("terminal_present") and a.get("terminal_status") not in
                   (None, "completed")]
    if interrupted:
        unsettled.append(f"attempt(s) that did not complete: {interrupted}")
    sessions = {a.get("session_id") for a in facts["attempts"] if a.get("session_id")}
    if facts["launched"] and not sessions:
        unsettled.append("no attempt recorded a session id, so usage cannot be attributed to a "
                         "launch")

    priced = _pricing.cost(usage, model=MODEL.split("/", 1)[-1], when=_priced_at(facts))
    amount = (priced or {}).get("amount")
    account["priced_at"] = _priced_at(facts).isoformat()
    if not isinstance(amount, (int, float)):
        return {**account, "derived": 0.0, "complete": False,
                "claim": "a session exists but no usage could be priced; spend is unknown, not "
                         "zero"}
    account["cost"] = priced
    if unsettled:
        return {**account, "derived": round(float(amount), 6), "complete": False,
                "claim": "the derived figure omits work this run cannot account for — "
                         + "; ".join(unsettled)}
    return {**account, "derived": round(float(amount), 6), "complete": True,
            "headroom": round(AGGREGATE_LIMIT - RESERVE - float(amount), 6),
            "claim": "the run tree's launches and the session's usage agree; the figure is the "
                     "whole of what this run spent"}


def admit(into: Path) -> "dict[str, Any]":
    """Whether another paid launch is permitted. Unestablished spend refuses."""
    account = spend(into)
    if not account["complete"]:
        return {"admit": False, "why": "this run's spend cannot be established", "spend": account}
    if account["derived"] + RESERVE > AGGREGATE_LIMIT:
        return {"admit": False,
                "why": f"derived {account['derived']} + reserve {RESERVE} exceeds "
                       f"{AGGREGATE_LIMIT}", "spend": account}
    return {"admit": True, "spend": account}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["identities", "setup", "withhold", "release",
                                        "check-withholding", "spend", "admit", "external",
                                        "project-suite", "launch-facts"])
    ap.add_argument("--into", type=Path, default=None)
    args = ap.parse_args()
    needs = {"setup", "spend", "admit", "external", "project-suite", "launch-facts"}
    if args.command in needs and not args.into:
        raise SystemExit(f"{args.command} needs --into <workdir>")

    table = {
        "identities": lambda: identities(),
        "setup": lambda: setup(args.into),
        "withhold": withhold,
        "release": release,
        "check-withholding": lambda: check_withholding(expect_withheld=True),
        "spend": lambda: spend(args.into),
        "admit": lambda: admit(args.into),
        "external": lambda: external(args.into),
        "project-suite": lambda: project_suite(args.into),
        "launch-facts": lambda: launch_facts(args.into),
    }
    print(json.dumps(table[args.command](), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
