#!/usr/bin/env python3
"""Run one engineering attempt on one arm of the modularity fixture, and account for its context.

MLR-C1 and MLR-C2 built the experimental object and proved its mechanics. This is the executor the
design (§19) said would be needed: the closed-world substrate drives a *reflector* over a scenario,
whereas here an arm selects a fixture variant and the work is an implementer trial against a hidden
correctness gate.

Everything that can be inherited is inherited. The launcher, the immutable reservation, worker-rules
preparation, prompt rendering and the evidence gate are the ones production uses, driven exactly as
`_trial.py` drives them, because an evaluation that bypassed orchestration would measure something
Proofbound does not ship. What is new is only what the modularity question needs: the project is an
arm's workspace with the module imported from outside it, correctness is the hidden external gate
rather than a grader, and the attempt's OpenCode database is read afterwards for the consumed-context
ledger.

**Validity before anything semantic.** A missing executable, absent credentials, a provider timeout
or a launch failure make the attempt *invalid*. They never become "the agent did not need the
implementation".
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import _mlr
import _mlr_context
import _profile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

VALID = "valid"
SETUP_FAILURE = "setup-failure"
HARNESS_FAILURE = "harness-failure"

TASK_ID = "MLR-external"
PHASE_ID = "build"
ROLE = "implementer"

# An implementer doing a real change reads, edits and runs tests; the reflector ceiling was set for
# a read-and-judge task. Thirty minutes is the same ceiling `_trial.py` uses and exists so one stuck
# worker cannot hold a series open, not to cut off work.
ATTEMPT_TIMEOUT_SECONDS = 1800

# The reflector evaluation launches with no permission flag because a reflector only reads. An
# implementer has to edit files and run tests, so it gets the flag production gives it. Stated as a
# constant rather than inherited from another script's default, because it is part of the frozen
# configuration: an arm that could not write would fail the task for a reason unrelated to context.
AUTO_FLAG = "--auto"

# The correctness oracle, versioned rather than replaced. MLR-C3 ran under v1, which rejected a
# product-correct restructuring because it asserted an internal function's signature; v2 asserts the
# product surface only. Historical evidence keeps the oracle it was actually judged by, so a later
# reader is never shown a correctness figure the run did not receive.
ORACLE_V1 = "external_test.py"
ORACLE_V2 = "external_test_v2.py"
ORACLE = ORACLE_V2


class RunError(RuntimeError):
    """The harness could not produce a judgeable attempt."""


def _sh(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, check=False, **kw)


def _prepare(built: dict[str, Any], root: Path, *, model: str,
             task: Path) -> tuple[Path, Path, Path]:
    """Turn a materialised arm into a project the launcher will accept.

    The run root lives under the workspace exactly as production requires, in *both* arms, so the
    only structural difference between them stays the vendored source.
    """
    workspace = Path(built["workspace"])
    _sh(["git", "init", "-q", str(workspace)])
    _sh(["git", "-C", str(workspace), "config", "user.email", "eval@proofbound.invalid"])
    _sh(["git", "-C", str(workspace), "config", "user.name", "Proofbound Eval"])
    _sh(["git", "-C", str(workspace), "add", "-A"])
    _sh(["git", "-C", str(workspace), "commit", "-qm", "fixture"])

    run = workspace / "DeepSeekAndDestroy" / "plans" / "mlr" / "runs" / "r1"
    contracts = run / "phases" / PHASE_ID / "tasks" / TASK_ID / "contracts"
    contracts.mkdir(parents=True)
    contract = contracts / "r0001.md"
    shutil.copyfile(task, contract)

    plan = workspace / "PLAN.md"
    if not plan.exists():
        plan.write_text("Service work plan.\n", encoding="utf-8")
    prep = _sh([sys.executable, str(SCRIPTS / "prepare_worker_rules.py"),
                "--project-root", str(workspace.resolve()), "--run-root", str(run.resolve()),
                "--plan", str(plan.resolve())])
    if prep.returncode != 0:
        raise RunError(f"could not prepare worker rules: {prep.stderr.strip()[:300]}")

    db = root / "worker.db"
    (run / "state.json").write_text(json.dumps({
        "project_worktree": str(workspace.resolve()),
        "execution_status": "active",
        "next_action": f"launch {ROLE}",
        "worker_rules": json.loads(prep.stdout),
        "worker_runtime": {"harness": "opencode-cli", "model": model,
                           "opencode": {"run_db": str(db.resolve())}},
        "phases": {PHASE_ID: {"status": "in-progress", "tasks": {TASK_ID: {
            "status": "prepared",
            "current_contract": {
                "revision": 1, "path": str(contract.resolve()),
                "sha256": hashlib.sha256(contract.read_bytes()).hexdigest()}}}}},
    }), encoding="utf-8")
    return run, db, contract


def grade(built: dict[str, Any], root: Path, *,
          oracle: str = ORACLE) -> dict[str, Any]:
    """Deterministic correctness, and whether the attempt stayed on its side of the boundary.

    Three independent facts, none of them a judgement: the hidden external gate, the service's own
    suite, and whether anything outside `app/` moved. The last is *evidence*, not a pass condition —
    an agent that edits the contract has not cheated, it has told us the boundary did not hold.

    The oracle is named in the result. A correctness number whose gate version is unrecorded cannot
    be compared with anything later, and MLR-C3 is the reason that matters here.
    """
    started = time.time()
    gate = _mlr.run_gate(built, _mlr.FIXTURE / "hidden" / oracle,
                         data_root=root / "grade-gate")
    regression = _mlr.run_tests(built, data_root=root / "grade-regression")
    verification_seconds = round(time.time() - started, 3)
    workspace = Path(built["workspace"])
    contract_now = _mlr.digest_file(workspace / "docs" / "storage-contract.md")
    vendored_now = (_mlr.digest_tree(workspace / _mlr.VENDORED / "objectstore")
                    if _mlr.arm_has_readable_copy(built) else None)
    return {
        "oracle": oracle,
        "gate_passed": gate.returncode == 0,
        "gate_output": (gate.stdout + gate.stderr)[-1500:],
        "regression_passed": regression.returncode == 0,
        "regression_output": (regression.stdout + regression.stderr)[-1000:],
        "correct": gate.returncode == 0 and regression.returncode == 0,
        "contract_unchanged": contract_now == built["contract_sha256"],
        "vendored_unchanged": vendored_now == built["vendored_digest"],
        "runtime_unchanged": _mlr.digest_tree(Path(built["runtime"])) == built["runtime_digest"],
        "verification_seconds": verification_seconds,
    }


def pin_interpreter(root: Path, env: dict[str, str]) -> dict[str, str]:
    """Make `python3` mean the interpreter that compiled the runtime.

    The runtime is bytecode compiled at materialisation, which is what makes the boundary real —
    and which also makes it importable by exactly one interpreter version. If the agent's `python3`
    resolved to a different one it would meet a magic-number error, and a fixture that cannot be
    executed measures nothing. So the attempt gets a bin directory of its own, first on `PATH`,
    naming the interpreter the fixture was built with.
    """
    binaries = Path(root) / "bin"
    binaries.mkdir(parents=True, exist_ok=True)
    for name in ("python3", "python"):
        link = binaries / name
        if not link.exists():
            link.symlink_to(sys.executable)
    env = dict(env)
    env["PATH"] = f"{binaries}:{env.get('PATH', '')}"
    return env


def run_attempt(arm: str, *, model: str, task: Path | None = None, keep: Path | None = None,
                timeout: int = ATTEMPT_TIMEOUT_SECONDS, oracle: str = ORACLE,
                fixture: Path = _mlr.FIXTURE) -> dict[str, Any]:
    """One arm, one fresh execution, ungraded context accounting plus a deterministic verdict."""
    started = time.time()
    task = Path(task) if task is not None else fixture / "tasks" / "external.md"
    holder = tempfile.mkdtemp(prefix="pb-mlr-")
    root = Path(holder)
    result: dict[str, Any] = {"arm": arm, "model": model, "harness": "opencode-cli", "role": ROLE,
                              "task_sha256": _mlr.digest_file(task),
                              "auto_flag": AUTO_FLAG,
                              "oracle": oracle,
                              "validity": HARNESS_FAILURE, "reason": None}
    try:
        built = _mlr.materialise(arm, root / "arm", fixture=fixture)
        result.update({"runtime_digest": built["runtime_digest"],
                       "source_digest": built["source_digest"],
                       "contract_sha256": built["contract_sha256"],
                       "workspace_digest": built["workspace_digest"]})
        try:
            run, db, _ = _prepare(built, root, model=model, task=task)
        except RunError as exc:
            result["reason"] = str(exc)
            return result

        env = pin_interpreter(root, _mlr.environment(built, data_root=root / "data"))
        result["interpreter"] = sys.version.split()[0]
        try:
            launch = _sh([sys.executable, str(SCRIPTS / "dsd_attempt.py"), "launch",
                          "--run-root", str(run.resolve()), "--phase-id", PHASE_ID,
                          "--task-id", TASK_ID, "--role", ROLE,
                          f"--auto-flag={AUTO_FLAG}"],
                         timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            result["reason"] = f"worker did not finish within {timeout}s"
            return result
        if launch.returncode != 0:
            blob = (launch.stdout + launch.stderr).lower()
            result["validity"] = SETUP_FAILURE if (
                "not found" in blob or "executable" in blob or "auth" in blob
                or "credential" in blob or "rate" in blob) else HARNESS_FAILURE
            result["reason"] = (launch.stderr or launch.stdout).strip()[:400]
            return result
        event_dir = Path(json.loads(launch.stdout)["event_dir"])

        try:
            _sh([sys.executable, str(SCRIPTS / "dsd_attempt.py"), "gate",
                 "--run-root", str(run.resolve()), "--phase-id", PHASE_ID,
                 "--task-id", TASK_ID], timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            result["reason"] = f"gate did not finish within {timeout}s"
            return result
        gate_path = event_dir / "evidence-gate.json"
        evidence = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.is_file() else None
        if evidence is None:
            result["reason"] = "gate produced no evidence artifact"
            return result
        if evidence.get("report_state") == "launcher-skeleton" or evidence.get(
                "needs_report_recovery"):
            result["validity"] = SETUP_FAILURE
            result["reason"] = ("worker produced no usable report "
                                f"(report_state={evidence.get('report_state')!r})")
            return result

        result.update({
            "validity": VALID,
            "event_dir": str(event_dir),
            "evidence_gate": evidence,
            "prompt_bytes": len((event_dir / "launch-prompt.txt").read_bytes())
                            if (event_dir / "launch-prompt.txt").is_file() else None,
            "context": _mlr_context.consumed(db, built),
        })
        outcome = grade(built, root, oracle=oracle)
        stage = _profile.profile(
            db, stage=ROLE, model=model,
            elapsed_seconds=round(time.time() - started, 3),
            verification_seconds=outcome["verification_seconds"])
        result["outcome"] = outcome
        result["profile"] = _profile.pipeline([stage], outcome={
            "correct": outcome["correct"], "gate_passed": outcome["gate_passed"],
            "regression_passed": outcome["regression_passed"], "oracle": outcome["oracle"]})
        return result
    except Exception as exc:                              # noqa: BLE001 - reported, never raised
        result["reason"] = f"{type(exc).__name__}: {exc}"[:400]
        return result
    finally:
        result["elapsed_seconds"] = round(time.time() - started, 3)
        if keep is not None and root.is_dir():
            target = Path(keep) / f"{arm}-{int(started * 1000)}"
            shutil.copytree(root, target, dirs_exist_ok=True)
            result["evidence"] = str(target)
        shutil.rmtree(root, ignore_errors=True)
