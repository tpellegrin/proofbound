#!/usr/bin/env python3
"""Run the system-craft calibration.

    WARNING: `run` invokes real models — one implementation trial, one craft reflection and one
    grading call per trial. Nothing here is part of the deterministic suite.

    validate   check behavioural equivalence and blindness without any model call
    run        execute the calibration matrix and write a summary
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))

import _craft  # noqa: E402
from _trial import VALID, harness_version, provider_available, run_trial  # noqa: E402

CASES = HERE / "craft"


def _run_suite(project: Path, test_file: Path) -> dict:
    """Run one test file inside a built project, without leaving caches behind."""
    target = project / test_file.name
    target.write_bytes(test_file.read_bytes())
    cp = subprocess.run([sys.executable, "-B", "-m", "unittest", test_file.stem, "-q"],
                        cwd=project, capture_output=True, text=True, check=False)
    target.unlink(missing_ok=True)
    return {"ok": cp.returncode == 0, "output": (cp.stdout + cp.stderr)[-600:]}


def cmd_validate(args: argparse.Namespace) -> int:
    """Prove the case is a usable control before a single model call is spent."""
    case = _craft.load(args.case)
    print(f"case {case['id']}  property {case['property']['id']}")
    failures = []

    # 1. Behavioural equivalence: one suite, every state, identical expectations.
    import shutil, tempfile
    for state in case["states"]:
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "p"
            shutil.copytree(state["fixture"], project,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            got = _run_suite(project, Path(case["behaviour_test"]))
            before = _run_suite(project, Path(case["future_test"]))
        status = "OK" if got["ok"] else "FAILED"
        print(f"  {state['id']:<10} baseline behaviour {status}"
              f"   future capability absent {'OK' if not before['ok'] else 'ALREADY PRESENT'}")
        if not got["ok"]:
            failures.append(f"{state['id']} does not exhibit the accepted behaviour")
        if before["ok"]:
            failures.append(f"{state['id']} already satisfies the future change")

    # 2. Nothing worker- or evaluator-visible may carry a label or the answer.
    visible = [Path(case["intent"]), Path(case["contract"]), Path(case["behaviour_test"])]
    for state in case["states"]:
        visible += _craft._fixture_files(Path(state["fixture"]))
    for path in visible:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for token in _craft.FORBIDDEN_IN_PROMPTS:
            if token in text:
                failures.append(f"{path.name} leaks {token!r}")
    print(f"  worker-visible material checked: {len(visible)} files")

    # 3. The declared property must not be quoted at the worker or the reflector.
    words = re.findall(r"[a-z]{4,}", case["property"]["scenario"].lower())
    needles = {" ".join(words[i:i + 6]) for i in range(len(words) - 5)}
    for path in visible:
        flat = " ".join(re.findall(r"[a-z]{4,}",
                                   path.read_text(encoding="utf-8", errors="ignore").lower()))
        if any(n in flat for n in needles):
            failures.append(f"{path.name} restates the calibration property")

    for problem in failures:
        print(f"  FAILURE: {problem}")
    print("  OK: usable as a calibration control" if not failures
          else f"  {len(failures)} problem(s)")
    return 1 if failures else 0


def cmd_run(args: argparse.Namespace) -> int:
    case = _craft.load(args.case)
    ok, detail = provider_available()
    if not ok:
        print(f"ERROR: cannot run trials: {detail}", file=sys.stderr)
        return 2
    order = [s.strip() for s in args.order.split(",")] if args.order else \
            [s["id"] for s in case["states"]] * args.trials
    by_id = {s["id"]: s for s in case["states"]}
    unknown = sorted(set(order) - set(by_id))
    if unknown:
        print(f"ERROR: unknown state(s) in order: {', '.join(unknown)}", file=sys.stderr)
        return 2

    intent = Path(case["intent"]).read_text(encoding="utf-8")
    contract = Path(case["contract"]).read_text(encoding="utf-8")
    results = []
    for n, sid in enumerate(order, 1):
        state = by_id[sid]
        trial = run_trial(state, model=args.model, role="implementer", keep=args.evidence)
        entry = {"state": sid, "state_identity": state["identity"], "trial": n,
                 "validity": trial["validity"], "reason": trial.get("reason")}
        if trial["validity"] == VALID and trial.get("evidence"):
            project = Path(trial["evidence"]) / "project"
            entry["behaviour"] = _run_suite(project, Path(case["behaviour_test"]))["ok"]
            entry["future"] = _run_suite(project, Path(case["future_test"]))["ok"]
            entry["ce1"] = _craft.ce1_facts(trial)
            diff = subprocess.run(["git", "-C", str(project), "diff", "HEAD"],
                                  capture_output=True, text=True, check=False).stdout
            before = "\n".join(
                f"--- {p.relative_to(state['fixture'])}\n"
                f"{p.read_text(encoding='utf-8', errors='ignore')}"
                for p in sorted(_craft._fixture_files(Path(state["fixture"]))))
            # Correctness first: a failed implementation is not a craft observation.
            if entry["future"] and entry["behaviour"]:
                reflection = _craft.reflect(intent=intent, contract=contract, before=before,
                                            diff=diff[:20000], model=args.reflector_model)
                entry["reflection"] = reflection.get("report")
                if reflection.get("report"):
                    claim = _craft.classify_claim(reflection["report"],
                                                  case["property"]["scenario"],
                                                  model=args.grader_model)
                    entry["claim"] = claim["claim"]
                    entry["claim_reason"] = claim.get("reason", "")[:300]
                    entry["outcome"] = _craft.outcome(
                        case["ground_truth"][sid]["status"], claim["claim"])
        results.append(entry)
        print(f"  {n}/{len(order)} {sid}: {entry['validity']}"
              f" future={entry.get('future')} -> {entry.get('outcome', 'n/a')}", flush=True)

    summary = {
        "format": "proofbound-craft-calibration-v1",
        "case": case["id"], "property": case["property"],
        "system": {"proofbound_sha": subprocess.run(
                       ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                       capture_output=True, text=True, check=False).stdout.strip() or None,
                   "harness": "opencode-cli", "harness_version": harness_version(),
                   "model": args.model, "reflector_model": args.reflector_model,
                   "grader_model": args.grader_model, "role": "implementer",
                   "python": f"{sys.version_info.major}.{sys.version_info.minor}"},
        "order": order,
        "states": {s["id"]: {"identity": s["identity"],
                             "status": case["ground_truth"][s["id"]]["status"]}
                   for s in case["states"]},
        "trials": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nsummary written: {args.out}")
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="check the case without spending a model call")
    v.add_argument("case", type=Path)
    v.set_defaults(handler=cmd_validate)
    r = sub.add_parser("run", help="execute the calibration (SPENDS PROVIDER RESOURCES)")
    r.add_argument("case", type=Path)
    r.add_argument("--model", required=True, help="worker that implements the change")
    r.add_argument("--reflector-model", required=True)
    r.add_argument("--grader-model", required=True)
    r.add_argument("--trials", type=int, default=5)
    r.add_argument("--order", help="explicit comma-separated state order; overrides --trials")
    r.add_argument("--evidence", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.set_defaults(handler=cmd_run)
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        return args.handler(args)
    except (_craft.CraftCaseError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
