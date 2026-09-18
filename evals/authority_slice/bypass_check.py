#!/usr/bin/env python3
"""Attempt to launch candidate-bound execution that the authorization guard has refused.

Run this at any revision of the repository it lives in. Before the admission repair it reproduces
the bypass; at or after the repair every route must refuse and the executor must never be reached.

    python3 evals/authority_slice/bypass_check.py                  # expect every route refused
    python3 evals/authority_slice/bypass_check.py --expect-bypass  # expect the bypass (pre-repair)

The fixture is one minimal mutation of a fully prepared, internally consistent state: its durable
consistency acceptance is deleted and nothing else. The candidate stays derivable, so only the guard
can detect the problem — the same mutation `pb-handoff-1`'s control condition used.

Three routes are attempted, because closing the first two would leave the defect intact:

1. `pb_execution.py admit` — the supported transition;
2. `dsd_state.py bind-contract` — what the pre-repair flow called;
3. a hand-written state entry followed by a launch — what a coordinator with file access can do,
   and the route that decides whether the boundary is enforcement or decoration.

**Whether a worker ran is established from the run tree, never from an exit code.** The defect's
shape is that the launcher *succeeds*: it returned 0 on a launch that should never have happened, so
an exit code is exactly the wrong evidence. The executor is the slice's local fake and reaches no
provider; this costs nothing and needs no credential.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import _live                                                          # noqa: E402


def executor_reached(config: dict) -> dict:
    """Did a worker actually run? Answered from what the launcher leaves behind."""
    event = Path(config["paths"]["run_root"]) / "attempts" / "implementer-1"
    return {
        "attempt_directory": event.is_dir(),
        "launch_reservation": (event / "launch-reservation.json").is_file(),
        "terminal_record": (event / "terminal.json").is_file(),
        "worker_report": (event / "report.md").is_file(),
        "project_mutated": (Path(config["paths"]["project"]) / "dispatch.py").is_file(),
    }


def payload_of(done: subprocess.CompletedProcess) -> dict:
    return json.loads(done.stdout) if done.stdout.strip().startswith("{") else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-bypass", action="store_true",
                    help="pass when the bypass reproduces (use at a pre-repair revision)")
    ap.add_argument("--keep", type=Path, default=None, help="where to build the fixture")
    args = ap.parse_args()

    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                              capture_output=True).stdout.strip()
    work = args.keep or Path(tempfile.mkdtemp(prefix="pb-bypass-"))
    shutil.rmtree(work, ignore_errors=True)
    prepared = _live.prepare(work, mode=_live.REHEARSAL)
    config = _live.load_config(prepared["workdir"])
    run_root = Path(config["paths"]["run_root"])
    candidate = prepared["candidate"]

    removed = sorted(p.name for p in Path(config["paths"]["consistency"]).glob("*.json"))
    for record in Path(config["paths"]["consistency"]).glob("*.json"):
        record.unlink()

    contract = _live.place_contract(config, "RQ-impl", candidate)
    guard = _live.sh([sys.executable, str(ROOT / "scripts" / "pb_execution.py"), "authorize",
                      "--graph", config["paths"]["graph"], "--ledger", config["paths"]["ledger"],
                      "--project-root", config["paths"]["project"],
                      "--consistency", config["paths"]["consistency"],
                      "--run-root", run_root, "--contract", contract])
    refusal = payload_of(guard)

    routes: dict = {}

    admit = _live.sh([sys.executable, str(ROOT / "scripts" / "pb_execution.py"), "admit",
                      "--run-root", run_root, "--phase-id", "build", "--task-id", "RQ-impl",
                      "--contract", contract, "--graph", config["paths"]["graph"],
                      "--ledger", config["paths"]["ledger"],
                      "--project-root", config["paths"]["project"],
                      "--consistency", config["paths"]["consistency"]])
    admitted = payload_of(admit)
    routes["admit"] = {"returncode": admit.returncode, "admitted": admitted.get("admitted"),
                       "findings": [f.get("code") for f in admitted.get("findings", [])],
                       "available": "invalid choice" not in admit.stderr}

    bind = _live.sh([sys.executable, str(ROOT / "scripts" / "dsd_state.py"), "bind-contract",
                     "--run-root", run_root, "--phase-id", "build", "--task-id", "RQ-impl",
                     "--contract", contract])
    routes["bind_contract"] = {"returncode": bind.returncode,
                               "refusal": bind.stderr.strip().splitlines()[:1]}

    # Route 3 — write the task's state entry exactly as a bound task looks, then launch. This asks
    # whether the launch trusts the contract in front of it or checks that the transition happened.
    state_path = run_root / "state.json"
    state = json.loads(state_path.read_text())
    state["phases"].setdefault("build", {"status": "in-progress", "tasks": {}})
    state["phases"]["build"]["tasks"]["RQ-impl"] = {
        "status": "prepared",
        "current_contract": {"revision": 1, "path": str(contract),
                             "sha256": hashlib.sha256(contract.read_bytes()).hexdigest()}}
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True))
    launched = _live.launch(work, phase="build", task="RQ-impl", role="implementer")
    routes["hand_bound_then_launch"] = {
        "launcher_returncode": launched.get("returncode"),
        "slot_classification": launched.get("slot", {}).get("classification"),
        "terminal_status": launched.get("status"),
        "refusal": (launched.get("stderr") or "").splitlines()[-1:],
    }

    reached = executor_reached(config)
    bypassed = any(reached.values())
    print(json.dumps({
        "revision": revision,
        "workdir": str(work),
        "executor": {"kind": config["executor"]["kind"], "provider_calls": 0},
        "fixture": {"candidate": candidate, "consistency_records_removed": removed},
        "guard": {"exit_code": guard.returncode, "authorized": refusal.get("authorized"),
                  "findings": [f.get("code") for f in refusal.get("findings", [])]},
        "routes": routes,
        "executor_reached": reached,
        "bypassed": bypassed,
    }, indent=2, sort_keys=True))
    return 0 if bypassed == args.expect_bypass else 1


if __name__ == "__main__":
    raise SystemExit(main())
