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
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

import _hermetic
import _mlr
import _mlr_run
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
    return _semantic_view.Policy(
        tools=tools, network=network, declared=tuple(declared),
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
        out["session"] = str(view.collect(staged["db"].relative_to(view.root),
                                          destination / "worker.db"))
    return out


def harness_is_clean(*, fixture: Path = _mlr.FIXTURE) -> dict[str, Any]:
    """Whether the staged launcher carries any of the evidence the treatment controls."""
    return _hermetic.scan([HARNESS_SOURCE], sensitive(fixture=fixture))


def executor_identity(executor: Path) -> dict[str, str]:
    """What the staged executor is, without saying anything about how it authenticates."""
    executor = Path(executor)
    return {"name": executor.name,
            "sha256": hashlib.sha256(executor.read_bytes()).hexdigest()}
