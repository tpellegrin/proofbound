#!/usr/bin/env python3
"""A supervised goal-to-change path over the existing Proofbound helpers.

The coordinator supplies semantic decisions. This CLI derives progress from contracts,
attempts, gates and acceptances; it never interprets a review's prose.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

from dsd_state import atomic_json, run_path
from _freeze import current_candidate, freeze_identity
from _receipts import receipt
from _contract import declared_candidate
import _worker_profiles as profiles

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
MODEL = "deepseek/deepseek-v4-flash"
EXECUTOR = Path.home() / ".proofbound/executors/opencode-1.18.29-darwin-arm64/opencode"
QUALIFIED_DIGEST = profiles.OPENCODE_SHA256
STAGES = (("design", "requirements", "spec-author", "spec-reflector"),
          ("design", "consistency", None, "spec-reflector"),
          ("build", "implementation", "implementer", "reviewer"))


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def helper(name, *args):
    cp = subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                        text=True, capture_output=True)
    if cp.returncode:
        raise ValueError((cp.stderr or cp.stdout).strip())
    return json.loads(cp.stdout)


def command(run, action, *extra):
    return shlex.join([sys.executable, str(SCRIPTS / "pb_workflow.py"), action,
                       "--run", str(run), *map(str, extra)])


def doctor(args):
    """Readiness for one worker profile. Never generates a completion and never reads a key."""
    try:
        settings = profiles.resolve(args.worker_profile)
    except profiles.ProfileError as exc:
        return {"ready": False, "problems": [f"worker profile is invalid: {exc}"],
                "profile": {"valid": False, "selector": str(args.worker_profile)},
                "provider_requests": 0}
    return readiness(settings, args.executor)


def readiness(settings, executor):
    """What `doctor` reports for resolved settings, in layers that fail separately.

    Profile validity, the executor build, the boundary, the credential or endpoint the profile
    names, tool-loop compatibility and task qualification are different facts. Only the first four
    are checkable without a model, and this checks only those.
    """
    exe = Path(executor).expanduser().resolve()
    installed = exe.is_file() and os.access(exe, os.X_OK)
    supported = platform.system() == "Darwin" and platform.machine() == "arm64"
    version = None
    if installed:
        cp = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=15,
                            stdin=subprocess.DEVNULL)
        version = cp.stdout.strip() if cp.returncode == 0 else None
    entry = settings["credential"]["auth_entry"]
    auth = Path.home() / ".local/share/opencode/auth.json"
    configured = False
    if entry and auth.is_file():
        try:
            configured = entry in read(auth)  # never emit credential values
        except (ValueError, OSError):
            pass
    problems = []
    if not supported: problems.append("supported worker environment is macOS arm64 only")
    if sys.version_info < (3, 10): problems.append("Python >=3.10 required")
    if not installed: problems.append("pinned OpenCode executable is missing")
    if entry and not configured:
        problems.append("DeepSeek credential is not configured; no provider request made"
                        if entry == "deepseek" else
                        f"{entry!r} credential is not configured; no provider request made")
    if not shutil.which("git"): problems.append("git is missing")
    if not Path("/usr/bin/sandbox-exec").exists(): problems.append("macOS sandbox-exec boundary unavailable")
    boundary_available = False
    if Path("/usr/bin/sandbox-exec").exists():
        cp = subprocess.run(["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)", "/usr/bin/true"], capture_output=True, timeout=10)
        boundary_available = cp.returncode == 0
        if not boundary_available: problems.append("sandbox-exec cannot start in this process environment; run outside the enclosing sandbox")
    qualified = installed and digest(exe) == settings["executor"]["sha256"]
    if installed and not qualified: problems.append("executor bytes are not the experimentally qualified build")
    endpoint = profiles.probe_endpoint(settings)
    if endpoint.get("applicable") and not endpoint.get("reachable"):
        problems.append(
            f"local endpoint {endpoint['url']} is not reachable ({endpoint.get('error')}). Start "
            "your OpenAI-compatible server there, or edit the profile. This profile never falls "
            "back to a hosted model or a cloud credential")
    local = settings["network"]["mode"] == "loopback-only"
    worker = {"backend": "opencode-cli", "path": str(exe), "installed": installed,
              "configured": configured if entry else "no credential required",
              "version": version, "model": settings["model"], "variant": settings["variant"],
              "profile": settings["profile"]["id"], "profile_digest": settings["digest"],
              "billing": settings["billing"]["basis"], "network": settings["network"]["mode"],
              "experimentally_qualified_build": qualified,
              "documented_serving": settings["provider"].get("documented_serving"),
              "runtime_identity": settings["provider"].get("runtime_identity"),
              "qualification_scope": (
                  "none: no live observation of this configuration exists" if local else
                  "pb-handoff-2 observed this request while it served V4 Flash, before "
                  "2026-09-10; no retained live evidence covers the V4.1 Flash it is served by "
                  "now, and no goal-to-change run has been observed")}
    return {"ready": not problems, "problems": problems,
            "python": {"path": sys.executable, "version": platform.python_version(), "supported": sys.version_info >= (3, 10)},
            "worker": worker,
            "readiness": {
                "profile_valid": True,
                "executor_installed": installed, "executor_is_pinned_build": qualified,
                "boundary_process_available": boundary_available,
                "credential_configured": configured if entry else "not required",
                "endpoint": endpoint if endpoint.get("applicable") else "not applicable",
                "tool_loop": "not established: doctor requests no completion. "
                             "`evals/pb_qualify.py` replays the tool loop against a stand-in "
                             "endpoint; only a live run observes a real model",
                "task_qualification": "not established by doctor",
                "project_tooling": "not checked by doctor. A run that declares --toolchain runs "
                                   "its project check inside its own boundary at authorization; "
                                   "`status` reports the result"},
            "environment_supported": supported, "boundary_process_available": boundary_available,
            "boundary": "macOS sandbox-exec for launched processes; host coordinator is outside it",
            "codex": {"installed": shutil.which("codex") is not None,
                      "integration": "explicit status/continue; no hook or native worker dependency"},
            "provider_requests": 0}


def start(args):
    project = args.project.expanduser().resolve()
    if not project.is_dir(): raise ValueError("project must be an existing directory")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.change):
        raise ValueError("change must be a short path-safe identifier")
    goal = args.goal_file.read_text() if args.goal_file else args.goal
    if not goal or not goal.strip(): raise ValueError("supply a nonempty goal")
    if not 30 <= args.deadline_seconds <= 3600:
        raise ValueError("--deadline-seconds must be between 30 and 3600")
    settings = profiles.resolve(args.worker_profile)
    run = project / "DeepSeekAndDestroy" / "plans" / args.change / "runs" / "first"
    authority = project / "specs" / args.change
    if run.exists():
        if (run / "run-config.json").is_file():
            config = read(run / "run-config.json")
            if Path(config["goal"]).read_text() == goal and config["paths"]["project"] == str(project):
                # Same goal, same project — but the rest of the requested configuration is
                # immutable for a started run, and returning `existing: true` while silently
                # keeping the old value told the caller their new `--check` had taken effect when
                # it had not. Name every difference instead; change nothing.
                conflicts = []
                requested_check = args.check
                if requested_check is not None and requested_check != config.get("check_command"):
                    conflicts.append({"field": "--check", "requested": requested_check,
                                      "in_effect": config.get("check_command")})
                requested_exe = str(args.executor.expanduser().resolve())
                if requested_exe != config.get("executor", {}).get("path"):
                    conflicts.append({"field": "--executor", "requested": requested_exe,
                                      "in_effect": config.get("executor", {}).get("path")})
                in_effect = config.get("deadline", {}).get("seconds")
                if args.deadline_seconds != in_effect:
                    conflicts.append({"field": "--deadline-seconds",
                                      "requested": args.deadline_seconds, "in_effect": in_effect})
                requested_toolchain = (str(Path(args.toolchain).expanduser().absolute().resolve())
                                       if getattr(args, "toolchain", None) else None)
                if requested_toolchain != (config.get("toolchain") or {}).get("resolved"):
                    conflicts.append({"field": "--toolchain", "requested": requested_toolchain,
                                      "in_effect": (config.get("toolchain") or {}).get("resolved")})
                recorded = profiles.of(config)
                ignored = ({"legacy", "profile.source", "profile.path", "profile.source_sha256"}
                           if recorded.get("legacy") else set())
                fields = [d["field"] for d in profiles.differences(recorded, settings)
                          if d["field"] not in ignored]
                if fields:
                    # The recorded settings stay in effect; a profile file edited since start
                    # shows up here as its own fields, never as a silently different resume.
                    conflicts.append({"field": "--worker-profile",
                                      "requested": f"{settings['profile']['id']} "
                                                   f"(differs in {', '.join(fields)})",
                                      "in_effect": recorded["profile"]["id"]})
                if conflicts:
                    raise ValueError(
                        "this run already exists and its configuration is fixed; the requested "
                        "value(s) were NOT applied: "
                        + "; ".join(f"{c['field']} requested {c['requested']!r}, in effect "
                                    f"{c['in_effect']!r}" for c in conflicts)
                        + f". Inspect {run}, or start a different --change.")
                return {"initialized": False, "existing": True, "run": str(run),
                        "configuration_unchanged": True, "next": command(run, "status")}
        raise ValueError(f"existing or incomplete run at {run}; inspect it; nothing overwritten")
    if authority.exists(): raise ValueError(f"authority directory exists: {authority}; choose another --change")
    cp = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if cp.returncode or Path(cp.stdout.strip()).resolve() != project:
        raise ValueError("supported project is a Git worktree root; initialize Git first")
    baseline = subprocess.check_output(["git", "-C", str(project), "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "-C", str(project), "status", "--porcelain"], text=True).strip():
        raise ValueError("start needs a clean project to retain a usable baseline patch; preserve pending work in a commit or separate worktree")
    if not authority.resolve().is_relative_to(project): raise ValueError("authority path escapes project through a symlink")
    if getattr(args, "toolchain", None):
        import _toolchain
        problems = _toolchain.check(args.toolchain, project)
        if problems: raise ValueError("--toolchain cannot be prepared: " + "; ".join(problems) + "; nothing was created")
    authority.mkdir(parents=True)
    run.mkdir(parents=True)
    goal_path = authority / "goal.md"
    goal_path.write_text(goal)
    req = authority / "requirements.md"
    req.write_text("# Proposed requirements — not accepted\n\nState numbered obligations, public compatibility, domain, checks and unresolved decisions.\n")
    graph, ledger = authority / "graph.json", authority / "ledger.json"
    atomic_json(graph, {"format": "proofbound-change-graph-v1", "artifacts": {str(req.relative_to(project)): []}})
    atomic_json(ledger, {"format": "proofbound-change-ledger-v1", "artifact_identity": "proofbound-artifact-text-v1", "artifacts": {}})
    runtime = Path(tempfile.mkdtemp(prefix="pb-workflow-", dir="/private/tmp" if platform.system() == "Darwin" else None))
    (runtime / "home").mkdir(); (runtime / "session").mkdir(); (runtime / "tmp").mkdir()
    if settings["executor"].get("startup"):
        # The executor's configuration directory, written now so no executor process ever has to.
        import _executor_startup
        _executor_startup.stage(runtime / "home")
    exe = args.executor.expanduser().resolve()
    config = {"format": "proofbound-supervised-workflow-v1", "mode": "live", "goal": str(goal_path),
              "goal_sha256": digest(goal_path), "requirements": str(req), "baseline": baseline,
              "interpreter": {"executable": sys.executable, "version": platform.python_version()},
              "executor": {"path": str(exe), "sha256": digest(exe) if exe.is_file() else None},
              "model": settings["model"], "variant": settings["variant"],
              "worker_profile": settings,
              "auto_flag": "--auto", "home": str(runtime / "home"),
              "deadline": {"seconds": args.deadline_seconds}, "check_command": args.check,
              "policy": {"aggregate_limit": 0, "reserve": 0, "launch_ceiling": 0, "repair_cycles": 1},
              "paths": {"project": str(project), "run_root": str(run), "ledger": str(ledger),
                        "graph": str(graph), "freezes": str(authority / "freezes"),
                        "consistency": str(authority / "consistency"), "session_db": str(runtime / "session/worker.db")}}
    # A local profile's executor configuration is written now, not at authorization: an offline
    # launch without it would let the executor fall back to its own default — a hosted model.
    config.update(profiles.write_opencode_config(settings, runtime))
    if getattr(args, "toolchain", None):
        # Declared, copied into the runtime and recorded by content now; verified before every launch.
        import _toolchain
        config["toolchain"] = _toolchain.prepare(args.toolchain, runtime, project)
    rules = helper("prepare_worker_rules.py", "--project-root", project, "--run-root", run,
                   "--plan", goal_path, "--model", settings["model"],
                   "--rule", "Review requirements, code and checks before reading a producer summary; record what you saw.")
    atomic_json(run / "state.json", {"project_worktree": str(project), "run_root": str(run),
        "execution_status": "active", "next_action": "propose requirements; no acceptance has been earned",
        "worker_rules": rules, "worker_runtime": {"harness": "opencode-cli", "model": settings["model"],
                                                  "opencode": {"run_db": config["paths"]["session_db"]}},
        "phases": {"design": {"status": "in-progress", "tasks": {}}, "build": {"status": "pending", "tasks": {}}}})
    atomic_json(run / "run-config.json", config)
    (run / "CONTINUE.md").write_text(f"# Continue Proofbound\n\nRead `{ROOT / 'docs/operator-guide.md'}`.\n\nRun `{command(run, 'status')}`.\n\nOwner goal: `{goal_path}`. Routine decisions within it are delegated; material goal changes, policy conflicts and spending need owner authority.\n")
    return {"initialized": True, "run": str(run), "accepted": False, "next": command(run, "status")}


def config_for(run):
    config = read(run / "run-config.json")
    if Path(config["paths"]["run_root"]).resolve() != run: raise ValueError("run identity mismatch")
    if digest(config["goal"]) != config["goal_sha256"]: raise ValueError("owner goal changed; new goal authority requires a new run")
    profiles.of(config)  # refuse a run whose recorded worker settings no longer match their digest
    return config


def ledger_for(run, c):
    """The run's launch ledger, always under the run's own billing basis — never a default."""
    from _launch_budget import LaunchLedger
    settings = profiles.of(c)
    policy = c["policy"]
    return LaunchLedger(run / "launch-ledger.json", limit=policy["aggregate_limit"],
                        reserve=policy["reserve"], ceiling=policy["launch_ceiling"],
                        repair_cycles=policy.get("repair_cycles", 1),
                        billing=settings["billing"],
                        output_token_allowance=settings["resources"]["output_token_allowance"])


def candidate(config):
    p = config["paths"]
    return freeze_identity(current_candidate(Path(p["graph"]), Path(p["ledger"]), Path(p["project"]))[2])


def task_args(run, phase, task):
    return ["--run-root", run, "--phase-id", phase, "--task-id", task]


def authority_args(config):
    p = config["paths"]
    return ["--graph", p["graph"], "--ledger", p["ledger"], "--project-root", p["project"], "--consistency", p["consistency"]]


def contract(config, task, *, revision=1, instruction=None):
    run = Path(config["paths"]["run_root"])
    project = Path(config["paths"]["project"])
    req = str(Path(config["requirements"]).relative_to(project))
    goal = str(Path(config["goal"]).relative_to(project))
    purposes = {"requirements": "proposal-reflection", "consistency": "consistency-reflection", "implementation": "implementation-review"}
    text = f"# Task {task}\nContract revision: r{revision:04d}\n\nOwner goal: `{goal}`, sha256 `{config['goal_sha256']}`.\n\n## Review purpose\n- {purposes[task]}\n\n"
    if task != "requirements": text += f"## Proofbound candidate\n- {candidate(config)}\n\n"
    objectives = {
        "requirements": f"Propose implementable numbered requirements in `{req}` from the owner's goal and existing project. Inspect public interfaces and tests. State compatibility, domain, check command `{config['check_command']}`, and unresolved choices. Do not silently narrow or contradict the goal. A fresh spec-reflector must challenge the proposal, identify concrete witnesses for contradictions, and state coverage. The coordinator adjudicates; no acceptance is seeded.",
        "consistency": f"Judge joint coherence of the goal and accepted `{req}` against the named candidate. This candidate has one requirements member: state that narrow coverage. Report contradictions and unresolved choices without choosing new goal authority.",
        "implementation": f"Implement accepted `{req}` under the named candidate. Preserve public compatibility. Add meaningful project checks and run `{config['check_command']}`. Do not edit governing specs or the run tree. A fresh reviewer must inspect requirements, code and checks before reading the implementer's summary, state coverage and defects. Diagnostics remain available; fresh context does not prove statistical independence."}
    text += "## Objective\n" + objectives[task] + "\n\n"
    if instruction: text += "Coordinator revision instruction: " + instruction + "\n\n"
    if task == "implementation":
        text += "## Accepted requirements snapshot\nUse these admitted bytes even if later project intent moves.\n\n"
        text += "\n".join("    " + line for line in Path(config["requirements"]).read_text().splitlines()) + "\n\n"
    if task == "requirements": text += f"## Allowed source changes\n- `{req}`\n\n"
    elif task == "consistency": text += "## Allowed source changes\nNONE\n\n"
    text += "## Acceptance criteria\n- AC-001 — satisfy the objective and public compatibility constraints.\n- AC-002 — review states coverage, findings and unresolved issues; coordinator judges semantics.\n"
    path = run / "phases" / ("build" if task == "implementation" else "design") / "tasks" / task / "contracts" / f"r{revision:04d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != text: raise ValueError("existing contract differs; explicit new revision required")
    if not path.exists(): path.write_text(text)
    return path


def _status(run):
    c = config_for(run); state = read(run / "state.json")
    settings = profiles.of(c)
    base = {"run": str(run), "project": c["paths"]["project"], "goal": c["goal"],
            "baseline": c["baseline"],
            "worker": {"profile": settings["profile"]["id"], "digest": settings["digest"],
                       "model": settings["model"], "variant": settings["variant"],
                       "billing": settings["billing"]["basis"],
                       "legacy_record": settings["legacy"]},
            "delivery_state": ("sealed" if (run / "delivery/manifest.json").exists() else "incomplete" if (run / "delivery").exists() else "absent"),
            "spending_authorized": c["policy"]["launch_ceiling"] > 0}
    admitted = state["phases"]["build"]["tasks"].get("implementation", {}).get("admission")
    for phase, name, writer, reviewer in STAGES:
        task = state["phases"][phase]["tasks"].get(name, {})
        if name == "consistency" and task.get("current_contract") and not admitted:
            old = declared_candidate(run_path(run, task["current_contract"]["path"]).read_text())
            if old != candidate(c):
                return {**base, "phase": phase, "task": name, "action": "bind", "next": command(run, "continue"),
                        "reason": "requirements changed; fresh consistency review under new candidate required"}
        if task.get("status") == "accepted":
            if name == "requirements":
                ledger = read(c["paths"]["ledger"])
                rel = str(Path(c["requirements"]).relative_to(c["paths"]["project"]))
                record = ledger["artifacts"].get(rel, {})
                if record.get("review", {}).get("gate_sha256") != task.get("accepted", {}).get("source_gate", {}).get("sha256"):
                    return {**base, "action": "record-requirements", "phase": phase, "task": name, "next": command(run, "continue")}
            if name == "consistency":
                cid = (declared_candidate(run_path(run, task["current_contract"]["path"]).read_text())
                       if admitted else candidate(c))
                from _consistency import lookup
                if lookup(Path(c["paths"]["consistency"]), cid)["state"] == "absent":
                    return {**base, "action": "record-consistency", "phase": phase, "task": name,
                            "reason": "qualifying acceptance retained; legitimate parent recovery", "next": command(run, "continue")}
            continue
        common = {**base, "phase": phase, "task": name}
        if not task.get("current_contract"):
            return {**common, "action": "bind", "next": command(run, "continue")}
        attempt = task.get("current_attempt") or {}
        if not attempt:
            return {**common, "action": "launch", "role": writer or reviewer, "next": command(run, "continue")}
        event = run_path(run, attempt["event_dir"])
        if not (event / "terminal.json").exists():
            return {**common, "action": "blocked", "reason": "prior attempt has no terminal record; inspect liveness and unknown spend; no automatic relaunch", "evidence": str(event)}
        gate = event / "evidence-gate.json"
        if not gate.exists(): return {**common, "action": "gate", "next": command(run, "continue")}
        g = read(gate)
        if not g.get("integrity_ok"):
            return {**common, "action": "blocked", "reason": "integrity failure; inspect findings before repair", "evidence": str(gate)}
        if g["role"] != reviewer:
            return {**common, "action": "launch", "role": reviewer, "next": command(run, "continue")}
        pending = pending_owner(run, gate)
        if pending:
            return {**common, "action": "blocked", "owner_request": pending["result"]["reason"],
                    "request_receipt": pending["path"],
                    "next": command(run, "resolve-owner", "--owner-response", "<actual owner decision>")}
        outstanding = pending_repair(run, gate)
        if outstanding:
            return {**common, "action": "blocked",
                    "pending_repair": outstanding["reason"],
                    "decided_at": outstanding["decided_at"],
                    "request_receipt": outstanding["path"],
                    "reason": "a repair was already decided for this review and has not been "
                              "carried out; revise the requirements it named, or supersede that "
                              "decision explicitly with a reason",
                    "next": command(run, "revise", "--reason", outstanding["reason"])}
        return {**common, "action": "adjudicate", "evidence": str(event / "report.md"), "gate": str(gate),
                "decision": "Judge coverage, contradictions and findings against owner goal. Accept only adequate review and output; request repair for defects or owner decision for unresolved scope/policy.",
                "next": command(run, "decide", "--decision", "accept", "--reason", "<your adjudication>")}
    if base["delivery_state"] == "sealed":
        # Proposing `finish` here and then refusing it was a loop with no exit: the next action a
        # resuming coordinator was told to take could not succeed. A sealed delivery is the end.
        delivery = run / "delivery"
        # The manifest is a flat path->digest map; it carries no timestamp, so none is reported.
        # What the delivery *does* record about itself is in handoff.json.
        handoff = read(delivery / "handoff.json") if (delivery / "handoff.json").is_file() else {}
        patch = next((p.name for p in delivery.glob("*.patch")), "change.patch")
        return {**base, "action": "complete", "delivery": str(delivery),
                "outcome": handoff.get("outcome"),
                "report_source": handoff.get("report_source"),
                "delivered_head": handoff.get("head"),
                "inspect": {"patch": str(delivery / patch),
                            "handoff": str(delivery / "handoff.json"),
                            "manifest": str(delivery / "manifest.json"),
                            "apply": shlex.join(["git", "-C", base["project"], "apply",
                                                 str(delivery / patch)])},
                "next": None}
    if base["delivery_state"] == "incomplete":
        return {**base, "action": "blocked",
                "reason": "a delivery directory exists without a manifest, so sealing did not "
                          "complete; inspect it and remove or complete it deliberately",
                "delivery": str(run / "delivery"), "next": None}
    return {**base, "action": "finish", "next": command(run, "finish", "--report", "<coordinator-report.md>")}




def pending_repair(run, gate):
    """A repair the coordinator asked for and nothing has yet fulfilled.

    Derived from the durable adjudication receipts, the same way `pending_owner` is, rather than
    held in memory by the process that made the decision. A `decide --decision repair` on
    consistency returns a `revise` instruction and changes no task state, so without this a fresh
    `status` re-proposed adjudication as though the decision had never been made — and a resuming
    coordinator would have adjudicated the same evidence twice.

    Superseded only by an actual `requirements revision`, which is the act the instruction asked
    for. Nothing here reads a reviewer's prose; it reads what the coordinator decided.
    """
    records = []
    for path in (run / "receipts").glob("*.json"):
        record = read(path)
        record["path"] = str(path)
        records.append(record)
    decisions = [r for r in records if r["action"] == "coordinator adjudication"
                 and r["identities"].get("gate") == str(gate)
                 and r["result"].get("decision") == "repair"]
    if not decisions: return None
    latest = max(decisions, key=lambda r: r["observed_at"])
    revised = [r for r in records if r["action"] == "requirements revision"
               and r["observed_at"] > latest["observed_at"]]
    if revised: return None
    return {"path": latest["path"], "reason": latest["result"]["reason"],
            "decided_at": latest["observed_at"]}


def pending_owner(run, gate):
    records = []
    for path in (run / "receipts").glob("*.json"):
        record = read(path)
        record["path"] = str(path)
        records.append(record)
    decisions = [r for r in records if r["action"] == "coordinator adjudication"
                 and r["identities"].get("gate") == str(gate)]
    if not decisions: return None
    latest = max(decisions, key=lambda r: r["observed_at"])
    if latest["result"]["decision"] != "owner": return None
    if any(r["action"] == "owner decision resolution" and r["identities"].get("request_receipt") == latest["path"] for r in records):
        return None
    return latest


def supervision(run):
    """A launch supervisor's state, before anything else: while one runs, nothing else may start."""
    return _supervision_state(run)[1]


def _supervision_state(run):
    """The record read once, and the state derived from that same read. A caller that waits must
    wait on this record: read again, the supervisor may have finished and removed it."""
    import _supervision
    record = _supervision.read_active(run)
    if record is None:
        return None, None
    state = _supervision.alive(record) if "unreadable" not in record else False
    if state is True:
        return record, {"action": "running", "reason": "a supervised launch is in progress",
                "supervisor": {k: record.get(k) for k in ("mode", "pid", "stage", "slot",
                                                          "created_at", "host_deadline_at")},
                "next": command(run, "continue") + "  # waits for it; launches nothing new"}
    return record, {"action": "blocked",
                    "reason": "the run's launch supervisor is " + ("not running" if state is False
                                                                   else "unverifiable")
                              + " and its launch was not finalized; inspect with recover",
                    "next": command(run, "recover")}


def status(run):
    supervised = supervision(run)
    if supervised is not None:
        return supervised
    result = _status(run)
    if result.get("action") == "blocked" and "no terminal record" in str(result.get("reason")):
        result["next"] = command(run, "recover") + "  # read-only: what the attempt left"
    if result["action"] == "launch":
        c = config_for(run)
        ledger = ledger_for(run, c)
        verdict = ledger.admit(phase=result["phase"], task=result["task"], role=result["role"],
                               run_root=run, db=c["paths"]["session_db"])
        if not verdict["admit"]:
            return {**result, "action": "blocked", "blocked_action": "launch", "reason": verdict["why"],
                    "next": ("Run " + command(run, "recover") + " to reconcile an interrupted launch from retained evidence"
                             if ledger.unresolved() else
                             "Supply explicit owner spending authority if none exists; otherwise reconcile retained launch/usage evidence. Never automatically buy another trajectory."),
                    "accounting": verdict["spend"]}
    tooling = project_tooling(run)
    if tooling is not None:
        result["project_tooling"] = tooling
    return result


def project_tooling(run):
    """Whether the project's own check has run inside this run's boundary. Only a run that declared
    a toolchain has one to report; being able to reach the provider says nothing about it."""
    record = read(run / "run-config.json").get("toolchain")
    if not record:
        return None
    check = record.get("boundary_check")
    out = {"toolchain": {k: record.get(k) for k in ("declared", "node_version", "npm_version")}}
    if check is None:
        return {**out, "verified": False, "why": "not checked yet: authorization runs the project "
                                                 "check inside the boundary"}
    return {**out, "verified": bool(check.get("passed")),
            "check": {k: check.get(k) for k in ("command", "returncode", "seconds", "checked_at")},
            **({} if check.get("passed") else {"why": "the project check did not pass inside the "
                                                      "boundary; see project-tooling-check.json"})}


def continue_run(run):
    record, supervised = _supervision_state(run)
    if supervised is not None:
        if supervised["action"] != "running":
            return supervised
        # Wait for the launch already in progress, by the token just seen running; start nothing.
        # Its result outlives its record, so a supervisor that finishes now is still reported.
        import _supervision
        result = _supervision.wait(run, record)
        return {"launch": {**result, "supervisor": {"token": record["token"], "pid": record["pid"],
                                                    "mode": record["mode"], "attached": True}},
                "next": command(run, "status")}
    c = config_for(run); s = _status(run); p = c["paths"]
    action = s["action"]
    if action in {"blocked", "adjudicate", "finish"}: return s
    phase, task = s["phase"], s["task"]
    common = task_args(run, phase, task)
    if action == "bind":
        if task != "requirements":
            helper("pb_freeze.py", "create", "--graph", p["graph"], "--ledger", p["ledger"], "--project-root", p["project"], "--into", p["freezes"])
        current = read(run / "state.json")["phases"][phase]["tasks"].get(task, {}).get("current_contract")
        revision = (int(current["revision"]) + 1) if current else 1
        path = contract(c, task, revision=revision)
        if task == "implementation": helper("pb_execution.py", "admit", *common, "--contract", path, *authority_args(c))
        else: helper("dsd_state.py", "bind-contract", *common, "--contract", path)
    elif action == "record-requirements":
        accepted = read(run / "state.json")["phases"][phase]["tasks"][task]["accepted"]["source_gate"]
        if digest(accepted["path"]) != accepted["sha256"]:
            raise ValueError("accepted requirements gate changed")
        assert_review_current(run, c, Path(accepted["path"]), paths=[c["requirements"], c["goal"]])
        helper("pb_ledger.py", "record", *common, "--artifact", c["requirements"], "--ledger", p["ledger"])
    elif action == "record-consistency":
        accepted = read(run / "state.json")["phases"][phase]["tasks"][task]
        cid = declared_candidate(run_path(run, accepted["current_contract"]["path"]).read_text())
        helper("pb_consistency.py", "record", *common, "--freeze", Path(p["freezes"]) / (cid + ".json"), "--into", p["consistency"])
    elif action == "gate": helper("dsd_attempt.py", "gate", *common)
    elif action == "launch":
        from _supervised_launch import launch
        result = launch(run, phase=phase, task=task, role=s["role"])
        return {"launch": result, "next": command(run, "status")}
    return status(run)


def decide(args):
    run = args.run.resolve(); c = config_for(run); s = status(run)
    if s["action"] != "adjudicate": raise ValueError("no fresh clean qualifying review awaits adjudication")
    if not args.reason.strip(): raise ValueError("record a substantive adjudication")
    receipt(run, "coordinator adjudication", {"decision": args.decision, "reason": args.reason,
            "reported_not_proven": True}, phase=s["phase"], task=s["task"], gate=s["gate"], gate_sha256=digest(s["gate"]))
    if args.decision == "accept":
        assert_review_current(run, c, Path(s["gate"]))
        if s["task"] == "implementation":
            check_project(run, c)
            assert_review_current(run, c, Path(s["gate"]))
        helper("dsd_state.py", "accept-task", *task_args(run, s["phase"], s["task"]), "--evidence-gate", s["gate"])
    elif args.decision == "repair":
        if s["task"] == "consistency":
            return {"action": "blocked", "reason": "consistency defect requires revised requirements and renewed authority; run revise with a within-goal correction, or request owner authority for a material goal/policy change", "next": command(run, "revise", "--reason", args.reason)}
        note = run / "decisions" / (str(len(list((run / "receipts").glob('*.json')))) + ".md")
        note.parent.mkdir(exist_ok=True); note.write_text(args.reason)
        from _supervised_launch import launch
        return launch(run, phase=s["phase"], task=s["task"], role="spec-author" if s["task"] == "requirements" else "fixer", inputs=[str(note)])
    else:
        return {"action": "owner-decision-required", "request": args.reason}
    return status(run)



def assert_review_current(run, c, gate, paths=None):
    baseline = gate.parent / "scope-baseline.json"
    result = helper("scope_snapshot.py", "compare", "--root", c["paths"]["project"], "--baseline", baseline)
    changed = result["changed"]
    if paths is not None:
        relative = {str(Path(p).relative_to(c["paths"]["project"])) for p in paths}
        changed = [entry for entry in changed if entry["path"] in relative]
    if changed or (paths is None and result.get("git_head_changed")):
        raise ValueError("project changed since the fresh review; review the new bytes before acceptance/delivery")


#: The project's own check gets its own bound, separate from the worker deadline and from any
#: teardown grace. A check that hangs is a different failure from a worker that hangs, and sharing
#: one number would make the evidence say the wrong thing about which one it was.
CHECK_TIMEOUT_SECONDS = 600


def coordinator(args):
    """Record who is coordinating this run, and how that was established.

    Three separate facts, never merged. `requested` is the configuration you chose. `self_reported`
    is what the coordinating agent says it is — a claim, retained as one, because an agent naming
    its own model is not evidence. `observed` is runtime metadata the host actually exposes, which
    most hosts do not; absent is recorded as absent rather than filled in from the other two.

    Recording a coordinator changes nothing about the run: not the worker backend, not the
    governing authority, not prior evidence, not the remaining allowances. A different capable
    coordinator may continue the same run, and the record simply gains another entry.
    """
    run = args.run.resolve()
    config_for(run)                              # refuse on a run this CLI does not understand
    entry = {"requested": args.requested,
             "self_reported": args.self_reported,
             "observed": args.observed,
             "evidence": ("host-provided runtime metadata" if args.observed else
                          "none; this host exposes no coordinator identity to the run"),
             "worker_backend_unchanged": True}
    path = receipt(run, "coordinator identity", entry)
    history = [read(p)["result"] for p in sorted((run / "receipts").glob("*.json"))
               if read(p)["action"] == "coordinator identity"]
    return {"recorded": entry, "receipt": path, "coordinators_recorded": len(history),
            "note": "requested, self-reported and observed identity are distinct; no model "
                    "identifier is inferred and none is substituted",
            "next": command(run, "status")}


def check_project(run, c):
    """Run the project's declared check, bounded, without mutating the project.

    `PYTHONDONTWRITEBYTECODE` because the check used to write `__pycache__/*.pyc` into the project
    and the stale-review guard then compared those new bytes against the reviewer's scope baseline
    and refused acceptance. The check invalidated the very review it was checking, and every
    fixture in this repository happened to gitignore `__pycache__`, so nothing caught it. An
    ordinary Python project could not be accepted at all.
    """
    timeout = c.get("check_timeout_seconds", CHECK_TIMEOUT_SECONDS)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if c.get("toolchain"):
        import _toolchain
        why = _toolchain.problems(c)
        if why:
            path = receipt(run, "project checks", {"command": c["check_command"], "returncode": None,
                           "refused": why})
            raise ValueError("project checks refused: " + "; ".join(why) + f"; evidence {path}; no acceptance")
        env["PATH"] = str(Path(c["toolchain"]["prepared"]) / "bin") + os.pathsep + env.get("PATH", "")
        env.update(_toolchain.WORKER_NPM_ENV)
    try:
        cp = subprocess.run(shlex.split(c["check_command"]), cwd=c["paths"]["project"],
                            capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as expired:
        def text(stream):
            if stream is None: return ""
            return stream.decode(errors="replace") if isinstance(stream, bytes) else stream
        path = receipt(run, "project checks", {
            "command": c["check_command"], "returncode": None, "timed_out": True,
            "timeout_seconds": timeout, "stdout": text(expired.stdout)[-8000:],
            "stderr": text(expired.stderr)[-8000:],
            "note": "the check did not finish within its own bound; whether it would have passed "
                    "is unknown, which is not the same as failing"})
        raise ValueError(f"project checks did not finish within {timeout}s; evidence {path}; "
                         f"no acceptance")
    path = receipt(run, "project checks", {"command": c["check_command"], "returncode": cp.returncode,
                   "timeout_seconds": timeout,
                   "stdout": cp.stdout[-8000:], "stderr": cp.stderr[-8000:]})
    if cp.returncode: raise ValueError(f"project checks failed; evidence {path}; no acceptance")
    return path


def finish(args):
    run = args.run.resolve(); c = config_for(run)
    if args.outcome == "accepted":
        current = status(run)["action"]
        if current == "complete":
            # Distinguish "already done" from "not ready". Both used to say the latter.
            raise ValueError(
                f"this run already has a sealed delivery at {run / 'delivery'}; nothing was "
                f"overwritten. Inspect it, or use --into for a separate copy.")
        if current == "blocked" and (run / "delivery").exists():
            raise ValueError(
                f"a delivery directory exists at {run / 'delivery'} without a manifest, so an "
                f"earlier sealing did not complete; inspect and remove it deliberately.")
        if current != "finish":
            raise ValueError("all required tasks must be accepted before delivery")
    task = read(run / "state.json")["phases"]["build"]["tasks"].get("implementation", {})
    gate = None
    if args.outcome == "accepted":
        gate = Path(task["accepted"]["source_gate"]["path"])
        if digest(gate) != task["accepted"]["source_gate"]["sha256"]:
            raise ValueError("accepted gate changed; cannot deliver")
        assert_review_current(run, c, gate)
    report = args.report.read_text()
    if not report.strip(): raise ValueError("coordinator report must explain change, decisions and unresolved issues")
    out = args.into.resolve() if args.into else run / "delivery"
    if out.exists(): raise ValueError(f"delivery already exists: {out}; preserve it; use --into with a new directory for an interrupted seal")
    if out != run / "delivery" and out.is_relative_to(Path(c["paths"]["project"])):
        raise ValueError("a custom --into must be outside the project to avoid recursive evidence collection")
    check = check_project(run, c) if args.outcome == "accepted" else None
    if gate: assert_review_current(run, c, gate)
    out.mkdir(parents=True)
    (out / "coordinator-report.md").write_text(report)
    project = c["paths"]["project"]
    patch = subprocess.check_output(["git", "-C", project, "diff", "--binary", c["baseline"], "--", ".", ":(exclude)DeepSeekAndDestroy"])
    untracked = subprocess.check_output(["git", "-C", project, "ls-files", "--others", "--exclude-standard", "-z"]).decode().split('\0')
    for rel in filter(None, untracked):
        if rel.startswith("DeepSeekAndDestroy/"): continue
        cp = subprocess.run(["git", "diff", "--no-index", "--binary", "--", "/dev/null", rel], cwd=project, capture_output=True)
        if cp.returncode not in (0, 1): raise ValueError("could not include untracked file in delivery patch")
        patch += cp.stdout
    patch_name = "change.patch" if args.outcome == "accepted" else "unaccepted.patch"
    (out / patch_name).write_bytes(patch)
    from _launch_budget import spend
    settings = profiles.of(c)
    account = spend(run, c["paths"]["session_db"], model=settings["model"],
                    limit=c["policy"]["aggregate_limit"], reserve=c["policy"]["reserve"],
                    billing=settings["billing"],
                    output_token_allowance=settings["resources"]["output_token_allowance"])
    ledger = ledger_for(run, c)
    if ledger.unresolved():
        account = {**account, "complete": False, "unknown_charges": True,
                   "unresolved_slots": [slot["slot"] for slot in ledger.unresolved()],
                   "claim": "unclassified launch intents; no inference of zero spend"}
    atomic_json(out / "usage.json", account)
    from _usage_events import events_from_db
    events = events_from_db(Path(c["paths"]["session_db"]))
    atomic_json(out / "usage-events.json", events)
    import _worker_profile
    observed = _worker_profile.observed_identity(events["rows"])
    # Allowlist evidence, never credentials, raw logs, prompts or session databases.
    retained = {"state.json", "run-config.json", "launch-ledger.json", "CONTINUE.md"}
    for source in run.rglob("*"):
        rel = source.relative_to(run)
        if not source.is_file() or "delivery" in rel.parts: continue
        if (len(rel.parts) == 1 and source.name in retained) or rel.parts[0] == "receipts" or (
                rel.parts[0] == "phases" and ("contracts" in rel.parts or source.name in {
                    "attempt.json", "terminal.json", "launch-reservation.json", "evidence-gate.json",
                    "scope-baseline.json", "scope-diff.json", "report.md"})):
            target = out / "evidence" / rel
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, target)
    shutil.copytree(Path(c["goal"]).parent, out / "authority")
    from _execution import bound_candidates
    atomic_json(out / "handoff.json", {"baseline": c["baseline"], "head": subprocess.check_output(["git", "-C", project, "rev-parse", "HEAD"], text=True).strip(),
                "outcome": args.outcome, "report_source": args.report_source, "report_is_claim": True, "checks": check,
                "bindings": bound_candidates(run),
                "worker_profile": {"id": settings["profile"]["id"], "digest": settings["digest"],
                                   "kind": settings["profile"]["kind"], "model": settings["model"],
                                   "variant": settings["variant"], "billing": settings["billing"],
                                   "network": settings["network"], "legacy_record": settings["legacy"]},
                "observed_worker_identity": {
                    **observed,
                    "note": "as the executor recorded it: the requested model id per message. A "
                            "local server's weights, quantization and template are not observed"},
                "run_retained_at": str(run), "runtime_retained_at": str(Path(c["home"]).parent),
                "limitation": "run-tree binding only; this package does not close L3/L4 durable implementation provenance"})
    atomic_json(out / "manifest.json", {str(p.relative_to(out)): digest(p) for p in out.rglob("*") if p.is_file()})
    return {"delivery": str(out), "outcome": args.outcome, "patch": str(out / patch_name), "retained_run": str(run), "cleanup": "explicit only; contains private project data"}


def verify_delivery(args):
    """Apply a sealed delivery to a fresh checkout of its recorded baseline and rerun its checks.

    Reads only the delivery directory — it works after the delivery is copied elsewhere — plus a
    repository holding the baseline commit, which defaults to the project the run recorded. It
    never touches that project or the run: everything happens in a new directory, and the
    result is written there. A file that no longer matches the manifest is reported, and the patch
    is not applied from a delivery that changed.
    """
    delivery = args.delivery.resolve()
    into = args.into.resolve()
    if into.exists(): raise ValueError(f"{into} exists; verification never overwrites")
    manifest = read(delivery / "manifest.json")
    altered = sorted(rel for rel, sha in manifest.items()
                     if not (delivery / rel).is_file() or digest(delivery / rel) != sha)
    unlisted = sorted(str(p.relative_to(delivery)) for p in delivery.rglob("*")
                      if p.is_file() and p.name != "manifest.json"
                      and str(p.relative_to(delivery)) not in manifest)
    handoff = read(delivery / "handoff.json")
    config = read(delivery / "evidence" / "run-config.json")
    patch = next((delivery / name for name in ("change.patch", "unaccepted.patch")
                  if (delivery / name).is_file()), None)
    result = {"delivery": str(delivery), "outcome_recorded": handoff.get("outcome"),
              "baseline": handoff.get("baseline"), "manifest_altered": altered,
              "manifest_unlisted": unlisted,
              "patch": {"path": str(patch) if patch else None,
                        "sha256": digest(patch) if patch else None}}
    result["accounting"] = _recompute_accounting(delivery)
    into.mkdir(parents=True)
    if altered or patch is None:
        result["applied"] = False
        result["verified"] = False
        result["why"] = ("the delivery no longer matches its manifest" if altered else
                         "the delivery holds no patch")
        atomic_json(into / "verification.json", result)
        return result
    source = Path(args.repo).resolve() if args.repo else Path(config["paths"]["project"])
    checkout = into / "checkout"
    clone = subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout",
                            str(source), str(checkout)], capture_output=True, text=True)
    steps = [clone]
    if clone.returncode == 0:
        steps.append(subprocess.run(["git", "-C", str(checkout), "checkout", "--quiet",
                                     "--detach", handoff["baseline"]],
                                    capture_output=True, text=True))
    if all(step.returncode == 0 for step in steps):
        steps.append(subprocess.run(["git", "-C", str(checkout), "apply", "--binary",
                                     str(patch)], capture_output=True, text=True))
    applied = all(step.returncode == 0 for step in steps)
    result.update(repository=str(source), checkout=str(checkout), applied=applied,
                  apply_error=None if applied else (steps[-1].stderr or steps[-1].stdout)[-2000:])
    result["project_check"] = {"passed": None, "note": "not run: the patch did not apply"}
    env = None
    toolchain = config.get("toolchain")
    if applied and toolchain:
        # The run's toolchain was a copy; verification uses its source, and only if the source
        # still holds the same bytes. The fresh checkout is prepared the way the run was.
        import _toolchain
        if not _toolchain.source_matches(toolchain):
            applied = False
            result["project_check"] = {"passed": None, "note": f"not run: {toolchain['resolved']} no "
                                       "longer holds the toolchain bytes the run prepared"}
        else:
            env = {"PATH": str(Path(toolchain["resolved"]) / "bin") + os.pathsep + os.environ.get("PATH", "")}
            prepared = _bounded(toolchain["dependencies"]["prepare_command"], checkout,
                                CHECK_TIMEOUT_SECONDS, env=env)
            now = _toolchain.dependencies(checkout)
            result["dependencies"] = {
                "command": toolchain["dependencies"]["prepare_command"], "returncode": prepared["returncode"],
                "lockfile_matches_prepared": now["lockfile"]["sha256"] == toolchain["dependencies"]["lockfile"]["sha256"],
                "node_modules_digest": now["node_modules"]["digest"],
                "note": "installed files can embed their install location (native build configuration), so "
                        "node_modules digests are compared within a run, not across locations; the lockfile is "
                        "the comparable identity"}
    if applied:
        result["project_check"] = _bounded(shlex.split(config["check_command"]), checkout,
                                           config.get("check_timeout_seconds",
                                                      CHECK_TIMEOUT_SECONDS), env=env)
        result["project_check"]["command"] = config["check_command"]
        if args.outcome_check:
            argv = [part.replace("{checkout}", str(checkout))
                    for part in shlex.split(args.outcome_check)]
            result["outcome_check"] = {**_bounded(argv, into, CHECK_TIMEOUT_SECONDS, env=env),
                                       "command": args.outcome_check}
    result["verified"] = bool(applied and result["project_check"]["passed"]
                              and (result.get("dependencies") or {"returncode": 0})["returncode"] == 0
                              and (result.get("outcome_check") or {"passed": True})["passed"])
    atomic_json(into / "verification.json", result)
    return result


def _recompute_accounting(delivery):
    """Usage totals and derived cost re-derived from the delivery's retained per-call rows.

    Compared with the figures `finish` recorded. A disagreement is reported, never repaired; a
    delivery that predates a recorded billing basis says so rather than being priced by guess.
    """
    from _usage_events import usage_from_rows
    import _worker_pricing
    try:
        usage = read(delivery / "usage.json")
        events = read(delivery / "usage-events.json")
    except (OSError, ValueError) as exc:
        return {"available": False, "why": f"retained accounting unreadable: {exc}"}
    rows = events.get("rows") or []
    recorded = usage.get("usage") or {}
    recomputed = usage_from_rows(rows)
    keys = ("calls_started", "calls_finished", "input", "output", "reasoning", "cache_read",
            "cache_write")
    out = {"available": True, "rows": len(rows), "anomalies": len(events.get("anomalies") or []),
           "usage_recomputes": (all(recomputed.get(k) == recorded.get(k) for k in keys)
                                if recorded else None),
           "complete_as_recorded": usage.get("complete"), "derived_recorded": usage.get("derived")}
    billing = usage.get("billing") or {}
    table = _worker_pricing.TABLES.get(billing.get("table"))
    if billing.get("basis") != profiles.PRICED or table is None:
        out["derived_recomputes"] = None
        out["why"] = ("no external API billing: no price to recompute"
                      if billing.get("basis") == profiles.NO_EXTERNAL_BILLING else
                      "the delivery records no billing basis to recompute against")
        return out
    priced = _worker_pricing.cost_rows(rows, model=billing["price_model"], table=table)
    amount = priced.get("amount")
    out["derived_recomputed"] = round(amount, 6) if isinstance(amount, (int, float)) else None
    out["derived_recomputes"] = (None if out["derived_recorded"] is None
                                 or out["derived_recomputed"] is None
                                 else abs(out["derived_recomputed"] - out["derived_recorded"])
                                 < 1e-6)
    out["table"] = table["id"]
    out["claim"] = "derived from retained usage at a dated table; not provider-confirmed billing"
    return out


def _bounded(argv, cwd, timeout, env=None):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(env or {})}
    try:
        cp = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                            env=env)
    except subprocess.TimeoutExpired:
        return {"returncode": None, "passed": None,
                "note": f"did not finish within {timeout}s; unknown, not failed"}
    return {"returncode": cp.returncode, "passed": cp.returncode == 0,
            "stdout": cp.stdout[-4000:], "stderr": cp.stderr[-4000:]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor"); d.add_argument("--executor", type=Path, default=EXECUTOR)
    d.add_argument("--worker-profile", default=profiles.DEFAULT_PROFILE,
                   help="built-in profile name or path to a profile file")
    pr = sub.add_parser("profile", help="resolve and show a worker profile; no provider call")
    pr_sel = pr.add_mutually_exclusive_group()
    pr_sel.add_argument("--worker-profile", default=profiles.DEFAULT_PROFILE)
    pr_sel.add_argument("--template", action="store_true",
                        help="print a local OpenAI-compatible profile template")
    st = sub.add_parser("start"); st.add_argument("--project", type=Path, required=True); st.add_argument("--change", default="CH-001")
    group = st.add_mutually_exclusive_group(required=True); group.add_argument("--goal"); group.add_argument("--goal-file", type=Path)
    st.add_argument("--check", required=True, help="project check argv, shell-quoted; no shell operators")
    st.add_argument("--executor", type=Path, default=EXECUTOR)
    st.add_argument("--worker-profile", default=profiles.DEFAULT_PROFILE,
                    help="built-in profile name or path to a profile file; fixed for the run")
    st.add_argument("--deadline-seconds", type=int, default=900,
                    help="per-attempt worker deadline; fixed for the run")
    st.add_argument("--toolchain", type=Path, default=None,
                    help="a Node distribution the project's checks need, copied into the run and "
                         "run inside the worker boundary; install the project's dependencies with "
                         "its npm first. Optional; fixed for the run")
    vd = sub.add_parser("verify-delivery", help="apply a sealed delivery to a fresh checkout of "
                        "its baseline and rerun the checks; touches neither project nor run")
    vd.add_argument("--delivery", type=Path, required=True)
    vd.add_argument("--into", type=Path, required=True, help="a new directory for the checkout")
    vd.add_argument("--repo", type=Path, help="a repository holding the baseline commit "
                    "(default: the project the run recorded)")
    vd.add_argument("--outcome-check", help="an extra check argv; {checkout} is replaced")
    co = sub.add_parser("coordinator"); co.add_argument("--run", type=Path, required=True)
    co.add_argument("--requested", required=True, help="the coordinator configuration you selected")
    co.add_argument("--self-reported", default=None, help="what the coordinating agent says it is")
    co.add_argument("--observed", default=None, help="runtime metadata the host actually exposes")
    rc = sub.add_parser("recover", help="diagnose an interrupted launch from retained evidence; with "
                        "--apply, resume its supervision or classify it. Never launches or accepts")
    rc.add_argument("--run", type=Path, required=True)
    rc.add_argument("--apply", action="store_true", help="make the one change the diagnosis names")
    for name in ("status", "continue", "admit", "decide", "finish", "revise", "resolve-owner", "authorize-spending", "authorize-resources"):
        p = sub.add_parser(name); p.add_argument("--run", type=Path, required=True)
        if name == "decide":
            p.add_argument("--decision", choices=["accept", "repair", "owner"], required=True); p.add_argument("--reason", required=True)
        if name == "resolve-owner": p.add_argument("--owner-response", required=True)
        if name == "revise": p.add_argument("--reason", required=True)
        if name == "finish":
            p.add_argument("--outcome", choices=["accepted", "blocked"], default="accepted")
            p.add_argument("--into", type=Path, help="new delivery directory; never overwrites an existing or interrupted seal")
            p.add_argument("--report", type=Path, required=True); p.add_argument("--report-source", choices=["direct", "relayed"], default="direct")
        if name == "authorize-spending":
            p.add_argument("--aggregate-limit", type=float, required=True); p.add_argument("--reserve", type=float, required=True)
            p.add_argument("--launch-ceiling", type=int, required=True); p.add_argument("--owner-authorization", required=True)
        if name == "authorize-resources":
            p.add_argument("--launch-ceiling", type=int, required=True); p.add_argument("--owner-authorization", required=True)
    args = ap.parse_args()
    try:
        if args.command == "doctor": result = doctor(args)
        elif args.command == "profile": result = show_profile(args)
        elif args.command == "verify-delivery": result = verify_delivery(args)
        elif args.command == "start": result = start(args)
        elif args.command == "coordinator": result = coordinator(args)
        elif args.command == "status": result = status(args.run.resolve())
        elif args.command == "continue": result = continue_run(args.run.resolve())
        elif args.command == "recover":
            import _supervision
            run = args.run.resolve(); config_for(run)
            result = _supervision.recover(run, apply=args.apply)
        elif args.command == "admit":
            run = args.run.resolve(); c = config_for(run)
            path = contract(c, "implementation")
            result = helper("pb_execution.py", "admit", *task_args(run, "build", "implementation"), "--contract", path, *authority_args(c))
        elif args.command == "decide": result = decide(args)
        elif args.command == "resolve-owner":
            run = args.run.resolve(); current = status(run)
            if not current.get("request_receipt"): raise ValueError("no pending owner decision")
            if not args.owner_response.strip(): raise ValueError("record the actual owner response; never infer one")
            receipt(run, "owner decision resolution", {"response": args.owner_response, "reported_not_proven": True}, request_receipt=current["request_receipt"])
            result = status(run)
        elif args.command == "revise":
            run = args.run.resolve(); c = config_for(run)
            state = read(run / "state.json")
            if status(run).get("owner_request"): raise ValueError("resolve the pending owner decision before revising")
            if state["phases"]["build"]["tasks"].get("implementation", {}).get("admission"):
                raise ValueError("implementation already admitted; continue its fixed authority, use a separate change for new intent")
            task = state["phases"]["design"]["tasks"].get("requirements", {})
            if not args.reason.strip(): raise ValueError("give the within-goal revision and contradiction witness")
            revision = int(task.get("current_contract", {}).get("revision", 0)) + 1
            path = contract(c, "requirements", revision=revision, instruction=args.reason)
            result = helper("dsd_state.py", "bind-contract", *task_args(run, "design", "requirements"), "--contract", path)
            receipt(run, "requirements revision", {"reason": args.reason, "contract": str(path)})
        elif args.command == "finish": result = finish(args)
        elif args.command == "authorize-resources": result = authorize_resources(args)
        else:
            result = authorize_spending(args)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"error": str(exc), "action": "blocked", "evidence_retained": True}, indent=2)); return 2


def authorize_spending(args):
    import math
    run = args.run.resolve(); c = config_for(run)
    settings = profiles.of(c)
    if settings["billing"]["basis"] != profiles.PRICED:
        raise ValueError("this run's worker profile has no external API billing, so a money limit "
                         "would bound nothing; use authorize-resources")
    if not all(math.isfinite(v) for v in [args.aggregate_limit, args.reserve]) or not 0 < args.reserve < args.aggregate_limit or args.launch_ceiling < 1:
        raise ValueError("require finite 0 < reserve < aggregate limit and positive launch ceiling")
    if (run / "launch-ledger.json").exists(): raise ValueError("resource policy is frozen after first launch intent; no automatic new trajectory")
    if not args.owner_authorization.strip(): raise ValueError("explicit owner authorization required")
    ready = readiness(settings, Path(c["executor"]["path"]))
    if not ready["ready"]: raise ValueError("readiness problems: " + "; ".join(ready["problems"]))
    from _workflow_boundary import prepare
    c = prepare(c)
    c["policy"].update(aggregate_limit=args.aggregate_limit, reserve=args.reserve, launch_ceiling=args.launch_ceiling)
    atomic_json(run / "run-config.json", c)
    receipt(run, "owner spending authorization", {"authority": args.owner_authorization, "policy": c["policy"], "billing_cap": False})
    return {"configured": True, "policy": c["policy"], "next": command(run, "continue")}


def authorize_resources(args):
    """Launch authority for a worker with no external API bill: attempts, not money.

    What is bounded is stated as enforced or merely configured, from the recorded settings. A money
    limit is not accepted here because it would bound nothing; unknown local compute cost is not
    thereby zero, and an unresolved attempt still blocks every further launch.
    """
    run = args.run.resolve(); c = config_for(run)
    settings = profiles.of(c)
    if settings["billing"]["basis"] != profiles.NO_EXTERNAL_BILLING:
        raise ValueError("this run's worker is billed by a provider; use authorize-spending")
    if args.launch_ceiling < 1: raise ValueError("require a positive launch ceiling")
    if (run / "launch-ledger.json").exists(): raise ValueError("resource policy is frozen after first launch intent; no automatic new trajectory")
    if not args.owner_authorization.strip(): raise ValueError("explicit owner authorization required")
    ready = readiness(settings, Path(c["executor"]["path"]))
    if not ready["ready"]: raise ValueError("readiness problems: " + "; ".join(ready["problems"]))
    from _workflow_boundary import prepare
    c = prepare(c)
    c["policy"].update(aggregate_limit=0, reserve=0, launch_ceiling=args.launch_ceiling)
    atomic_json(run / "run-config.json", c)
    bounded = {"launch_ceiling": args.launch_ceiling,
               "repair_cycles": c["policy"].get("repair_cycles", 1),
               "attempt_deadline_seconds": c["deadline"]["seconds"],
               "output_token_allowance": settings["resources"]["output_token_allowance"],
               "per_call_output_tokens": settings["limits"]["output"],
               "context_tokens": settings["limits"]["context"]}
    receipt(run, "owner resource authorization", {
        "authority": args.owner_authorization, "bounded": bounded,
        "enforced": settings["resources"]["enforced"],
        "configured_not_enforced": settings["resources"]["configured"],
        "billing": settings["billing"], "network": settings["network"]})
    return {"configured": True, "policy": c["policy"], "bounded": bounded,
            "enforced": settings["resources"]["enforced"],
            "configured_not_enforced": settings["resources"]["configured"],
            "next": command(run, "continue")}


def show_profile(args):
    """Resolve a profile and print its settings, or print the local template. Touches nothing."""
    if args.template:
        # Printed bare so `profile --template > local.json` is the file to edit. It does not
        # resolve until its placeholder model is replaced: nothing is inferred from a name.
        return profiles.LOCAL_TEMPLATE
    settings = profiles.resolve(args.worker_profile)
    return {"settings": settings, "digest": settings["digest"],
            "note": "a run keeps these resolved settings; later edits to a profile file do not "
                    "reach a started run"}


if __name__ == "__main__":
    raise SystemExit(main())
