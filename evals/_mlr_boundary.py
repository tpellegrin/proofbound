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
import signal
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
#: How far behind the controller's deadline the in-view limits are set. They cannot take effect
#: inside the sandbox, so they must not conclude an attempt before the controller does.
INNER_DEADLINE_MARGIN_SECONDS = 120.0
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
    task = Path(task) if task is not None else _mlr.fixture_for(fixture).task
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
    # **The controller's own wait is the deadline.** Not by preference but by necessity: the view's
    # sandbox profile denies `signal`, so a process inside it cannot stop even its own direct child
    # — measured as `EPERM` for both `kill` and `killpg`. The monitor that owns the worker therefore
    # cannot enforce a limit from where it sits, and this call, which is the view's parent and is
    # not sandboxed, is the only place that can. `run_bounded_attempt` catches the expiry and stops
    # the attempt's own pids by hand.
    #
    # The in-view limits are still passed, deliberately set *behind* this one. They matter for
    # callers that do not run inside a sandbox, and sitting behind the controller keeps them from
    # writing a `terminal.json` that says "timeout" while the worker they could not signal is still
    # running — a disposition that would read as authoritative and would not be.
    inner = timeout + _mlr_run.TERMINATION_GRACE_SECONDS + INNER_DEADLINE_MARGIN_SECONDS
    return view.run(
        [str(staged["binaries"] / "python3"), str(staged["harness"] / "dsd_attempt.py"), "launch",
         "--run-root", str(staged["run"]), "--phase-id", _mlr_run.PHASE_ID,
         "--task-id", _mlr_run.TASK_ID, "--role", _mlr_run.ROLE,
         f"--auto-flag={_mlr_run.AUTO_FLAG}",
         "--timeout", str(inner),
         "--termination-grace", str(_mlr_run.TERMINATION_GRACE_SECONDS)]
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
        "auto_flag": _mlr_run.AUTO_FLAG, "variant": variant,
        "validity": _mlr_run.HARNESS_FAILURE, "reason": None,
        "interpreter": sys.version.split()[0],
        # Whether this attempt can still be retried without buying a second semantic trajectory.
        # Set the instant the launcher is entered and never cleared: everything below that call is
        # the executor and its provider, so after it nothing downstream — an extraction defect, a
        # grading crash, a killed process — may be read as "no model call happened". A retry
        # decision that assumed otherwise would re-roll a trajectory the design says is immutable.
        "trajectory_began": False,
    }
    # Nothing above the `try`. Resolving the fixture, hashing the executor and making the extraction
    # directory can all fail — an unknown fixture root, a binary removed between the eligibility
    # check and the hash, no temp space — and each of them provably happens before the launcher is
    # entered, which is §11 A's case and retryable. Raised from here they escaped the series loop
    # instead, and the loop's pre-attempt checkpoint would then be the only surviving row: a slot
    # frozen in §11 C, unresumable, for a failure that never reached the executor. Found in review.
    extraction: Path | None = None
    grace = _mlr_run.TERMINATION_GRACE_SECONDS
    # Held outside the `with` so an interrupt can still find the view and the run root it has to
    # clean up after. They are assigned as soon as each exists and are never used for anything else.
    view_for_teardown: Any = None
    staged_for_teardown: Any = None
    try:
        spec = _mlr.fixture_for(fixture)
        result.update({"oracle": spec.oracle, "fixture": str(spec.root),
                       "package": spec.package, "executor": executor_identity(executor)})
        extraction = Path(tempfile.mkdtemp(prefix="pb-mlr-out-"))
        view_policy = policy(executor=executor)
        result["boundary_identity"] = view_policy.identity()
        with _semantic_view.semantic_view(view_policy) as view:
            view_for_teardown = view
            staged = stage(view, arm, fixture=fixture, task=task, model=model,
                           home_files=credentials or {})
            staged_for_teardown = staged["run"]
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

            result["trajectory_began"] = True
            result["attempt_deadline_seconds"] = timeout
            # **One deadline for the attempt, not one per leg.** `launch` and `gate` are both
            # bounded calls, and giving each the full `timeout` made the real exposure about twice
            # the number the record reported. They share a single monotonic deadline now, so
            # `attempt_deadline_seconds` means what it says. Found in review.
            attempt_deadline = time.monotonic() + timeout
            try:
                launched = launch(view, staged, variant=variant, cleared=cleared, timeout=timeout)
            except subprocess.TimeoutExpired:
                # The deadline. Killing `sandbox-exec` — all that `subprocess.run` does on expiry —
                # leaves the detached monitor and the worker running in their own sessions, still
                # calling a provider, while the `finally` below destroys the view around them. The
                # work this attempt owns is stopped here instead, by pid, from outside the sandbox,
                # and the result says whether it actually stopped rather than that a signal was
                # sent. Provider-side work already dispatched is not ours to cancel and no claim is
                # made about it.
                result["validity"] = _mlr_run.HARNESS_FAILURE
                result["timed_out"] = True
                result["terminal_status"] = "controller-timeout"
                result["termination"] = _stop_attempt(view.root, staged["run"], grace=grace)
                result["reason"] = (f"the controller's {timeout}s deadline expired; "
                                    + _stop_summary(result["termination"]))
                result["extraction"] = {k: Path(v).name
                                        for k, v in extract(view, extraction, staged).items()}
                return result
            result["launch_returncode"] = launched.returncode

            # The event directory is resolved *before* the return code is judged, because a
            # deadline that fired is reported as a non-zero launch: `wait_worker` returns 1 for any
            # terminal status other than "completed". Reading the return code first would send a
            # timed-out attempt down the generic failure path, where its disposition, both of its
            # clocks and its evidence were all discarded — which is what an earlier revision of
            # this repair did.
            try:
                event_dir = Path(json.loads(launched.stdout)["event_dir"])
            except (ValueError, KeyError):
                event_dir = None

            # The monitor's disposition wins over anything gradeable. A worker stopped at its
            # deadline can still have left a complete-looking `report.md` behind — written moments
            # before it was terminated, or by a tool call that outlived the decision — and grading
            # that would turn a terminated attempt into an ordinary successful slot. The attempt is
            # accounted and preserved instead: `trajectory_began` is already true, so §11 C governs
            # and no retry follows from this.
            terminal = _terminal_disposition(event_dir) if event_dir is not None else {}
            result["terminal_status"] = terminal.get("status")
            result["timed_out"] = bool(terminal.get("timed_out"))
            # Both clocks, always. `worker_wall_seconds` exceeding the deadline while
            # `worker_monotonic_seconds` sits well under it is a suspended host, not an overrun.
            for key in ("worker_monotonic_seconds", "worker_wall_seconds"):
                if key in terminal:
                    result[key] = terminal[key]
            if terminal.get("termination") is not None:
                # Kept under its own name. The controller's `termination` replaces nothing: the
                # monitor's record is the evidence of what it was *refused*, which is the
                # measurement the whole design rests on.
                result["monitor_termination"] = terminal["termination"]
            if result["timed_out"]:
                result["validity"] = _mlr_run.HARNESS_FAILURE
                # `wait_worker` returns non-zero for any terminal status other than "completed",
                # so a noticed deadline arrives here as a non-zero launch. Left in place it would
                # make `execution_stage` read `launcher-refused` — "the launcher declined to start
                # the worker" — about an attempt whose worker demonstrably ran. Dropped, so the
                # stage derives to `worker-executed`, which is what happened. Found in review.
                result.pop("launch_returncode", None)
                # A monitor inside the view can *notice* a deadline but cannot act on one, so its
                # disposition is not taken as evidence that anything stopped. The controller stops
                # the attempt's pids itself and reports what it confirmed.
                result["termination"] = _stop_attempt(view.root, staged["run"], grace=grace)
                result["reason"] = (
                    f"the worker exceeded its deadline after "
                    f"{terminal.get('worker_monotonic_seconds')}s of monotonic execution; "
                    + _stop_summary(result["termination"]))
                # Evidence still comes back: the monitor bound the report and froze the scope at
                # termination, and this is what carries the session and workspace out of a view
                # that is about to be destroyed.
                result["extraction"] = {k: Path(v).name
                                        for k, v in extract(view, extraction, staged).items()}
                return result

            if launched.returncode != 0:
                blob = (launched.stdout + launched.stderr).lower()
                result["validity"] = _mlr_run.SETUP_FAILURE if (
                    "not found" in blob or "auth" in blob or "credential" in blob
                    or "rate" in blob) else _mlr_run.HARNESS_FAILURE
                result["reason"] = (launched.stderr or launched.stdout).strip()[:400]
                return result
            if event_dir is None:
                result["reason"] = "launcher produced no event directory"
                return result

            remaining = attempt_deadline - time.monotonic()
            if remaining <= 0:
                # The worker finished, but not inside the attempt's budget. Classifying anything
                # after this point would be grading work the deadline had already disallowed.
                result["validity"] = _mlr_run.HARNESS_FAILURE
                result["timed_out"] = True
                result["terminal_status"] = "controller-timeout"
                result["termination"] = _stop_attempt(view.root, staged["run"], grace=grace)
                result["reason"] = (f"the controller's {timeout}s deadline expired before the "
                                    f"attempt could be classified; "
                                    + _stop_summary(result["termination"]))
                result["extraction"] = {k: Path(v).name
                                        for k, v in extract(view, extraction, staged).items()}
                return result
            try:
                gate(view, staged, timeout=remaining)
            except subprocess.TimeoutExpired:
                # Previously this landed in the blanket `except Exception`, which stopped nothing:
                # the attempt was reported as a harness failure while its processes ran on.
                result["validity"] = _mlr_run.HARNESS_FAILURE
                result["timed_out"] = True
                result["terminal_status"] = "controller-timeout"
                result["termination"] = _stop_attempt(view.root, staged["run"], grace=grace)
                result["reason"] = (f"the controller's {timeout}s deadline expired while "
                                    f"classifying the attempt; "
                                    + _stop_summary(result["termination"]))
                result["extraction"] = {k: Path(v).name
                                        for k, v in extract(view, extraction, staged).items()}
                return result
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
    except BaseException:
        # Ctrl-C, or anything else that is not an `Exception`. Not swallowed — it is re-raised
        # immediately — but the attempt's own processes are stopped on the way out, because
        # everything inside the view would otherwise keep running and keep calling a provider.
        #
        # **This runs after the view has already been destroyed**, because a `with` block exits
        # before an enclosing handler is selected. So `attempt.json` is gone and with it the
        # recorded pids, which means neither the process-group nor the ancestry test can fire and
        # ownership rests on the command-line test alone. That still reaches the launcher, the
        # monitor, the worker and `wait_worker` — each carries a path under the view root in its
        # argv, and argv outlives the directory — but it does not reach a bare tool subprocess.
        # Reduced evidence, recorded as such, rather than a claim of clean teardown. Found in
        # review. A controller that is itself SIGKILLed cannot do even this, and there is no
        # in-view fallback because nothing inside the view can signal anything.
        if result.get("trajectory_began") and view_for_teardown is not None:
            result["interrupted"] = True
            result["termination"] = _stop_attempt(view_for_teardown.root, staged_for_teardown,
                                                  grace=grace)
            result["termination"]["ownership_reduced_to_command_line"] = True
        raise
    finally:
        result["elapsed_seconds"] = round(time.time() - started, 3)
        if extraction is not None:
            # Retaining evidence must not be able to destroy the attempt that produced it. This
            # block runs on the success path too, so an unusable `--keep` raised out of the function
            # *after* the outcome, the context ledger and the cost had all been computed: the money
            # was spent, the trajectory was lost, the temp directory below was never removed, and
            # the series loop's pre-attempt checkpoint became the only surviving row — a slot frozen
            # in §11 C by a mistyped path. Found in review. Reported like every other failure here,
            # and it does not invalidate the measurement: `extract` had already succeeded, and §11 D
            # is about that step rather than about copying its products somewhere convenient.
            if keep is not None and extraction.is_dir():
                try:
                    target = Path(keep) / f"{arm}-{int(started * 1000)}"
                    shutil.copytree(extraction, target, dirs_exist_ok=True)
                    result["evidence"] = str(target)
                except OSError as exc:
                    result["evidence_error"] = f"{type(exc).__name__}: {exc}"[:400]
            shutil.rmtree(extraction, ignore_errors=True)


def _process_table() -> list[dict[str, Any]] | None:
    """One snapshot of the process table, or `None` if it could not be taken.

    `None` and `[]` are different facts and must not share a representation: an empty table means
    nothing is running, while no table at all means nothing is *known*. Collapsing them let a
    failed `ps` report an attempt as cleanly stopped. Found in review.

    `ps` rather than a ppid walk alone. A descendant that calls `setsid` leaves its parent's group,
    and when its parent dies it is reparented to pid 1 — so for that shape neither the group nor the
    ancestry chain still recognises it.
    """
    try:
        done = subprocess.run(["/bin/ps", "-Ao", "pid=,ppid=,pgid=,command="],
                              capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    rows: list[dict[str, Any]] = []
    for line in done.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 3:
            continue
        try:
            rows.append({"pid": int(parts[0]), "ppid": int(parts[1]), "pgid": int(parts[2]),
                         "command": parts[3] if len(parts) > 3 else ""})
        except ValueError:
            continue
    return rows


def _owned_processes(view_root: Path, recorded: list[int]) -> dict[str, Any]:
    """Every live process this attempt owns, and nothing else.

    Returns the owned rows, the groups they lead, the recorded pids that could not be corroborated,
    and whether the process table was readable at all.

    A recorded pid is trusted only if its own command line still names this view. Between the
    launcher writing `attempt.json` and a deadline up to half an hour later, a recorded pid can
    exit and the number be reused by something unrelated; signalling it on the strength of the
    number alone would reach a process this attempt never owned. Corroborated roots are what the
    group and ancestry tests extend from, so an uncorroborated number cannot drag a stranger's
    group in behind it.

    From those roots, four ways a process is recognised, because no one of them is sufficient:

    * it is a corroborated recorded pid — the worker and its monitor;
    * it is still in the process group one of them leads, which is where the executor's tool
      subprocesses sit;
    * it descends from one of them, transitively, over the live snapshot;
    * its command line names this attempt's view root, which catches the processes the launcher
      never recorded at all — the in-view launcher itself and the `wait_worker` helper polling
      inside it, both of which inherit the *controller's* process group.

    The view root is a fresh `mkdtemp` path belonging to this slot alone, which is what makes the
    command-line test safe rather than reckless: no process outside this attempt can name it. The
    match is refused for an implausibly short root, so a truncated value cannot select the whole
    table. The controller and every process it descends from are excluded by pid, so no positive
    test can select them.

    **Known gap, measured not assumed.** A descendant that leaves the group *and* whose own command
    line does not name the view — an ordinary `git` or `node` invocation — is unrecognisable by any
    of the four once the intermediate that links it to a root has exited. `_stop_attempt` re-derives
    ownership while it works, which catches such a process while its parent still lives, but not
    after. The gap is stated in `MLR-eventbus-b1-timeout-audit.md` rather than papered over.
    """
    marker = str(view_root)
    rows = _process_table()
    if rows is None:
        return {"owned": [], "groups": [], "uncorroborated": sorted(set(recorded)),
                "table_unavailable": True}

    by_pid = {row["pid"]: row for row in rows}
    by_parent: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_parent.setdefault(row["ppid"], []).append(row)

    # Never the controller, and never anything it hangs from. An earlier revision excluded the
    # whole of the controller's *process group* instead, which looked equivalent and was not:
    # `sandbox-exec` is started without a new session, so the in-view launcher and the
    # `wait_worker` helper inherit the controller's group, and excluding the group excluded exactly
    # the processes that were being left behind.
    protected = {0, 1, os.getpid()}
    walker = os.getpid()
    while walker in by_pid:
        walker = by_pid[walker]["ppid"]
        if walker in protected:
            break
        protected.add(walker)

    def names_view(row: dict[str, Any]) -> bool:
        return len(marker) >= 12 and marker in row["command"]

    roots = {row["pid"] for row in rows
             if row["pid"] in recorded and row["pid"] not in protected and names_view(row)}
    uncorroborated = sorted(set(recorded) - roots)

    descendants: set[int] = set()
    frontier = list(roots)
    while frontier:
        for child in by_parent.get(frontier.pop(), []):
            if child["pid"] not in descendants:
                descendants.add(child["pid"])
                frontier.append(child["pid"])

    groups = {row["pgid"] for row in rows if row["pid"] in roots and row["pgid"] == row["pid"]}
    groups -= protected

    owned: list[dict[str, Any]] = []
    for row in rows:
        if row["pid"] in protected:
            continue
        if row["pid"] in roots:
            why = "recorded"
        elif row["pgid"] in groups:
            why = "process-group"
        elif row["pid"] in descendants:
            why = "descends-from-recorded"
        elif names_view(row):
            why = "names-the-view"
        else:
            continue
        owned.append({**row, "owned_because": why})
    return {"owned": owned, "groups": sorted(groups), "uncorroborated": uncorroborated,
            "table_unavailable": False}


def _attempt_processes(run_root: Path) -> list[int]:
    """The pids the launcher recorded for this attempt, if it got as far as recording any."""
    # `rglob`, not a fixed `phases/*/tasks/*/attempts/*` shape. The launcher's event-directory
    # layout is its own business and does vary — a glob that encoded one arrangement would silently
    # return no pids under another, and "no pids" is the input that makes everything downstream
    # conclude there was nothing to stop.
    pids: list[int] = []
    for path in sorted(Path(run_root).rglob("attempt.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for key in ("worker_pid", "launcher_pid"):
            value = data.get(key)
            if isinstance(value, int):
                pids.append(value)
    return pids


def _pid_alive(pid: int) -> bool:
    """Whether a pid is still running. `EPERM` counts as alive: it is a process we cannot signal,
    which is the opposite of a process that has stopped."""
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _signal_all(pids: Iterable[int], groups: Iterable[int], sig: int) -> list[dict[str, Any]]:
    """Signal each owned pid, and each group the attempt's roots lead.

    Both, because neither alone is enough. Individual pids reach a descendant that left the group;
    the group signal reaches a child forked *after* the snapshot was taken, which no list of pids
    can name. The groups are only those led by a corroborated root, so nothing unowned is in them.
    """
    sent: list[dict[str, Any]] = []
    for scope, target, call in ([("group", g, os.killpg) for g in groups]
                                + [("process", p, os.kill) for p in pids]):
        record: dict[str, Any] = {"scope": scope, "target": target}
        try:
            call(target, sig)
            record["delivered"] = True
        except ProcessLookupError:
            record["delivered"] = False
            record["already_exited"] = True
        except PermissionError as exc:
            record["delivered"] = False
            record["refused"] = f"EPERM (errno={exc.errno})"
        sent.append(record)
    return sent


def _stop_attempt(view_root: Path, run_root: Path, *, grace: float) -> dict[str, Any]:
    """Stop everything this attempt owns, then look again and say what is still running.

    Signals go to the whole owned set at once and the grace is waited **once**, not per process: a
    grace paid serially for each pid would multiply the overrun it exists to bound.

    Ownership is re-derived while waiting and **merged** into the watch set, never replaced. Merging
    is what catches a child forked after the first snapshot — the window is the whole grace, during
    which the worker is still alive and still driving tool calls. Replacing would lose a `setsid`
    descendant the moment its parent died, which is why the first version of this refused to
    re-derive at all and so missed the forked children instead. Found in review, twice.

    Survivors come from a liveness sweep, not from the signals having been delivered. Delivery is
    not death: a worker can trap `SIGTERM`, the semantic view refuses signals outright with
    `EPERM`, and a group leader exiting says nothing about the group.
    """
    recorded = _attempt_processes(run_root)
    scan = _owned_processes(view_root, recorded)
    record: dict[str, Any] = {"recorded_pids": recorded}
    if scan["uncorroborated"]:
        # A recorded pid whose command line no longer names this view. Either it exited and the
        # number was reused, or it exited and was reaped. Reported, and deliberately not signalled.
        record["uncorroborated_pids"] = scan["uncorroborated"]
    if scan["table_unavailable"]:
        # Nothing is known, which is not the same as nothing running. Never reported as stopped.
        return {**record, "found": 0, "stopped": False, "table_unavailable": True}

    watch: dict[int, dict[str, Any]] = {row["pid"]: row for row in scan["owned"]}
    groups = set(scan["groups"])
    record["found"] = len(watch)
    record["owned"] = [{k: row[k] for k in ("pid", "pgid", "owned_because")}
                       for row in watch.values()]
    if not watch and not groups:
        # Nothing was running. Said plainly, because it is a different fact from having stopped
        # something, and the two must not share a sentence.
        return {**record, "stopped": True, "nothing_was_running": True}

    def refresh() -> None:
        again = _owned_processes(view_root, recorded)
        if again["table_unavailable"]:
            return
        for row in again["owned"]:
            watch.setdefault(row["pid"], row)
        groups.update(again["groups"])

    def settle(limit: float) -> list[int]:
        deadline = time.monotonic() + max(0.0, limit)
        while time.monotonic() < deadline:
            refresh()
            if not [pid for pid in watch if _pid_alive(pid)]:
                return []
            time.sleep(0.05)
        refresh()
        return [pid for pid in watch if _pid_alive(pid)]

    record["sigterm"] = _signal_all(list(watch), groups, signal.SIGTERM)
    if not settle(grace):
        record["found"] = len(watch)
        return {**record, "stopped": True, "escalated": False, "survivors": []}

    record["escalated"] = True
    record["sigkill"] = _signal_all([pid for pid in watch if _pid_alive(pid)], groups,
                                    signal.SIGKILL)
    left = settle(grace)
    record["found"] = len(watch)
    record["owned"] = [{k: row[k] for k in ("pid", "pgid", "owned_because")}
                       for row in watch.values()]
    record["survivors"] = [{k: watch[pid][k] for k in ("pid", "pgid", "owned_because")}
                           for pid in left]
    record["stopped"] = not left
    return record


def _stop_summary(termination: dict[str, Any]) -> str:
    """The outcome in words, kept in step with what was actually established.

    Every qualification the structured record carries appears here too. The prose is what reaches a
    run report, and a reader of the prose must not end up better informed by reading the JSON.
    """
    caveat = ""
    if termination.get("uncorroborated_pids"):
        caveat = (f"; {len(termination['uncorroborated_pids'])} recorded pid(s) could not be "
                  "corroborated against this view and were not signalled")
    if termination.get("table_unavailable"):
        return ("the process table could not be read, so nothing could be identified or stopped"
                + caveat)
    if termination.get("nothing_was_running"):
        return "no process this attempt owned was still running" + caveat
    survivors = termination.get("survivors") or []
    if termination.get("stopped"):
        return (f"all {termination.get('found')} process(es) this attempt owned were confirmed "
                f"stopped{caveat}")
    return (f"{len(survivors)} of {termination.get('found')} process(es) this attempt owned are "
            f"STILL RUNNING after SIGKILL: {survivors}{caveat}")


def _terminal_disposition(event_dir: Path) -> dict[str, Any]:
    """What the monitor recorded about how the attempt ended, or nothing readable.

    An unreadable or absent `terminal.json` is reported as such rather than as "not a timeout": the
    caller then proceeds to the evidence gate, which is the check that decides whether there is
    anything gradeable. Silence here must not be able to assert that a deadline was respected.
    """
    path = Path(event_dir) / "terminal.json"
    if not path.is_file():
        return {"status": None, "terminal_missing": True}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": None, "terminal_unreadable": f"{type(exc).__name__}: {exc}"}


def harness_is_clean(*, fixture: Path = _mlr.FIXTURE) -> dict[str, Any]:
    """Whether the staged launcher carries any of the evidence the treatment controls."""
    return _hermetic.scan([HARNESS_SOURCE], sensitive(fixture=fixture))


def executor_identity(executor: Path) -> dict[str, str]:
    """What the staged executor is, without saying anything about how it authenticates."""
    executor = Path(executor)
    return {"name": executor.name,
            "sha256": hashlib.sha256(executor.read_bytes()).hexdigest()}
