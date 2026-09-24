#!/usr/bin/env python3
"""Qualify a worker configuration through Proofbound's own path, and compare what was retained.

    suite                          describe the cases, their identities and what each establishes
    plan    --worker-profile P ... freeze a bounded plan (replay, live proposal, or live)
    authorize --proposal D --owner-authorization '…' --into D2
                                   the owner's own statement turns a proposal into a live plan
    replay  --plan D --into R      run a replay plan with stand-ins, through the production path
    prepare-live --plan D --into R start and authorize a live plan's runs; launches nothing
    grade   --live R               grade a live plan's runs after its coordinator has driven them
    inspect --result R             re-derive every grade from the retained copies; no model call
    compare A B                    what two results can and cannot support; derived, never stored

`replay` is unpaid: no provider, no credential. `prepare-live` makes no provider request either —
but a live plan's runs, once a coordinator drives them, **spend** under the plan's authorization.
Nothing here ranks configurations, names a winner or changes a default. Qualification is evidence
for a person, never permission.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _qualify                                                     # noqa: E402
import _compare                                                     # noqa: E402


def emit(value) -> int:
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


def do_plan(args) -> int:
    into = args.into
    if into.exists():
        raise _qualify.QualificationError(f"{into} exists; a frozen plan is never overwritten")
    plan = _qualify.build_plan(
        profile=args.worker_profile, mode=args.mode, cases=args.case or None,
        coordinator=args.coordinator, owner_authorization=args.owner_authorization,
        proposal=args.proposal, per_launch_allowance=args.per_launch_allowance,
        deadline_seconds=args.deadline_seconds,
        executor=str(args.executor) if args.executor else None)
    into.mkdir(parents=True)
    _qualify._write_json(into / "plan.json", plan)
    return emit(_plan_view(plan, into))


def _plan_view(plan, where) -> dict:
    nxt = {_qualify.REPLAY: f"python3 {HERE / 'pb_qualify.py'} replay --plan {where} --into <result>",
           _qualify.PROPOSED: f"NOT AUTHORIZED. After the owner's decision: python3 "
                              f"{HERE / 'pb_qualify.py'} authorize --proposal {where} "
                              "--owner-authorization '<the owner's actual statement>' --into <plan>",
           _qualify.AUTHORIZED: f"python3 {HERE / 'pb_qualify.py'} prepare-live --plan {where} "
                                "--into <runs>"}
    return {"plan": str(where / "plan.json"), "digest": plan["digest"], "mode": plan["mode"],
            "status": plan["status"], "trials": plan["allocation"]["order"],
            "worker_profile": plan["worker_profile"]["settings"]["profile"]["id"],
            "allocation": {c: {k: v for k, v in a.items() if k in ("ceiling", "minimum",
                                                                     "aggregate_limit", "reserve")}
                           for c, a in plan["resources"]["per_case"].items()},
            "campaign": plan["resources"]["campaign"], "next": nxt[plan["status"]]}


def do_authorize(args) -> int:
    proposal = _qualify.load_plan(args.proposal)
    if args.into.exists():
        raise _qualify.QualificationError(f"{args.into} exists; a plan is never overwritten")
    plan = _qualify.authorize_proposal(proposal, args.owner_authorization)
    args.into.mkdir(parents=True)
    _qualify._write_json(args.into / "plan.json", plan)
    return emit(_plan_view(plan, args.into))


def do_prepare_live(args) -> int:
    plan = _qualify.load_plan(args.plan)
    if plan["mode"] != _qualify.LIVE:
        raise _qualify.QualificationError("this is a replay plan; use `replay`")
    _qualify.assert_executable(plan)
    executor = plan["executor"]["path"]
    if not executor:
        raise _qualify.QualificationError("a live plan must name the pinned executor (--executor)")
    ready = subprocess.run([sys.executable, str(_qualify.CLI), "doctor", "--worker-profile",
                            plan["worker_profile"]["selector"], "--executor", executor],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
    readiness = json.loads(ready.stdout)
    if not readiness.get("ready"):
        # Before anything is created: an unready configuration leaves no half-prepared runs.
        raise _qualify.QualificationError("readiness problems, nothing prepared: "
                                          + "; ".join(readiness.get("problems", [])))
    if args.into.exists():
        raise _qualify.QualificationError(f"{args.into} exists; never overwritten")
    prepared = []
    for trial in _qualify.trials(plan):
        work = args.into / "trials" / trial["trial_id"]
        work.mkdir(parents=True)
        started = _qualify.start_trial(plan, trial, work,
                                       profile_selector=plan["worker_profile"]["selector"],
                                       executor=executor)
        # What `start` froze must be what the plan froze, before anything is authorized.
        _qualify.assert_run_matches(plan, started["run"], executor_sha=plan["executor"]["sha256"])
        _qualify.authorize(plan, started["run"], trial["case"])
        prepared.append({**trial, "run": str(started["run"]), "project": str(started["project"]),
                         "stops": _qualify.CASES[trial["case"]]["stops"]})
    _qualify._write_json(args.into / "live.json", {"plan_digest": plan["digest"],
                                                   "trials": prepared})
    return emit({"prepared": prepared, "launched": 0,
                 "next": "a coordinator drives each run with pb_workflow.py status / continue / "
                         "decide until the trial's stopping point, recording itself with "
                         "`pb_workflow.py coordinator`; then run `pb_qualify.py grade --live "
                         f"{args.into} --plan {args.plan}`"})


def do_grade(args) -> int:
    plan = _qualify.load_plan(args.plan)
    live = json.loads((args.live / "live.json").read_text(encoding="utf-8"))
    if live["plan_digest"] != plan["digest"]:
        raise _qualify.QualificationError("these runs were prepared under a different plan")
    _qualify.assert_gradeable(plan)
    results = []
    for trial in live["trials"]:
        evidence = args.live / "trials" / trial["trial_id"] / "evidence"
        if evidence.exists():
            raise _qualify.QualificationError(f"{evidence} exists; grading never overwrites")
        spec = {k: trial[k] for k in ("trial_id", "case", "subject", "variant")}
        common = {**spec, "case_identity": _qualify.case_identity(trial["case"]),
                  "transport": "none"}
        if not any(Path(trial["run"]).rglob("attempt.json")):
            # Never driven is not observed — not an infrastructure failure, and not a result.
            results.append({**common, "status": _qualify.NOT_RUN,
                            "reason": "no attempt was launched in this run"})
            continue
        retained = _qualify.retain(Path(trial["run"]), Path(trial["project"]), evidence, plan,
                                   spec)
        status, why = _qualify.trial_status(evidence, trial["case"])
        results.append({**common, "status": status, "reason": why,
                        "evidence_dir": f"trials/{trial['trial_id']}/evidence",
                        "evidence": retained, "outcome": _qualify.grade(evidence, spec),
                        "observed": _qualify.observed(evidence)})
    record = {"format": _qualify.RESULT_FORMAT, "plan": plan, "plan_digest": plan["digest"],
              "started_at": None, "finished_at": _qualify._now(),
              "configuration": _qualify.configuration(plan), "configuration_basis": "planned",
              "observed_configuration": _qualify.observed_configuration(results),
              "graded_under": {"suite": _qualify.suite()["digest"],
                               "control_plane": _qualify.control_plane_digest(),
                               "interpreter": _qualify.interpreter()},
              "selection": {"planned_trials": [t["trial_id"] for t in live["trials"]],
                            "executed": [t["trial_id"] for t in live["trials"]],
                            "not_selected": []},
              "trials": results, "denominators": _qualify.denominators(results, len(results)),
              "summary": _qualify.summary(results),
              "claim": "live: one observation per planned cell under this configuration; not a "
                       "rate, a ranking or a reliability estimate"}
    _qualify._write_json(args.live / "result.json", record)
    return emit({"result": str(args.live / "result.json"), "denominators": record["denominators"]})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("suite", help="describe the qualification suite")
    p = sub.add_parser("plan", help="freeze a bounded plan")
    p.add_argument("--worker-profile", required=True)
    p.add_argument("--mode", choices=[_qualify.REPLAY, _qualify.LIVE], default=_qualify.REPLAY)
    p.add_argument("--into", type=Path, required=True)
    p.add_argument("--case", action="append", choices=sorted(_qualify.CASES))
    p.add_argument("--coordinator", help="the coordinator configuration that will drive a live plan")
    p.add_argument("--owner-authorization", help="the owner's own statement; makes a live plan "
                                                 "executable")
    p.add_argument("--proposal", action="store_true",
                   help="freeze a live plan without authorization; it cannot be executed")
    p.add_argument("--per-launch-allowance", type=float,
                   help="billed workers: derived-spend allowance per launch; each trial's limit is "
                        "its enumerated launch ceiling times this")
    p.add_argument("--deadline-seconds", type=int, help="per attempt (default: 900 live, 300 "
                                                        "replay)")
    p.add_argument("--executor", type=Path, help="the pinned executor a live plan will use")
    au = sub.add_parser("authorize", help="authorize a retained proposal with the owner's statement")
    au.add_argument("--proposal", type=Path, required=True)
    au.add_argument("--owner-authorization", required=True)
    au.add_argument("--into", type=Path, required=True)
    r = sub.add_parser("replay", help="execute a replay plan with stand-ins")
    r.add_argument("--plan", type=Path, required=True)
    r.add_argument("--into", type=Path, required=True)
    r.add_argument("--only", action="append", help="a case or trial id; repeatable")
    pl = sub.add_parser("prepare-live", help="start and authorize a live plan's runs")
    pl.add_argument("--plan", type=Path, required=True)
    pl.add_argument("--into", type=Path, required=True)
    g = sub.add_parser("grade", help="grade a live plan's runs")
    g.add_argument("--plan", type=Path, required=True)
    g.add_argument("--live", type=Path, required=True)
    i = sub.add_parser("inspect", help="re-derive grades from retained evidence")
    i.add_argument("--result", type=Path, required=True)
    c = sub.add_parser("compare", help="derived comparison of two results")
    c.add_argument("a", type=Path)
    c.add_argument("b", type=Path)
    c.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        if args.command == "suite":
            return emit(_qualify.suite())
        if args.command == "plan":
            return do_plan(args)
        if args.command == "authorize":
            return do_authorize(args)
        if args.command == "replay":
            record = _qualify.replay(args.plan, args.into, only=args.only)
            return emit({"result": str(args.into), "denominators": record["denominators"],
                         "summary": record["summary"],
                         "replay_as_declared": record["replay_as_declared"],
                         "outcomes": {t["trial_id"]: (t.get("outcome") or {}).get(
                             "outcome") or (t.get("outcome") or {}).get("review")
                             or (t.get("outcome") or {}).get("delivered_verdict") or t["status"]
                             for t in record["trials"]},
                         "claim": record["claim"]})
        if args.command == "prepare-live":
            return do_prepare_live(args)
        if args.command == "grade":
            return do_grade(args)
        if args.command == "inspect":
            report = _qualify.inspect(args.result)
            emit(report)
            return 1 if report["mismatches"] else 0
        comparison = _compare.compare_qualification(_qualify.load_result(args.a),
                                                    _qualify.load_result(args.b),
                                                    label_a=str(args.a), label_b=str(args.b))
        if args.json:
            return emit(comparison)
        print(_compare.render_qualification(comparison))
        return 0
    except (_qualify.QualificationError, _compare.ComparisonError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
