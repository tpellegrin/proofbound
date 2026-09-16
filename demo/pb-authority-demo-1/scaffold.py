#!/usr/bin/env python3
"""Scaffolding for `pb-authority-demo-1`. Not an orchestrator.

It does the mechanical setup a person should not hand-roll — creating the disposable project, the
run tree, the worker-rules revision and `state.json` — plus three things the demonstration needs to
be honest: the fixture identities, the external-suite lock, and spend accounting read from the
session the executor actually wrote.

**It launches no worker and makes no semantic decision.** The workflow itself is driven by the
`dsd_attempt.py`, `dsd_state.py`, `pb_ledger.py`, `pb_graph.py`, `pb_freeze.py` and
`pb_consistency.py` commands the committed design names, run by the orchestrator. That separation
is deliberate: a script that drove the roles would be the new orchestrator the design rules out.

    python3 demo/pb-authority-demo-1/scaffold.py identities
    python3 demo/pb-authority-demo-1/scaffold.py setup --into <workdir>
    python3 demo/pb-authority-demo-1/scaffold.py lock|unlock|verify-lock
    python3 demo/pb-authority-demo-1/scaffold.py spend --into <workdir>
    python3 demo/pb-authority-demo-1/scaffold.py external --into <workdir>
    python3 demo/pb-authority-demo-1/scaffold.py project-suite --into <workdir>
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

#: The design's accounting rule, transcribed rather than reinvented.
AGGREGATE_LIMIT = 0.40
RESERVE = 0.10

RUN_RELATIVE = Path("DeepSeekAndDestroy/plans/demo/runs/r1")


def digest_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest_tree(root: Path) -> str:
    """One digest over a directory's relative paths and contents, ignoring caches."""
    accumulator = hashlib.sha256()
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        accumulator.update(path.relative_to(root).as_posix().encode())
        accumulator.update(b"\0")
        accumulator.update(path.read_bytes())
        accumulator.update(b"\0")
    return accumulator.hexdigest()


def sh(argv: list[str], **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, check=False, **kw)


def identities() -> dict[str, Any]:
    return {
        "intent_sha256": digest_file(INTENT),
        "fixture_tree_sha256": digest_tree(FIXTURE),
        "fixture_source_sha256": digest_file(FIXTURE / "rateguard" / "__init__.py"),
        "fixture_suite_sha256": digest_file(FIXTURE / "tests" / "test_rateguard.py"),
        "external_suite_sha256": digest_file(
            EXTERNAL / "test_retry_after_external.py"),
        "reference_sha256": digest_file(
            EXTERNAL / "reference" / "rateguard" / "__init__.py"),
        "design_sha256": digest_file(
            ROOT / "docs/architecture/proofbound/evidence/authority-workflow-demonstration.md"),
        "check_sha256": digest_file(HERE / "design-to-execution-check.md"),
        "contracts_tree_sha256": digest_tree(CONTRACTS),
    }


# -- the external-suite lock ---------------------------------------------------------------------

def lock() -> dict[str, Any]:
    """Deny the external suite to everything, including its owner, for the duration of a run.

    Deepest first, then the root. A directory at mode `0000` cannot be listed, so locking the root
    before its contents would leave the contents unreachable *and* unmodifiable.
    """
    # Compiled copies go first. A `.pyc` of the suite left readable beside a locked `.py` would
    # hand over the assertions the lock exists to withhold.
    for cache in sorted(Path(EXTERNAL).rglob("__pycache__"), reverse=True):
        shutil.rmtree(cache, ignore_errors=True)
    for base, dirs, files in os.walk(EXTERNAL, topdown=False):
        for name in files:
            os.chmod(Path(base) / name, 0o000)
        for name in dirs:
            os.chmod(Path(base) / name, 0o000)
    os.chmod(EXTERNAL, 0o000)
    return verify_lock(expect_locked=True)


def unlock() -> dict[str, Any]:
    """Restore access top-down, opening each directory *before* walking into it.

    A `0000` directory cannot be listed, so a bottom-up pass — or any pass that globs first —
    silently skips everything beneath one and leaves it locked. Found while testing this.
    """
    os.chmod(EXTERNAL, 0o700)
    for base, dirs, files in os.walk(EXTERNAL, topdown=True):
        for name in dirs:
            os.chmod(Path(base) / name, 0o700)
        for name in files:
            os.chmod(Path(base) / name, 0o600)
    return verify_lock(expect_locked=False)


def verify_lock(*, expect_locked: bool) -> dict[str, Any]:
    """Prove the state rather than assume it: actually try to read the suite."""
    target = EXTERNAL / "test_retry_after_external.py"
    try:
        with open(target, "rb"):
            readable = True
            error = None
    except PermissionError as exc:
        readable, error = False, f"PermissionError(errno={exc.errno})"
    except OSError as exc:                                   # pragma: no cover
        readable, error = False, f"{type(exc).__name__}(errno={exc.errno})"
    mode = stat.S_IMODE(os.stat(EXTERNAL).st_mode) if EXTERNAL.exists() else None
    record = {"locked": not readable, "read_attempt": error or "succeeded",
              "dir_mode": oct(mode) if mode is not None else None,
              "uid": os.getuid(), "as_expected": (not readable) == expect_locked}
    if not record["as_expected"]:
        raise SystemExit(f"external-suite lock is not in the expected state: {record}")
    return record


# -- setup ---------------------------------------------------------------------------------------

def setup(into: Path) -> dict[str, Any]:
    """Create the disposable project, the run tree, the worker rules and `state.json`."""
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
        "phases": {
            "design": {"status": "in-progress", "tasks": {}},
            "build": {"status": "pending", "tasks": {}},
        },
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # The real formats, discovered by running the tools rather than guessed: an invented
    # `proofbound-ledger-v1` was refused by `pb_ledger validate` before any money was spent.
    from _change_graph import GRAPH_FORMAT, canonical_graph_text
    (into / "ledger.json").write_text(
        json.dumps({"format": "proofbound-change-ledger-v1",
                    "artifact_identity": "proofbound-artifact-text-v1",
                    "artifacts": {}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # The declared change graph. Choosing this artifact set is a parent decision and is recorded
    # as one: the change consists of the specification, which depends on the accepted intent.
    #
    # It lives *inside the project* because `pb_graph` refuses a graph outside it — the graph is
    # ordinary project state, not orchestrator scratch. Learned by running the tool, unpaid.
    # `spec.md` alone, with no declared dependency. The design had it depend on `intent.md`, which
    # is not recordable: every ledger record requires an accepted, clean integrity gate and a
    # review (`pb_ledger.REQUIRED_REVIEW_KEYS`), and a parent-authored intent has no worker, no
    # gate and no reviewer. The ledger records artifacts produced under review; the intent is the
    # authority that review is *against*. Recorded as finding F1 in the run report.
    #
    # The dependency edge is not lost, only moved to where both ends are reviewed artifacts: after
    # the implementation is accepted the graph is extended to
    # `{"spec.md": [], "rateguard/__init__.py": ["spec.md"]}` and revalidated.
    (project / "change-graph.json").write_text(
        canonical_graph_text({"format": GRAPH_FORMAT,
                              "artifacts": {"spec.md": []}}), encoding="utf-8")

    # Task contracts live inside the run root, because `dsd_state bind-contract` refuses a path
    # outside it. Only the candidate-free ones are placed now: the three that bind a candidate
    # cannot exist until a candidate does, and writing them is a parent act at that point in the
    # workflow — for the implementation contract, a parent act by the *resuming* orchestrator.
    contracts = run / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    for name in ("RG-spec.md",):
        shutil.copyfile(CONTRACTS / name, contracts / name)
    for name in ("freezes", "consistency", "contracts", "evidence"):
        (into / name).mkdir(parents=True, exist_ok=True)

    return {"project": str(project), "run_root": str(run), "db": str(db),
            "ledger": str(into / "ledger.json"),
            "graph": str(project / "change-graph.json"),
            "task_contracts": str(contracts),
            "freezes": str(into / "freezes"), "consistency": str(into / "consistency"),
            "contracts": str(into / "contracts"),
            "head": sh(["git", "rev-parse", "HEAD"], cwd=project).stdout.strip(),
            "identities": identities()}


# -- correctness ---------------------------------------------------------------------------------

def project_suite(into: Path) -> dict[str, Any]:
    project = (into / "project").resolve()
    done = sh([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "tests"],
              cwd=project, env={**os.environ, "PYTHONPATH": str(project)})
    return {"returncode": done.returncode, "passed": done.returncode == 0,
            "tail": (done.stderr or done.stdout).strip()[-600:]}


def external(into: Path) -> dict[str, Any]:
    """The external suite, against the project as the implementer left it."""
    project = (into / "project").resolve()
    done = sh([sys.executable, "-m", "unittest", "discover",
               "-s", EXTERNAL, "-t", EXTERNAL],
              env={**os.environ, "PYTHONPATH": str(project)})
    return {"returncode": done.returncode, "passed": done.returncode == 0,
            "tail": (done.stderr or done.stdout).strip()[-1500:]}


# -- spend ---------------------------------------------------------------------------------------

def spend(into: Path) -> dict[str, Any]:
    """What this demonstration has spent, and whether that figure is the whole of it.

    Read from the session database the executor wrote, priced by the same machinery the
    experiments use. An attempt that ran without recording usage is unpriced, and unpriced means
    the remaining budget cannot be established — which blocks further paid launches.
    """
    import _pricing
    import _profile

    db = (into / "session" / "worker.db").resolve()
    if not db.is_file():
        return {"derived": 0.0, "complete": True, "sessions": 0,
                "claim": "no session database exists yet; nothing has been spent"}
    stage = _profile.profile(db, stage="implementer", model=MODEL, variant=VARIANT,
                             elapsed_seconds=0.0, verification_seconds=0.0)
    usage = stage.get("usage") or {}
    priced = _pricing.cost(usage, model=MODEL.split("/", 1)[-1],
                           when=datetime.now(tz=timezone.utc))
    amount = (priced or {}).get("amount")
    if not isinstance(amount, (int, float)):
        return {"derived": 0.0, "complete": False, "usage": usage,
                "claim": "the session exists but no usage could be priced; spend is unknown, "
                         "not zero, and no further paid launch is permitted"}
    return {"derived": round(float(amount), 6), "complete": True, "usage": usage,
            "cost": priced, "limit": AGGREGATE_LIMIT, "reserve": RESERVE,
            "headroom": round(AGGREGATE_LIMIT - RESERVE - float(amount), 6),
            "claim": "derived from the recorded session usage"}


def admit(into: Path) -> dict[str, Any]:
    """Whether another paid launch is permitted under the design's rule."""
    account = spend(into)
    if not account["complete"]:
        return {"admit": False, "why": "spend cannot be established", "spend": account}
    if account["derived"] + RESERVE > AGGREGATE_LIMIT:
        return {"admit": False, "why": f"derived {account['derived']} + reserve {RESERVE} "
                                       f"exceeds {AGGREGATE_LIMIT}", "spend": account}
    return {"admit": True, "spend": account}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["identities", "setup", "lock", "unlock", "verify-lock",
                                        "spend", "admit", "external", "project-suite"])
    ap.add_argument("--into", type=Path, default=None)
    args = ap.parse_args()

    if args.command in {"setup", "spend", "admit", "external", "project-suite"} and not args.into:
        raise SystemExit(f"{args.command} needs --into <workdir>")

    if args.command == "identities":
        out = identities()
    elif args.command == "setup":
        out = setup(args.into)
    elif args.command == "lock":
        out = lock()
    elif args.command == "unlock":
        out = unlock()
    elif args.command == "verify-lock":
        out = verify_lock(expect_locked=True)
    elif args.command == "spend":
        out = spend(args.into)
    elif args.command == "admit":
        out = admit(args.into)
    elif args.command == "external":
        out = external(args.into)
    else:
        out = project_suite(args.into)

    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
