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

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
MODEL = "deepseek/deepseek-v4-flash"
EXECUTOR = Path.home() / ".proofbound/executors/opencode-1.18.29-darwin-arm64/opencode"
QUALIFIED_DIGEST = "2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669"
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
    exe = args.executor.expanduser().resolve()
    installed = exe.is_file() and os.access(exe, os.X_OK)
    supported = platform.system() == "Darwin" and platform.machine() == "arm64"
    version = None
    if installed:
        cp = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=15)
        version = cp.stdout.strip() if cp.returncode == 0 else None
    auth = Path.home() / ".local/share/opencode/auth.json"
    configured = False
    if auth.is_file():
        try:
            configured = "deepseek" in read(auth)  # never emit credential values
        except (ValueError, OSError):
            pass
    problems = []
    if not supported: problems.append("supported worker environment is macOS arm64 only")
    if sys.version_info < (3, 10): problems.append("Python >=3.10 required")
    if not installed: problems.append("pinned OpenCode executable is missing")
    if not configured: problems.append("DeepSeek credential is not configured; no provider request made")
    if not shutil.which("git"): problems.append("git is missing")
    if not Path("/usr/bin/sandbox-exec").exists(): problems.append("macOS sandbox-exec boundary unavailable")
    boundary_available = False
    if Path("/usr/bin/sandbox-exec").exists():
        cp = subprocess.run(["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)", "/usr/bin/true"], capture_output=True, timeout=10)
        boundary_available = cp.returncode == 0
        if not boundary_available: problems.append("sandbox-exec cannot start in this process environment; run outside the enclosing sandbox")
    qualified = installed and digest(exe) == QUALIFIED_DIGEST
    if installed and not qualified: problems.append("executor bytes are not the experimentally qualified build")
    return {"ready": not problems, "problems": problems,
            "python": {"path": sys.executable, "version": platform.python_version(), "supported": sys.version_info >= (3, 10)},
            "worker": {"backend": "opencode-cli", "path": str(exe), "installed": installed,
                       "configured": configured, "version": version, "model": MODEL, "variant": "high",
                       "experimentally_qualified_build": qualified,
                       "qualification_scope": "pb-handoff-2: one seeded-authority continuation, not goal-to-change"},
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
    run = project / "DeepSeekAndDestroy" / "plans" / args.change / "runs" / "first"
    authority = project / "specs" / args.change
    if run.exists():
        if (run / "run-config.json").is_file():
            config = read(run / "run-config.json")
            if Path(config["goal"]).read_text() == goal and config["paths"]["project"] == str(project):
                return {"initialized": False, "existing": True, "run": str(run), "next": command(run, "status")}
        raise ValueError(f"existing or incomplete run at {run}; inspect it; nothing overwritten")
    if authority.exists(): raise ValueError(f"authority directory exists: {authority}; choose another --change")
    cp = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if cp.returncode or Path(cp.stdout.strip()).resolve() != project:
        raise ValueError("supported project is a Git worktree root; initialize Git first")
    baseline = subprocess.check_output(["git", "-C", str(project), "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "-C", str(project), "status", "--porcelain"], text=True).strip():
        raise ValueError("start needs a clean project to retain a usable baseline patch; preserve pending work in a commit or separate worktree")
    if not authority.resolve().is_relative_to(project): raise ValueError("authority path escapes project through a symlink")
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
    exe = args.executor.expanduser().resolve()
    config = {"format": "proofbound-supervised-workflow-v1", "mode": "live", "goal": str(goal_path),
              "goal_sha256": digest(goal_path), "requirements": str(req), "baseline": baseline,
              "interpreter": {"executable": sys.executable, "version": platform.python_version()},
              "executor": {"path": str(exe), "sha256": digest(exe) if exe.is_file() else None},
              "model": MODEL, "variant": "high", "auto_flag": "--auto", "home": str(runtime / "home"),
              "deadline": {"seconds": 900}, "check_command": args.check,
              "policy": {"aggregate_limit": 0, "reserve": 0, "launch_ceiling": 0, "repair_cycles": 1},
              "paths": {"project": str(project), "run_root": str(run), "ledger": str(ledger),
                        "graph": str(graph), "freezes": str(authority / "freezes"),
                        "consistency": str(authority / "consistency"), "session_db": str(runtime / "session/worker.db")}}
    rules = helper("prepare_worker_rules.py", "--project-root", project, "--run-root", run,
                   "--plan", goal_path, "--model", MODEL,
                   "--rule", "Review requirements, code and checks before reading a producer summary; record what you saw.")
    atomic_json(run / "state.json", {"project_worktree": str(project), "run_root": str(run),
        "execution_status": "active", "next_action": "propose requirements; no acceptance has been earned",
        "worker_rules": rules, "worker_runtime": {"harness": "opencode-cli", "model": MODEL,
                                                  "opencode": {"run_db": config["paths"]["session_db"]}},
        "phases": {"design": {"status": "in-progress", "tasks": {}}, "build": {"status": "pending", "tasks": {}}}})
    atomic_json(run / "run-config.json", config)
    (run / "CONTINUE.md").write_text(f"# Continue Proofbound\n\nRead `{ROOT / 'docs/operator-guide.md'}`.\n\nRun `{command(run, 'status')}`.\n\nOwner goal: `{goal_path}`. Routine decisions within it are delegated; material goal changes, policy conflicts and spending need owner authority.\n")
    return {"initialized": True, "run": str(run), "accepted": False, "next": command(run, "status")}


def config_for(run):
    config = read(run / "run-config.json")
    if Path(config["paths"]["run_root"]).resolve() != run: raise ValueError("run identity mismatch")
    if digest(config["goal"]) != config["goal_sha256"]: raise ValueError("owner goal changed; new goal authority requires a new run")
    return config


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
    base = {"run": str(run), "project": c["paths"]["project"], "goal": c["goal"],
            "baseline": c["baseline"],
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
        return {**common, "action": "adjudicate", "evidence": str(event / "report.md"), "gate": str(gate),
                "decision": "Judge coverage, contradictions and findings against owner goal. Accept only adequate review and output; request repair for defects or owner decision for unresolved scope/policy.",
                "next": command(run, "decide", "--decision", "accept", "--reason", "<your adjudication>")}
    return {**base, "action": "finish", "next": command(run, "finish", "--report", "<coordinator-report.md>")}




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


def status(run):
    result = _status(run)
    if result["action"] == "launch":
        c = config_for(run)
        from _launch_budget import LaunchLedger
        policy = c["policy"]
        ledger = LaunchLedger(run / "launch-ledger.json", limit=policy["aggregate_limit"],
                              reserve=policy["reserve"], ceiling=policy["launch_ceiling"])
        verdict = ledger.admit(phase=result["phase"], task=result["task"], role=result["role"],
                               run_root=run, db=c["paths"]["session_db"])
        if not verdict["admit"]:
            return {**result, "action": "blocked", "blocked_action": "launch", "reason": verdict["why"],
                    "next": "Supply explicit owner spending authority if none exists; otherwise reconcile retained launch/usage evidence. Never automatically buy another trajectory.",
                    "accounting": verdict["spend"]}
    return result


def continue_run(run):
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


def check_project(run, c):
    cp = subprocess.run(shlex.split(c["check_command"]), cwd=c["paths"]["project"], capture_output=True, text=True)
    path = receipt(run, "project checks", {"command": c["check_command"], "returncode": cp.returncode,
                   "stdout": cp.stdout[-8000:], "stderr": cp.stderr[-8000:]})
    if cp.returncode: raise ValueError(f"project checks failed; evidence {path}; no acceptance")
    return path


def finish(args):
    run = args.run.resolve(); c = config_for(run)
    if args.outcome == "accepted" and status(run)["action"] != "finish": raise ValueError("all required tasks must be accepted before delivery")
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
    account = spend(run, c["paths"]["session_db"], limit=c["policy"]["aggregate_limit"], reserve=c["policy"]["reserve"])
    from _launch_budget import LaunchLedger
    ledger = LaunchLedger(run / "launch-ledger.json")
    if ledger.unresolved():
        account = {**account, "complete": False, "unknown_charges": True,
                   "unresolved_slots": [slot["slot"] for slot in ledger.unresolved()],
                   "claim": "unclassified launch intents; no inference of zero spend"}
    atomic_json(out / "usage.json", account)
    from _usage_events import events_from_db
    atomic_json(out / "usage-events.json", events_from_db(Path(c["paths"]["session_db"])))
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
                "run_retained_at": str(run), "runtime_retained_at": str(Path(c["home"]).parent),
                "limitation": "run-tree binding only; this package does not close L3/L4 durable implementation provenance"})
    atomic_json(out / "manifest.json", {str(p.relative_to(out)): digest(p) for p in out.rglob("*") if p.is_file()})
    return {"delivery": str(out), "outcome": args.outcome, "patch": str(out / patch_name), "retained_run": str(run), "cleanup": "explicit only; contains private project data"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor"); d.add_argument("--executor", type=Path, default=EXECUTOR)
    st = sub.add_parser("start"); st.add_argument("--project", type=Path, required=True); st.add_argument("--change", default="CH-001")
    group = st.add_mutually_exclusive_group(required=True); group.add_argument("--goal"); group.add_argument("--goal-file", type=Path)
    st.add_argument("--check", required=True, help="project check argv, shell-quoted; no shell operators")
    st.add_argument("--executor", type=Path, default=EXECUTOR)
    for name in ("status", "continue", "admit", "decide", "finish", "revise", "resolve-owner", "authorize-spending"):
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
    args = ap.parse_args()
    try:
        if args.command == "doctor": result = doctor(args)
        elif args.command == "start": result = start(args)
        elif args.command == "status": result = status(args.run.resolve())
        elif args.command == "continue": result = continue_run(args.run.resolve())
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
        else:
            result = authorize_spending(args)
        print(json.dumps(result, indent=2, sort_keys=True)); return 0
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"error": str(exc), "action": "blocked", "evidence_retained": True}, indent=2)); return 2


def authorize_spending(args):
    import math
    run = args.run.resolve(); c = config_for(run)
    if not all(math.isfinite(v) for v in [args.aggregate_limit, args.reserve]) or not 0 < args.reserve < args.aggregate_limit or args.launch_ceiling < 1:
        raise ValueError("require finite 0 < reserve < aggregate limit and positive launch ceiling")
    if (run / "launch-ledger.json").exists(): raise ValueError("resource policy is frozen after first launch intent; no automatic new trajectory")
    if not args.owner_authorization.strip(): raise ValueError("explicit owner authorization required")
    ready = doctor(argparse.Namespace(executor=Path(c["executor"]["path"])))
    if not ready["ready"]: raise ValueError("readiness problems: " + "; ".join(ready["problems"]))
    from _workflow_boundary import prepare
    c = prepare(c)
    c["policy"].update(aggregate_limit=args.aggregate_limit, reserve=args.reserve, launch_ceiling=args.launch_ceiling)
    atomic_json(run / "run-config.json", c)
    receipt(run, "owner spending authorization", {"authority": args.owner_authorization, "policy": c["policy"], "billing_cap": False})
    return {"configured": True, "policy": c["policy"], "next": command(run, "continue")}


if __name__ == "__main__":
    raise SystemExit(main())
