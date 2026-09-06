#!/usr/bin/env python3
"""One trial: one scenario, one configuration, one pristine execution of the real pipeline.

The thing under evaluation is *Proofbound plus a configured harness and model*, not a raw
model completion. So a trial drives the same orchestration production uses — the launcher,
the immutable reservation, prompt rendering, the integrity gate, the scope check. There is
deliberately no eval-only model client: an evaluation that bypassed orchestration would
measure something Proofbound does not ship.

The provider seam is inherited exactly as it is. `run_worker.py` launches a worker as
`subprocess.Popen(["opencode", "run", "--model", …])` resolved through `PATH`. The
deterministic slices substitute a fake binary there; a real trial simply has the real binary
present. Nothing here reimplements that seam.

**Validity is decided before anything semantic.** A missing executable, absent credentials, a
provider timeout or a launch failure produce an *invalid* trial, never "the reflector missed
the contradiction". Conflating the two would let an outage masquerade as a result.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

# Validity classes. The distinction that matters is whether the agent failed or the
# evaluation machinery failed to produce a judgeable trial.
VALID = "valid"
SETUP_FAILURE = "setup-failure"          # executable/credentials/provider unavailable
HARNESS_FAILURE = "harness-failure"      # our own machinery malfunctioned

TASK_ID = "EVAL-artifact"
PHASE_ID = "spec"


class TrialError(RuntimeError):
    """The harness itself could not run a trial."""


def provider_available(executable: str = "opencode") -> tuple[bool, str]:
    """Whether a real worker could be launched at all, without touching secret values."""
    found = shutil.which(executable)
    if not found:
        return False, f"worker executable {executable!r} is not on PATH"
    return True, found


def _sh(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, check=False, **kw)


def _build_project(scenario: dict[str, Any], root: Path) -> tuple[Path, Path]:
    """A pristine project and run tree for exactly one trial.

    Copied fresh every time: a previous trial's accepted artifacts would change what the next
    trial's reflector sees, which is the whole reason trials must not share state.
    """
    project = root / "project"
    shutil.copytree(scenario["fixture"], project)
    _sh(["git", "init", "-q", str(project)])
    _sh(["git", "-C", str(project), "config", "user.email", "eval@proofbound.invalid"])
    _sh(["git", "-C", str(project), "config", "user.name", "Proofbound Eval"])
    _sh(["git", "-C", str(project), "add", "-A"])
    _sh(["git", "-C", str(project), "commit", "-qm", "scenario fixture"])

    run = project / "DeepSeekAndDestroy" / "plans" / "eval" / "runs" / "r1"
    contracts = run / "phases" / PHASE_ID / "tasks" / TASK_ID / "contracts"
    contracts.mkdir(parents=True)
    contract = contracts / "r0001.md"
    shutil.copyfile(scenario["contract"], contract)

    plan = project / "PLAN.md"
    if not plan.exists():
        plan.write_text("Evaluation scenario plan.\n", encoding="utf-8")
    prep = _sh([sys.executable, str(SCRIPTS / "prepare_worker_rules.py"),
                "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                "--plan", str(plan.resolve())])
    if prep.returncode != 0:
        raise TrialError(f"could not prepare worker rules: {prep.stderr.strip()[:300]}")

    (run / "state.json").write_text(json.dumps({
        "project_worktree": str(project.resolve()),
        "execution_status": "active",
        "next_action": "launch spec-reflector",
        "worker_rules": json.loads(prep.stdout),
        "worker_runtime": {"harness": "opencode-cli", "model": os.environ.get(
            "PROOFBOUND_EVAL_MODEL", "opencode-go/deepseek-v4-flash"),
            "opencode": {"run_db": str((root / "worker.db").resolve())}},
        "phases": {PHASE_ID: {"status": "in-progress", "tasks": {TASK_ID: {
            "status": "prepared",
            "current_contract": {
                "revision": 1, "path": str(contract.resolve()),
                "sha256": hashlib.sha256(contract.read_bytes()).hexdigest()}}}}},
    }), encoding="utf-8")
    return project, run


def _supplied_bytes(run: Path, event_dir: Path) -> int | None:
    """Bytes of the material the prompt directs the worker to read.

    A provider-neutral context proxy that is *not* a token count and must never be described
    as one. It covers the worker-rules snapshot, the role protocol and the task contract —
    the files the launcher names — and not whatever the worker chooses to open afterwards.
    """
    try:
        reservation = json.loads((event_dir / "launch-reservation.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    total = 0
    for key in ("task_contract", "worker_rules"):
        raw = reservation.get(key)
        if isinstance(raw, str):
            path = Path(raw) if Path(raw).is_absolute() else run / raw
            if path.is_file():
                total += len(path.read_bytes())
    rules_dir = run / "worker-rules"
    if rules_dir.is_dir():
        for path in sorted(rules_dir.rglob("*")):
            if path.is_file() and path.suffix == ".md":
                total += len(path.read_bytes())
    return total or None


def run_trial(scenario: dict[str, Any], *, model: str, keep: Path | None = None,
              timeout: int = 900) -> dict[str, Any]:
    """Execute one trial and return its raw evidence, ungraded.

    Grading is a separate concern; this function only reports what happened.
    """
    started = time.time()
    holder = tempfile.mkdtemp(prefix="pb-eval-")
    root = Path(holder)
    result: dict[str, Any] = {"scenario": scenario["id"],
                              "scenario_identity": scenario["identity"],
                              "model": model, "harness": "opencode-cli",
                              "validity": HARNESS_FAILURE, "reason": None}
    try:
        try:
            project, run = _build_project(scenario, root)
        except TrialError as exc:
            result["reason"] = str(exc)
            return result

        env = dict(os.environ)
        env["PROOFBOUND_EVAL_MODEL"] = model
        launch = _sh([sys.executable, str(SCRIPTS / "dsd_attempt.py"), "launch",
                      "--run-root", str(run.resolve()), "--phase-id", PHASE_ID,
                      "--task-id", TASK_ID, "--role", "spec-reflector", "--auto-flag="],
                     env=env, timeout=timeout)
        if launch.returncode != 0:
            # A launch failure is the harness or the provider, never the reflector's judgement.
            blob = (launch.stdout + launch.stderr).lower()
            result["validity"] = SETUP_FAILURE if (
                "not found" in blob or "executable" in blob or "auth" in blob
                or "credential" in blob or "rate" in blob) else HARNESS_FAILURE
            result["reason"] = (launch.stderr or launch.stdout).strip()[:400]
            return result
        event_dir = Path(json.loads(launch.stdout)["event_dir"])

        # Run the real gate, then read the artifact it writes. The CLI returns a deliberately
        # reduced surface for parent context economy; `evidence-gate.json` is authoritative.
        gate_cli = _sh([sys.executable, str(SCRIPTS / "dsd_attempt.py"), "gate",
                        "--run-root", str(run.resolve()), "--phase-id", PHASE_ID,
                        "--task-id", TASK_ID], timeout=timeout)
        gate_path = event_dir / "evidence-gate.json"
        gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.is_file() else None
        result.update({
            "validity": VALID,
            "run_root": str(run.resolve()),
            "event_dir": str(event_dir),
            "gate": gate,
            "gate_exit": gate_cli.returncode,
            "report": (event_dir / "report.md").read_text(encoding="utf-8")
                      if (event_dir / "report.md").is_file() else "",
            # The launch prompt is a pointer list: Proofbound hands the worker paths, not
            # content. So the envelope is small and says little about context cost, and the
            # material the worker is directed to read is measured separately.
            "prompt_bytes": len((event_dir / "launch-prompt.txt").read_bytes())
                            if (event_dir / "launch-prompt.txt").is_file() else None,
            "context_bytes": _supplied_bytes(run, event_dir),
            "state": json.loads((run / "state.json").read_text(encoding="utf-8")),
        })
        terminal = event_dir / "terminal.json"
        if terminal.is_file():
            result["terminal"] = json.loads(terminal.read_text(encoding="utf-8"))
        # Whether the worker actually produced something judgeable is Proofbound's own
        # classification, not a heuristic here: the launcher pre-creates a report skeleton,
        # and the gate reports `launcher-skeleton` plus `needs_report_recovery` when the
        # worker never wrote into it. A trial with nothing to judge is a setup failure.
        if gate is None:
            result["validity"] = HARNESS_FAILURE
            result["reason"] = "gate produced no evidence artifact"
        elif gate.get("report_state") == "launcher-skeleton" or gate.get("needs_report_recovery"):
            result["validity"] = SETUP_FAILURE
            result["reason"] = ("worker produced no usable report "
                                f"(report_state={gate.get('report_state')!r})")
        return result
    finally:
        result["elapsed_seconds"] = round(time.time() - started, 3)
        if keep is not None and root.is_dir():
            # Raw evidence is kept locally and never committed: it is large, provider
            # specific, and is execution evidence rather than a measurement.
            target = Path(keep) / f"{scenario['id']}-{int(started * 1000)}"
            shutil.copytree(root, target, dirs_exist_ok=True)
            result["evidence"] = str(target)
        shutil.rmtree(root, ignore_errors=True)
