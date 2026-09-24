#!/usr/bin/env python3
"""Prepare one first-use run of the public CSV task. Launches nothing and spends nothing.

This is **not** the paired pilot. `protocol-v2.md` and `preparation-identities.json` freeze that
pilot against harness `aff0c75` and a Codex/GPT-6 coordinator; they are not read, copied or
changed here. A first-use run is a separately identified, single-arm usability observation under
whichever coordinator actually drives it and whichever instrument is checked out now. It reuses
the pilot's public goal and outcome check unchanged, and its result is diagnostic — not held-out
evidence, not a comparison.

    python3 examples/csv-summary/first_use.py prepare --into /private/tmp/csv-first-use-1 \\
        --coordinator claude-code/opus

`prepare` builds a fresh Git project from `project/`, copies `goal.md` and `check_outcome.py`
beside it (outside the project), records every identity the run will depend on, and prints the
commands a coordinator runs. The run itself starts with `pb_workflow.py start`, from the goal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import _worker_profiles as profiles                                  # noqa: E402

FORMAT = "proofbound-first-use-v1"
CHANGE = "FU-1"

#: Launches enumerated from the workflow's stages, as in the qualification suite: requirements
#: author and fresh challenge, consistency challenge, implementer and fresh reviewer (5); one
#: implementation repair and its fresh review (2); one requirements revision with its fresh
#: challenge and renewed consistency review (3); one pre-executor allowance (1).
LAUNCHES = {"minimum": 5, "ceiling": 11}


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(into: Path, *, coordinator: str, per_launch: float, executor: str) -> dict:
    into = into.resolve()
    into.mkdir(parents=True, exist_ok=False)
    project = into / "project"
    shutil.copytree(HERE / "project", project, ignore=shutil.ignore_patterns("__pycache__"))
    (project / ".gitignore").write_text("DeepSeekAndDestroy/\n__pycache__/\n")
    for args in (("init", "-q"), ("config", "user.name", "Proofbound first-use fixture"),
                 ("config", "user.email", "fixture@proofbound.invalid"), ("add", "."),
                 ("commit", "-qm", "CSV summary starting project")):
        subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)
    baseline = subprocess.check_output(["git", "-C", str(project), "rev-parse", "HEAD"],
                                       text=True).strip()
    for name in ("goal.md", "check_outcome.py"):
        shutil.copyfile(HERE / name, into / name)
    settings = profiles.resolve(profiles.DEFAULT_PROFILE)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                           text=True)
    python = sys.executable
    run = project / "DeepSeekAndDestroy" / "plans" / CHANGE / "runs" / "first"
    pb = ROOT / "scripts" / "pb_workflow.py"
    aggregate = round(LAUNCHES["ceiling"] * per_launch, 6)

    def cmd(*parts) -> str:
        return shlex.join([python, str(pb), *map(str, parts)])

    identity = {
        "format": FORMAT, "status": "prepared; NOT authorized; not run",
        "not_the_pilot": "separate from protocol-v2.md / preparation-identities.json, which "
                         "remain frozen and unrun; this run is diagnostic, not held out",
        "coordinator": {"requested": coordinator,
                        "note": "record the actual coordinator with `pb_workflow.py coordinator`"
                                " in the run; requested, self-reported and observed stay apart"},
        "harness": {"commit": head.stdout.strip() or None,
                    "clean": head.returncode == 0 and not dirty.stdout.strip()},
        "interpreter": {"version": platform.python_version(), "executable": python},
        "worker": {"profile": settings["profile"]["id"], "revision":
                   settings["profile"]["revision"], "settings_digest": settings["digest"],
                   "requested_model": settings["model"], "variant": settings["variant"],
                   "documented_serving": settings["provider"]["documented_serving"],
                   "executor": {"path": executor,
                                "sha256": sha(Path(executor)) if Path(executor).is_file()
                                else None,
                                "pinned": settings["executor"]["sha256"]}},
        "task": {"goal": {"path": str(into / "goal.md"), "sha256": sha(into / "goal.md")},
                 "outcome_check": {"path": str(into / "check_outcome.py"),
                                   "sha256": sha(into / "check_outcome.py")},
                 "starting_project": {"path": str(project), "baseline": baseline,
                                      "files": {str(p.relative_to(project)): sha(p)
                                                for p in sorted(project.rglob("*"))
                                                if p.is_file() and ".git" not in p.parts}}},
        "resources_proposed_not_authorized": {
            "launches": LAUNCHES, "per_launch_derived_allowance": per_launch,
            "aggregate_derived_limit": aggregate, "reserve": per_launch,
            "attempt_deadline_seconds": 900,
            "containment": settings["resources"]["attempt_containment"],
            "claim": "admission and containment over derived spend — measured usage priced at "
                     f"{settings['billing']['table']}; not a provider billing cap"},
        # Every participant that can cost money or effort, and who measures it. Proofbound meters
        # only the worker.
        "metered_participants": {
            "worker": "derived cost of measured usage at the dated table; admission- and "
                      "containment-limited by this run's authorization; not provider billing",
            "coordinator": "each coordinator session, including any fresh-session handoff, is "
                           "metered by its own host and valued there (for example a headless "
                           "session's list-price figure); it needs its own authorization and is "
                           "never covered by the worker allowance",
            "human": "owner and operator effort; unmeasured"},
        "stopping": ["a sealed delivery, accepted or blocked", "the launch ceiling or derived "
                     "limit", "unknown spend or an unresolved attempt", "a second failed repair",
                     "an owner decision the goal cannot settle"],
        "commands": {
            "readiness": cmd("doctor", "--executor", executor),
            "start": cmd("start", "--project", project, "--change", CHANGE, "--goal-file",
                         into / "goal.md", "--check", f"{python} -m unittest discover",
                         "--executor", executor),
            "record_coordinator": cmd("coordinator", "--run", run, "--requested", coordinator,
                                      "--self-reported", "<what the coordinating agent says>"),
            "authorize": cmd("authorize-spending", "--run", run, "--aggregate-limit", aggregate,
                             "--reserve", per_launch, "--launch-ceiling", LAUNCHES["ceiling"],
                             "--owner-authorization", "<the owner's actual statement>"),
            "drive": [cmd("status", "--run", run), cmd("continue", "--run", run),
                      cmd("decide", "--run", run, "--decision", "accept|repair|owner",
                          "--reason", "<adjudication>")],
            "finish": cmd("finish", "--run", run, "--report", "<coordinator report.md>"),
            "verify": cmd("verify-delivery", "--delivery", run / "delivery", "--into",
                          into / "fresh-verification", "--outcome-check",
                          f"{python} {into / 'check_outcome.py'} {{checkout}}"),
        },
    }
    (into / "first-use-identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    return {"prepared": str(into), "baseline": baseline, "launched": 0,
            "identity": str(into / "first-use-identity.json"),
            "authorization": "none; nothing was started or spent"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--into", type=Path, required=True)
    p.add_argument("--coordinator", required=True, help="the coordinator that will drive it")
    p.add_argument("--per-launch-allowance", type=float, default=0.05)
    p.add_argument("--executor", default=str(Path.home() / ".proofbound/executors/"
                                             "opencode-1.18.29-darwin-arm64/opencode"))
    args = ap.parse_args()
    print(json.dumps(prepare(args.into, coordinator=args.coordinator,
                             per_launch=args.per_launch_allowance,
                             executor=args.executor), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
