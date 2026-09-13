#!/usr/bin/env python3
"""The modularity experiment's worker, run inside a constructed evidence surface.

R4-A built a per-slot execution view and proved it with local commands. This is the layer that puts
the *real* thing inside it: the prepared arm, the compiled dependency, the inherited DSD launcher,
the executor, its session database, and the ordinary tool subprocess tree the model drives.

**One entry point.** The boundary is applied once, around the launcher, so everything below it —
`dsd_attempt`, `run_worker`, the executor and every tool it spawns — inherits the same evidence
surface. Wrapping individual shell commands would leave the executor itself on the outside, which is
where the question *what can the evaluated process see?* stops having a single answer.

**Construct, never mount.** The arm is materialised on the control plane and its declared parts are
copied in. The repository is not exposed; neither is the fixture generator, the hidden gate, the
reference solution, prior samples or any result. The harness the launcher needs is staged as a
declared input like everything else, and is checked to carry none of those.

**The boundary is not the measurement.** It controls what evidence can be reached. Attribution
records what actually entered context, and the hidden gate decides whether the work was right. Those
three stay separate, and nothing here touches the second or the third.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import _hermetic
import _mlr
import _mlr_context
import _mlr_run
import _pricing
import _profile
import _semantic_view

ROOT = Path(__file__).resolve().parents[1]
HARNESS_SOURCE = ROOT / "scripts"

#: Where the launcher and its helpers live inside the view. They are orchestration, not evidence,
#: and are staged as a declared input after being checked for controlled material.
HARNESS_AREA = "harness"
#: Where the interpreter the fixture was compiled by is made to mean `python3`.
BIN_AREA = "bin"
#: The one part of the view that is source by design, in one arm only.
FULL_EXPOSURE = "workspace/third_party"


def sensitive(*, fixture: Path = _mlr.FIXTURE) -> list[_hermetic.Sensitive]:
    """What must not appear in the view undeclared. The fixture's own identities, not the checker's."""
    return list(_mlr.hermeticity(fixture=fixture)["sensitive"])


def interpreter_exposure(executable: str | Path | None = None) -> tuple[str, ...]:
    """The installation the pinned interpreter lives in.

    An interpreter reached through symlinks lives in two places at once — the linked name and the
    real one — so the common ancestor of both is what the policy has to expose. Nothing about which
    interpreter is right belongs in the substrate; this is the experiment naming its own.
    """
    executable = Path(executable or sys.executable)
    candidates = [executable, executable.resolve(),
                  Path(sys.base_prefix), Path(sys.base_prefix).resolve()]
    return (os.path.commonpath([str(c) for c in candidates]),)


def policy(*, executor: Path | None = None, network: bool = True,
           declared: Iterable[str] = (), executable: str | Path | None = None
           ) -> _semantic_view.Policy:
    """The boundary this experiment runs under.

    Network is open because the executor has to reach its provider and no evidence this experiment
    controls is reachable over it. That is a statement about this treatment, not a security posture:
    opening the network buys the view no additional filesystem.
    """
    tools = [_semantic_view.Tool("opencode", executor)] if executor else []
    exposure = interpreter_exposure(executable)
    # No file-change notification. It was added while a hang was being chased, and the hang has
    # since been explained by an outbound firewall on the host interrupting the executor's provider
    # connection. The Field Test settles it against the evidence rather than against the intuition:
    # two real trajectories — 27 calls over 49 tools, and 26 over 53 — started and ran to completion
    # without it. Nothing required it, so it is not carried.
    return _semantic_view.Policy(
        tools=tools, network=network, notifications=False, declared=tuple(declared),
        extra_reads=exposure,
        system_execs=(*_semantic_view.SYSTEM_EXECS, *exposure))


def stage(view: _semantic_view.View, arm: str, *, fixture: Path = _mlr.FIXTURE,
          task: Path | None = None, model: str, home_files: dict[str, Path] | None = None,
          executable: str | Path | None = None) -> dict[str, Any]:
    """Build one arm on the control plane and copy its declared parts into the view.

    Returns the `built` mapping the rest of the machinery already expects, with every path pointing
    inside the view — so `grade`, the attribution ledger and the profile keep working on exactly the
    shapes they were written for.
    """
    task = Path(task) if task is not None else fixture / "tasks" / "external.md"
    holder = Path(tempfile.mkdtemp(prefix="pb-mlr-stage-"))
    try:
        prepared = _mlr.materialise(arm, holder / "arm", fixture=fixture)
        shutil.rmtree(view.workspace)
        shutil.copytree(Path(prepared["workspace"]), view.workspace)
        shutil.rmtree(view.runtime)
        shutil.copytree(Path(prepared["runtime"]), view.runtime)
    finally:
        shutil.rmtree(holder, ignore_errors=True)

    built = dict(prepared)
    built.update({"workspace": view.workspace, "runtime": view.runtime})

    # The launcher and its helpers. Orchestration rather than evidence — asserted rather than
    # assumed, because staging the repository wholesale is exactly what this design refuses.
    harness = view.root / HARNESS_AREA
    shutil.copytree(HARNESS_SOURCE, harness,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    # `python3` must mean the interpreter that compiled the bytecode, inside the view as it did
    # outside it. A symlink is enough: the target is a system path the policy already allows.
    binaries = view.root / BIN_AREA
    binaries.mkdir(exist_ok=True)
    for name in ("python3", "python"):
        link = binaries / name
        if not link.exists():
            link.symlink_to(Path(executable or sys.executable))

    for name, source in (home_files or {}).items():
        target = view.home / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(source), target)

    run, db, contract = _mlr_run._prepare(built, view.session.parent, model=model, task=task)
    # `_prepare` puts the session database beside the run root; the view keeps it in its own area so
    # extraction has one place to look and destruction has one place to clear.
    db = view.session / "worker.db"
    state = run / "state.json"
    document = json.loads(state.read_text(encoding="utf-8"))
    document["worker_runtime"]["opencode"]["run_db"] = str(db)
    state.write_text(json.dumps(document), encoding="utf-8")
    return {"built": built, "run": run, "db": db, "contract": contract, "harness": harness,
            "binaries": binaries, "task": task}


def environment(view: _semantic_view.View, staged: dict[str, Any]) -> dict[str, str]:
    """Everything the worker needs, and nothing it merely inherited.

    Five names beyond the substrate's three. Each is a path inside the view or a value the experiment
    declares; none points at the control plane, and none arrived by being present in the evaluator's
    shell.
    """
    return {
        "PATH": os.pathsep.join([str(staged["binaries"]), str(view.tools_root),
                                 *_semantic_view.BASE_PATH]),
        "PYTHONPATH": str(view.runtime),
        "OBJECTSTORE_ROOT": str(view.data),
        "OPENCODE_DB": str(staged["db"]),
        "DSD_OC_RUN_DB": str(staged["db"]),
    }


def preflight(view: _semantic_view.View, arm: str, *,
              fixture: Path = _mlr.FIXTURE) -> dict[str, Any]:
    """Whether this slot's evidence surface is the one the treatment intends.

    `full` declares its source exposure and the check permits exactly that; a second copy anywhere
    else in the view is a finding in either arm. The control plane's own repository is outside the
    surface and is not consulted — the question changed from *is this host clean* to *does this view
    expose anything undeclared*, which is the whole point of constructing one.
    """
    declared = [str(view.root / FULL_EXPOSURE)] if arm == _mlr.FULL else []
    report = _hermetic.scan(view.roots(), sensitive(fixture=fixture), declared=declared)
    report["arm"] = arm
    report["declared"] = declared
    # The rule this slot was judged under, recorded beside the judgement. `_hermetic.scan` reports
    # what it found; which rule it was applying is the caller's to say.
    report["hermeticity_identity"] = _mlr.preflight_identity(fixture=fixture)
    return report


class PreflightRefused(RuntimeError):
    """The slot's evidence surface was not the one the treatment intends, so nothing was launched."""


def launch(view: _semantic_view.View, staged: dict[str, Any], *, variant: str | None,
           cleared: dict[str, Any], timeout: int = _mlr_run.ATTEMPT_TIMEOUT_SECONDS
           ) -> subprocess.CompletedProcess:
    """Start the inherited launcher inside the view.

    This is the single place the boundary is entered. Everything the launcher starts — the worker
    script, the executor, every tool subprocess — is a descendant of this call and inherits it.

    The preflight report is an argument rather than an assumption, so a caller that has not run one
    cannot call this at all and a caller that ran one and ignored it is refused. The ordering is a
    control-flow invariant and not a flag stored on the view: nothing durable should be able to say
    "this slot was clean" after the moment that was true.
    """
    if cleared.get("status") != _hermetic.CLEAN:
        raise PreflightRefused(
            f"preflight returned {cleared.get('status')!r} with "
            f"{len(cleared.get('findings') or [])} finding(s); no semantic slot was consumed")
    return view.run(
        [str(staged["binaries"] / "python3"), str(staged["harness"] / "dsd_attempt.py"), "launch",
         "--run-root", str(staged["run"]), "--phase-id", _mlr_run.PHASE_ID,
         "--task-id", _mlr_run.TASK_ID, "--role", _mlr_run.ROLE,
         f"--auto-flag={_mlr_run.AUTO_FLAG}"]
        + (["--variant", variant] if variant else []),
        env=environment(view, staged), timeout=timeout)


def gate(view: _semantic_view.View, staged: dict[str, Any], *,
         timeout: int = _mlr_run.ATTEMPT_TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    """Classify the worker's terminal event, inside the view like everything else."""
    return view.run(
        [str(staged["binaries"] / "python3"), str(staged["harness"] / "dsd_attempt.py"), "gate",
         "--run-root", str(staged["run"]), "--phase-id", _mlr_run.PHASE_ID,
         "--task-id", _mlr_run.TASK_ID],
        env=environment(view, staged), timeout=timeout)


def extract(view: _semantic_view.View, destination: Path, staged: dict[str, Any]) -> dict[str, str]:
    """Bring back the slot's products, from the outside, after it has finished.

    The workspace as the oracle will judge it, the session database the ledger and the profile will
    read, and this run's own logs. Nothing historical, because nothing historical was ever there.
    """
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    out: dict[str, str] = {}
    out["workspace"] = str(view.collect("workspace", destination / "workspace"))
    if staged["db"].is_file():
        # The executor leaves the database in write-ahead mode, where the file on its own is not a
        # database: opening the copy read-only fails with `unable to open database file` because the
        # log it needs was left behind. Checkpointing first makes the copy self-contained, which is
        # what a durable piece of evidence has to be.
        _checkpoint(staged["db"])
        out["session"] = str(view.collect(staged["db"].relative_to(view.root),
                                          destination / "worker.db"))
    return out


def _checkpoint(database: Path) -> None:
    """Fold a write-ahead log back into its database, so one file is the whole of it."""
    try:
        connection = sqlite3.connect(str(database))
    except sqlite3.Error:                                   # pragma: no cover - unopenable database
        return
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.commit()
    except sqlite3.Error:                                   # pragma: no cover - nothing to fold
        pass
    finally:
        connection.close()


def run_bounded_attempt(arm: str, *, model: str, variant: str | None, executor: Path,
                        credentials: dict[str, Path] | None = None, keep: Path | None = None,
                        fixture: Path = _mlr.FIXTURE, task: Path | None = None,
                        timeout: int = _mlr_run.ATTEMPT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """One arm, one execution, inside a constructed evidence surface.

    The same shape `run_attempt` has always produced — validity, outcome, context ledger, profile,
    cost — assembled from the same machinery. What changed is where the worker ran and what it could
    see while running. Grading happens after the view is gone, on the extracted workspace, so the
    hidden gate is never a file the subject could have found.
    """
    started = time.time()
    result: dict[str, Any] = {
        "arm": arm, "model": model, "harness": "opencode-cli", "role": _mlr_run.ROLE,
        "auto_flag": _mlr_run.AUTO_FLAG, "variant": variant, "oracle": _mlr_run.ORACLE,
        "validity": _mlr_run.HARNESS_FAILURE, "reason": None,
        "executor": executor_identity(executor),
        "interpreter": sys.version.split()[0],
    }
    extraction = Path(tempfile.mkdtemp(prefix="pb-mlr-out-"))
    try:
        view_policy = policy(executor=executor)
        result["boundary_identity"] = view_policy.identity()
        with _semantic_view.semantic_view(view_policy) as view:
            staged = stage(view, arm, fixture=fixture, task=task, model=model,
                           home_files=credentials or {})
            built = staged["built"]
            result.update({
                "task_sha256": _mlr.digest_file(staged["task"]),
                "runtime_digest": built["runtime_digest"],
                "runtime_structure": built["runtime_structure"],
                "source_digest": built["source_digest"],
                "contract_sha256": built["contract_sha256"],
                "workspace_digest": built["workspace_digest"],
            })

            cleared = preflight(view, arm, fixture=fixture)
            result["hermeticity"] = {k: cleared[k] for k in
                                     ("status", "hermeticity_identity", "scanned_roots",
                                      "declared", "claim")}
            result["hermeticity"]["declared_exposures"] = len(cleared["declared_exposures"])
            result["hermeticity"]["findings"] = cleared["findings"][:50]
            if cleared["status"] != _hermetic.CLEAN:
                result["validity"] = _mlr_run.SETUP_FAILURE
                result["reason"] = "hermeticity preflight refused the environment"
                return result

            launched = launch(view, staged, variant=variant, cleared=cleared, timeout=timeout)
            result["launch_returncode"] = launched.returncode
            if launched.returncode != 0:
                blob = (launched.stdout + launched.stderr).lower()
                result["validity"] = _mlr_run.SETUP_FAILURE if (
                    "not found" in blob or "auth" in blob or "credential" in blob
                    or "rate" in blob) else _mlr_run.HARNESS_FAILURE
                result["reason"] = (launched.stderr or launched.stdout).strip()[:400]
                return result
            try:
                event_dir = Path(json.loads(launched.stdout)["event_dir"])
            except (ValueError, KeyError) as exc:
                result["reason"] = f"launcher produced no event directory: {exc}"
                return result

            gate(view, staged, timeout=timeout)
            gate_path = event_dir / "evidence-gate.json"
            evidence = (json.loads(gate_path.read_text(encoding="utf-8"))
                        if gate_path.is_file() else None)
            if evidence is None:
                result["reason"] = "gate produced no evidence artifact"
                return result
            if evidence.get("report_state") == "launcher-skeleton" or evidence.get(
                    "needs_report_recovery"):
                result["validity"] = _mlr_run.SETUP_FAILURE
                result["reason"] = "worker produced no usable report"
                return result

            result["event_dir"] = str(event_dir.relative_to(view.root))
            result["evidence_gate"] = evidence
            prompt = event_dir / "launch-prompt.txt"
            result["prompt_bytes"] = len(prompt.read_bytes()) if prompt.is_file() else None
            collected = extract(view, extraction, staged)
            result["extraction"] = {k: Path(v).name for k, v in collected.items()}
            session = Path(collected["session"]) if "session" in collected else None
            workspace = Path(collected["workspace"])
            view_root = view.root
            # Attribution reads the session while the view's own paths are still meaningful, so a
            # path class is resolved against the arm it was produced under rather than a directory
            # that no longer exists.
            if session and session.is_file():
                # Usage first, so an attempt that fails afterwards still accounts for what it spent.
                # A provider call that happened is a provider call that was paid for.
                usage = _profile.profile(
                    session, stage=_mlr_run.ROLE, model=model, variant=variant,
                    elapsed_seconds=round(time.time() - started, 3), verification_seconds=0.0)
                result["cost"] = _pricing.cost(
                    usage["usage"], model=model.split("/", 1)[-1],
                    when=datetime.fromtimestamp(started, tz=timezone.utc))
            result["context"] = (_mlr_context.consumed(session, built) if session else None)
        result["view_destroyed"] = not view_root.exists()

        graded_root = Path(tempfile.mkdtemp(prefix="pb-mlr-grade-"))
        try:
            regraded = _mlr.materialise(arm, graded_root / "arm", fixture=fixture)
            shutil.rmtree(regraded["workspace"])
            shutil.copytree(workspace, regraded["workspace"])
            result["outcome"] = _mlr_run.grade(regraded, graded_root)
        finally:
            shutil.rmtree(graded_root, ignore_errors=True)

        if session and session.is_file():
            stage_profile = _profile.profile(
                session, stage=_mlr_run.ROLE, model=model, variant=variant,
                elapsed_seconds=round(time.time() - started, 3),
                verification_seconds=result["outcome"]["verification_seconds"])
            result["profile"] = _profile.pipeline([stage_profile], outcome={
                "correct": result["outcome"]["correct"],
                "gate_passed": result["outcome"]["gate_passed"],
                "regression_passed": result["outcome"]["regression_passed"],
                "oracle": result["outcome"]["oracle"]})
            result["cost"] = _pricing.cost(
                stage_profile["usage"], model=model.split("/", 1)[-1],
                when=datetime.fromtimestamp(started, tz=timezone.utc))
        result["validity"] = _mlr_run.VALID
        return result
    except Exception as exc:                              # noqa: BLE001 - reported, never raised
        result["reason"] = f"{type(exc).__name__}: {exc}"[:400]
        return result
    finally:
        result["elapsed_seconds"] = round(time.time() - started, 3)
        if keep is not None and extraction.is_dir():
            target = Path(keep) / f"{arm}-{int(started * 1000)}"
            shutil.copytree(extraction, target, dirs_exist_ok=True)
            result["evidence"] = str(target)
        shutil.rmtree(extraction, ignore_errors=True)


def harness_is_clean(*, fixture: Path = _mlr.FIXTURE) -> dict[str, Any]:
    """Whether the staged launcher carries any of the evidence the treatment controls."""
    return _hermetic.scan([HARNESS_SOURCE], sensitive(fixture=fixture))


def executor_identity(executor: Path) -> dict[str, str]:
    """What the staged executor is, without saying anything about how it authenticates."""
    executor = Path(executor)
    return {"name": executor.name,
            "sha256": hashlib.sha256(executor.read_bytes()).hexdigest()}
