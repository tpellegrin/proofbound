#!/usr/bin/env python3
"""Run Proofbound's Eval V1 suite.

    WARNING: `run` invokes a real model through the configured worker harness, once per
    trial plus once per semantic grade. A full suite is tens of provider calls. Nothing
    here is part of the deterministic test suite, and running the deterministic suite never
    reaches this file.

Measures one claim: a fresh spec-reflector, given an artifact it did not author, detects a
planted engineering contradiction. Every trial drives the real Proofbound pipeline — there
is no eval-only model client, because an evaluation that bypassed orchestration would
measure something Proofbound does not ship.

    list      show the scenarios and their identities
    run       execute the suite and write a summary
    show      render a recorded summary
    compare   read two recorded runs and report what differs between them
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))

from _compare import ComparisonError, compare  # noqa: E402
from _compare import render as render_comparison  # noqa: E402
from _grade import mechanical, semantic  # noqa: E402
from _scenario import ScenarioError, discover  # noqa: E402
from _summary import SummaryError, load, render, summarize  # noqa: E402
from _trial import NO_TREATMENT, harness_version, provider_available, run_trial  # noqa: E402

DEFAULT_MODEL = "opencode-go/deepseek-v4-flash"
# Inherited DSD's default worker model, so `run` with no flags measures the shipped
# configuration. It is deliberately NOT a claim that the model exists in any given
# environment: `--model` is how a run states what it actually tested.
#
# The default grader is the same model, which means the system under test judges itself
# unless `--grader-model` names a different one. That is procedural independence only —
# separate invocation, blind to version and prior scores — and a run must record which
# kind of independence it actually had.
DEFAULT_GRADER = DEFAULT_MODEL

# The P12 control's one variable. `none` is current production behaviour, stated explicitly
# rather than left absent, because a record that says nothing is a different fact from a record
# that says "no author report was supplied".
NO_TREATMENT_ARM = NO_TREATMENT
AUTHOR_REPORT_TREATMENT = "author-report"


def _system(model: str, grader_model: str) -> dict:
    sha = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=False).stdout.strip()
    return {"proofbound_sha": sha or None, "harness": "opencode-cli",
            # Identity says which harness; version says which release of it. Absent means
            # unknown, in this record and in every older one.
            "harness_version": harness_version(), "model": model,
            "grader_model": grader_model, "role": "spec-reflector",
            "python": f"{sys.version_info.major}.{sys.version_info.minor}"}


def cmd_list(args: argparse.Namespace) -> int:
    for scenario in discover(args.scenarios):
        print(f"{scenario['id']:<28} {scenario['kind']:<11} {scenario['identity'][:12]}"
              f"  {scenario['summary']}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    scenarios = discover(args.scenarios)
    if args.only:
        scenarios = [s for s in scenarios if s["id"] in set(args.only)]
        if not scenarios:
            print("ERROR: no scenario matched --only", file=sys.stderr)
            return 2
    ok, detail = provider_available()
    if not ok:
        # Explicit setup failure, never a semantic result and never a fabricated baseline.
        print(f"ERROR: cannot run trials: {detail}", file=sys.stderr)
        return 2
    print(f"worker executable: {detail}\n"
          f"about to run {len(scenarios)} scenario(s) x {args.trials} trial(s) "
          f"against {args.model} with treatment {args.treatment!r}; "
          "this spends provider resources.\n")

    treated = args.treatment == AUTHOR_REPORT_TREATMENT
    if treated:
        missing = [s["id"] for s in scenarios if not s.get("author_report")]
        if missing:
            # Silently running an untreated trial in the treated arm would destroy the
            # experiment while looking like it worked.
            print(f"ERROR: no author report for: {', '.join(missing)}", file=sys.stderr)
            return 2

    results = []
    for scenario in scenarios:
        graded = []
        for n in range(args.trials):
            trial = run_trial(scenario, model=args.model, keep=args.evidence,
                              treatment=scenario["author_report"] if treated else None)
            entry = {"trial": trial, "mechanical": {"ok": False, "findings": ["not evaluated"]},
                     "semantic": {"result": "grading-unavailable", "reason": "trial not valid"}}
            if trial["validity"] == "valid":
                entry["mechanical"] = mechanical(trial)
                entry["semantic"] = semantic(trial, scenario, grader_model=args.grader_model)
            graded.append(entry)
            # Calibration material: everything a human needs to check the grader's call, in
            # one local file. Kept out of the committed summary because it holds the planted
            # property and the full report.
            if args.evidence and trial.get("evidence"):
                (Path(trial["evidence"]) / "calibration.json").write_text(json.dumps({
                    "scenario": scenario["id"],
                    # Every planted obligation, so a human can check each grader call against
                    # the statement it was actually judging.
                    "properties": [{"id": p["id"], "dimension": p.get("dimension"),
                                    "statement": p["statement"]}
                                   for p in scenario["properties"]],
                    "report": trial.get("report", ""),
                    "author_report_sha256": trial.get("author_report_sha256"),
                    "grader": entry["semantic"]}, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
            print(f"  {scenario['id']} trial {n + 1}/{args.trials}: "
                  f"{trial['validity']} / {entry['semantic']['result']}")
        results.append({"scenario": scenario, "graded": graded})

    summary = summarize(results, system=_system(args.model, args.grader_model))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("\n" + render(summary))
    print(f"\nsummary written: {args.out}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    print(render(load(args.summary)))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Report what differs between two recorded runs. Nothing is written.

    A comparison is derived from the summaries it names, so it is printed rather than stored:
    a persisted copy would be a second place for the same facts to live, and eventually to
    disagree.
    """
    print(render_comparison(compare(load(args.a), load(args.b),
                                    label_a=args.a.stem, label_b=args.b.stem)))
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scenarios", type=Path, default=HERE / "scenarios")
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show scenarios and identities").set_defaults(handler=cmd_list)

    r = sub.add_parser("run", help="execute the suite (SPENDS PROVIDER RESOURCES)")
    r.add_argument("--model", default=DEFAULT_MODEL)
    r.add_argument("--grader-model", default=DEFAULT_GRADER)
    r.add_argument("--trials", type=int, default=5)
    r.add_argument("--treatment", choices=[NO_TREATMENT_ARM, AUTHOR_REPORT_TREATMENT],
                   default=NO_TREATMENT_ARM,
                   help="supply each scenario's author report to the reflector (P12 control)")
    r.add_argument("--only", action="append", help="restrict to named scenarios; repeatable")
    r.add_argument("--out", type=Path, default=HERE / "results" / "eval-v1.json")
    r.add_argument("--evidence", type=Path, default=None,
                   help="local directory for raw trial evidence; never commit it")
    r.set_defaults(handler=cmd_run)

    s = sub.add_parser("show", help="render a recorded summary")
    s.add_argument("summary", type=Path)
    s.set_defaults(handler=cmd_show)

    c = sub.add_parser("compare", help="report what differs between two recorded runs")
    c.add_argument("a", type=Path)
    c.add_argument("b", type=Path)
    c.set_defaults(handler=cmd_compare)
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        return args.handler(args)
    except (ComparisonError, ScenarioError, SummaryError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
