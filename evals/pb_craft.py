#!/usr/bin/env python3
"""Run the system-craft calibration.

    WARNING: `run` invokes real models — one implementation trial, one craft reflection and one
    grading call per trial. Nothing here is part of the deterministic suite.

    validate        check behavioural equivalence and blindness without any model call
    run             execute the calibration matrix and write a summary
    reflect         re-reflect on retained implementations under two context arms
    regrade         repeat the grader over frozen report bytes
    repeat-reflect  repeat the reflector over frozen implementations, grading each result once
"""
from __future__ import annotations

import argparse
import hashlib
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
import _experiment  # noqa: E402
import _grade  # noqa: E402
import _repeat  # noqa: E402
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


def _retained_trials(evidence: Path, case: dict) -> list[dict]:
    """Every retained implementation whose change can still be reconstructed.

    Pairing on the same implementation is what makes the routing question answerable: the
    architecture, the model's actual code and the resulting change are held exactly constant, so
    the only thing that differs between the two arms is what the reflector was asked.
    """
    by_id = {s["id"]: s for s in case["states"]}
    out = []
    for tree in sorted(Path(evidence).iterdir()):
        if not tree.is_dir():
            continue
        sid = tree.name.rsplit("-", 1)[0]
        if sid not in by_id:
            continue
        project = tree / "project"
        diff = subprocess.run(["git", "-C", str(project), "diff", "HEAD"],
                              capture_output=True, text=True, check=False).stdout
        if not diff.strip():
            continue  # no reconstructable change: the trial never implemented anything
        out.append({"instance": tree.name, "state": sid, "diff": diff,
                    "identity": by_id[sid]["identity"]})
    return out


def _routing_summary(case: dict, args: argparse.Namespace, results: list[dict]) -> dict:
    """The durable shape of a routing run: what was asked, of what, under which configuration."""
    treatment = Path(args.treatment)
    return {
        "format": "proofbound-craft-routing-v1",
        "case": case["id"], "property": case["property"],
        "treatment": {"path": str(args.treatment),
                      "sha256": hashlib.sha256(treatment.read_bytes()).hexdigest(),
                      "bytes": len(treatment.read_bytes())},
        "system": {"proofbound_sha": subprocess.run(
                       ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                       capture_output=True, text=True, check=False).stdout.strip() or None,
                   "harness": "opencode-cli", "harness_version": harness_version(),
                   "reflector_model": args.reflector_model,
                   "grader_model": args.grader_model,
                   "python": f"{sys.version_info.major}.{sys.version_info.minor}"},
        "states": {s["id"]: {"identity": s["identity"],
                             "status": case["ground_truth"][s["id"]]["status"]}
                   for s in case["states"]},
        "pairs": results,
    }


def cmd_reflect(args: argparse.Namespace) -> int:
    """Paired untreated/question-routed reflection over retained implementations."""
    case = _craft.load(args.case)
    ok, detail = provider_available()
    if not ok:
        print(f"ERROR: cannot reflect: {detail}", file=sys.stderr)
        return 2
    treatment = Path(args.treatment).read_text(encoding="utf-8")
    intent = Path(case["intent"]).read_text(encoding="utf-8")
    contract = Path(case["contract"]).read_text(encoding="utf-8")
    by_id = {s["id"]: s for s in case["states"]}
    trials = _retained_trials(args.evidence, case)
    print(f"{len(trials)} retained implementations; two arms each\n")

    results: list[dict] = []

    def write_summary() -> None:
        """Persist after every pair.

        A paired matrix is hours of provider calls, and an interruption partway through should
        cost the remaining pairs, never the ones already paid for. Written to a temporary file
        and renamed, so a reader never catches a half-serialised record, and rewritten whole
        each time, so the file is always an honest description of the pairs that finished.
        """
        tmp = args.out.with_suffix(args.out.suffix + ".partial")
        tmp.write_text(json.dumps(_routing_summary(case, args, results),
                                  indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(args.out)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    for n, trial in enumerate(trials, 1):
        state = by_id[trial["state"]]
        before = "\n".join(
            f"--- {p.relative_to(state['fixture'])}\n"
            f"{p.read_text(encoding='utf-8', errors='ignore')}"
            for p in sorted(_craft._fixture_files(Path(state["fixture"]))))
        # Counterbalanced: the arm that runs first alternates, and neither inherits anything
        # from the other — every reflection is a separate fresh invocation.
        arms = [_craft.UNTREATED, _craft.QUESTION_ROUTED]
        if n % 2 == 0:
            arms.reverse()
        entry = {"instance": trial["instance"], "state": trial["state"],
                 "state_identity": trial["identity"], "arm_order": list(arms), "arms": {}}
        for arm in arms:
            got = _craft.reflect(intent=intent, contract=contract, before=before,
                                 diff=trial["diff"][:20000], model=args.reflector_model,
                                 treatment=treatment if arm == _craft.QUESTION_ROUTED else None)
            record = {"report": got.get("report"), "reason": got.get("reason")}
            if got.get("report"):
                claim = _craft.classify_claim(got["report"], case["property"]["scenario"],
                                              model=args.grader_model)
                record["claim"] = claim["claim"]
                record["claim_reason"] = claim.get("reason", "")[:300]
                record["outcome"] = _craft.outcome(
                    case["ground_truth"][trial["state"]]["status"], claim["claim"])
            entry["arms"][arm] = record
        results.append(entry)
        write_summary()
        print(f"  {n}/{len(trials)} {trial['state']}: "
              f"U={entry['arms'][_craft.UNTREATED].get('outcome')} "
              f"Q={entry['arms'][_craft.QUESTION_ROUTED].get('outcome')}", flush=True)

    write_summary()
    print(f"\nsummary written: {args.out}")
    return 0


def _anchors(case_dir: Path, subdir: str = "anchors") -> tuple[dict, list[dict]]:
    """The frozen report corpus, verified byte-for-byte against its manifest.

    An anchor whose bytes no longer hash to what was pre-registered is not an anchor: the whole
    point of layer G is that the text does not move, so a mismatch stops the run rather than
    quietly measuring something else.

    `subdir` selects which frozen corpus. A second corpus exists because a second semantic column
    exists, and a column's dispersion belongs to that column rather than to the grader in general.
    """
    directory = Path(case_dir) / subdir
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    loaded = []
    for entry in manifest["anchors"]:
        data = (directory / f"{entry['id']}.md").read_bytes()
        got = hashlib.sha256(data).hexdigest()
        if got != entry["sha256"] or len(data) != entry["bytes"]:
            raise ValueError(f"anchor {entry['id']} no longer matches its manifest hash")
        loaded.append({**entry, "report": data.decode("utf-8")})
    return manifest, loaded


def _frozen_system(args: argparse.Namespace, **extra: object) -> dict:
    return {"proofbound_sha": subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=False).stdout.strip() or None,
            "harness": "opencode-cli", "harness_version": harness_version(),
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "grader_prompt_sha256": _repeat.sha256_text(_craft.GRADER_PROMPT),
            **extra}


def _discovery_grader(report: str, statement: str, **kw: object) -> dict:
    """The closed-world question, adapted to the repeated-measurement interface.

    `grade_property` asks whether a report identifies one specific planted problem — the question
    every other Proofbound evaluation grades with, and a materially different one from the craft
    verdict grader, which answers "upheld" both when a report says the property holds and when it
    never mentions it. Its answer *is* the outcome: there is no declared status to combine with,
    because a report either surfaced the pressure or it did not.
    """
    got = _grade.grade_property(report, statement, **kw)
    return {"claim": got["result"], "reason": got.get("reason", "")}


def cmd_regrade(args: argparse.Namespace) -> int:
    """Layer G — identical report bytes, graded again and again."""
    case = _craft.load(args.case)
    ok, detail = provider_available()
    if not ok:
        print(f"ERROR: cannot grade: {detail}", file=sys.stderr)
        return 2
    manifest, anchors = _anchors(args.case, args.anchors)
    discovery = args.question == "discovery"
    if discovery and args.pressure_file:
        # A pressure frozen in its own pre-registration, read from the file that froze it, so the
        # bytes graded are the bytes committed.
        statement = Path(args.pressure_file).read_text(encoding="utf-8").strip()
        if len(statement) < 20:
            raise ValueError(f"{args.pressure_file} does not state a pressure")
    elif discovery:
        # The planted problem, taken verbatim from the case's own committed ground truth. It was
        # written when the case was built, is never shown to a worker or a reflector, and is not
        # authored here — a statement invented now could be fitted to reports already read.
        statement = case["ground_truth"][args.problem_state]["rationale"]
        if not statement.strip():
            raise ValueError(f"state {args.problem_state!r} declares no rationale to grade against")
    else:
        statement = case["property"]["scenario"]
    config = {
        "format": "proofbound-craft-grader-repeat-v1", "layer": _repeat.GRADER_LAYER,
        "question": args.question,
        "case": case["id"], "property": case["property"], "repeats": args.repeats,
        "graded_statement": statement,
        "anchor_corpus": args.anchors,
        "anchor_selection": manifest["selection_rule"],
        "anchors": [{k: v for k, v in a.items() if k != "report"} for a in anchors],
        "system": _frozen_system(args, grader_model=args.grader_model),
    }
    measurements = _repeat.load_series(args.out, config)
    if measurements:
        print(f"resuming: {len(measurements)} measurements already recorded for this "
              f"frozen configuration")

    for anchor in anchors:
        status = case["ground_truth"][anchor["state"]]["status"]
        for n in range(1, args.repeats + 1):
            if _repeat._already_done(measurements, (anchor["id"], n)):
                continue
            if discovery:
                got = _repeat.grade_once(
                    anchor["report"], statement, status=status,
                    grader=_discovery_grader, outcome=lambda _status, claim: claim,
                    unavailable=_grade.UNAVAILABLE, grader_model=args.grader_model)
            else:
                got = _repeat.grade_once(
                    anchor["report"], statement, status=status,
                    grader=_craft.classify_claim, outcome=_craft.outcome,
                    unavailable=_craft.UNAVAILABLE, model=args.grader_model)
            measurements.append({"item": anchor["id"], "repeat": n, **got})
            _repeat.write_series(args.out, config, measurements)
            print(f"  {anchor['id']} {n}/{args.repeats}: {got['status']} "
                  f"{got.get('outcome') or ''}", flush=True)

    for anchor in anchors:
        print(f"\n{anchor['id']} ({anchor['state']}, prior {anchor['prior_outcome']}): "
              f"{_repeat.distribution(measurements, anchor['id'])['counts']}")
    print(f"\nrecord written: {args.out}")
    return 0


def cmd_repeat_reflect(args: argparse.Namespace) -> int:
    """Layers R and E — identical architecture, reflected again and again, each result graded once."""
    case = _craft.load(args.case)
    ok, detail = provider_available()
    if not ok:
        print(f"ERROR: cannot reflect: {detail}", file=sys.stderr)
        return 2
    intent = Path(case["intent"]).read_text(encoding="utf-8")
    contract = Path(case["contract"]).read_text(encoding="utf-8")
    by_id = {s["id"]: s for s in case["states"]}
    wanted = [name.strip() for name in args.instances.split(",") if name.strip()]
    retained = {t["instance"]: t for t in _retained_trials(args.evidence, case)}
    missing = [name for name in wanted if name not in retained]
    if missing:
        raise ValueError(f"no retained implementation for: {', '.join(missing)}")

    items = []
    for name in wanted:
        trial = retained[name]
        state = by_id[trial["state"]]
        before = "\n".join(
            f"--- {p.relative_to(state['fixture'])}\n"
            f"{p.read_text(encoding='utf-8', errors='ignore')}"
            for p in sorted(_craft._fixture_files(Path(state["fixture"]))))
        diff = trial["diff"][:20000]
        prompt = _craft.CRAFT_PROMPT.format(intent=intent, contract=contract,
                                            before=before, diff=diff)
        items.append({"instance": name, "state": trial["state"],
                      "state_identity": trial["identity"], "before": before, "diff": diff,
                      "before_sha256": _repeat.sha256_text(before),
                      "diff_sha256": _repeat.sha256_text(diff),
                      "prompt_sha256": _repeat.sha256_text(prompt),
                      "prompt_bytes": len(prompt.encode("utf-8"))})

    config = {
        "format": "proofbound-craft-reflector-repeat-v1", "layer": _repeat.REFLECTOR_LAYER,
        "case": case["id"], "property": case["property"], "repeats": args.repeats,
        "treatment": None,
        "instances": [{k: v for k, v in i.items() if k not in ("before", "diff")} for i in items],
        "system": _frozen_system(args, reflector_model=args.reflector_model,
                                 grader_model=args.grader_model,
                                 craft_prompt_sha256=_repeat.sha256_text(_craft.CRAFT_PROMPT)),
    }
    raw = _repeat.load_series(args.raw, config)
    if raw:
        print(f"resuming: {len(raw)} measurements already recorded for this frozen configuration")

    scenario = case["property"]["scenario"]
    for item in items:
        status = case["ground_truth"][item["state"]]["status"]
        for n in range(1, args.repeats + 1):
            if _repeat._already_done(raw, (item["instance"], n)):
                continue
            got = _repeat.reflect_once(
                reflector=_craft.reflect, intent=intent, contract=contract,
                before=item["before"], diff=item["diff"], model=args.reflector_model)
            record = {"item": item["instance"], "repeat": n,
                      "reflection_status": got["status"], "seconds_reflect": got["seconds"]}
            if got["status"] == _repeat.REFLECTED:
                record.update({"report": got["report"], "report_sha256": got["report_sha256"],
                               "report_bytes": got["report_bytes"]})
                graded = _repeat.grade_once(
                    got["report"], scenario, status=status, grader=_craft.classify_claim,
                    outcome=_craft.outcome, unavailable=_craft.UNAVAILABLE,
                    model=args.grader_model)
                record.update({"status": graded["status"], "claim": graded["claim"],
                               "outcome": graded["outcome"], "reason": graded["reason"],
                               "seconds_grade": graded["seconds"]})
            else:
                record.update({"status": _repeat.REFLECTION_FAILURE, "claim": None,
                               "outcome": None, "reason": got["reason"]})
            raw.append(record)
            _repeat.write_series(args.raw, config, raw)
            _repeat.write_series(args.out, config, _repeat.redact(raw))
            print(f"  {item['instance']} {n}/{args.repeats}: {record['status']} "
                  f"{record.get('outcome') or ''}", flush=True)

    for item in items:
        print(f"\n{item['instance']} ({item['state']}): "
              f"{_repeat.distribution(raw, item['instance'])['counts']}")
    print(f"\ndurable record: {args.out}\nlocal reports:  {args.raw}")
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    """Execute one pre-registered closed-world experiment. Never runs during the test suite."""
    experiment = _experiment.load(args.experiment)
    case = _craft.load(args.case)
    ok, detail = provider_available()
    if not ok:
        print(f"ERROR: cannot sample: {detail}", file=sys.stderr)
        return 2

    intent = Path(case["intent"]).read_text(encoding="utf-8")
    contract = Path(case["contract"]).read_text(encoding="utf-8")
    by_id = {s["id"]: s for s in case["states"]}
    retained = {t["instance"]: t for t in _retained_trials(args.evidence, case)}
    missing = [n for n in experiment["instances"] if n not in retained]
    if missing:
        raise ValueError(f"no retained implementation for: {', '.join(missing)}")

    arms = {}
    for arm in experiment["arms"]:
        treatment = None
        if arm.get("treatment"):
            treatment = Path(arm["treatment"]).read_text(encoding="utf-8")
            arm["treatment_sha256"] = _repeat.sha256_text(treatment)
        arms[arm["id"]] = treatment

    prepared = {}
    for name in experiment["instances"]:
        trial = retained[name]
        state = by_id[trial["state"]]
        before = "\n".join(
            f"--- {p.relative_to(state['fixture'])}\n"
            f"{p.read_text(encoding='utf-8', errors='ignore')}"
            for p in sorted(_craft._fixture_files(Path(state["fixture"]))))
        prepared[name] = {"before": before, "diff": trial["diff"][:20000],
                          "state": trial["state"], "identity": trial["identity"]}

    config = _experiment.configuration(experiment, _frozen_system(
        args, reflector_model=args.reflector_model, grader_model=args.grader_model,
        craft_prompt_sha256=_repeat.sha256_text(_craft.CRAFT_PROMPT)))
    measurements = _repeat.load_series(args.out, config)
    raw = _repeat.load_series(args.raw, config)
    done_reflections = {r["item"]: r for r in raw}
    if measurements:
        print(f"resuming: {len(measurements)} graded cells and {len(raw)} reflections already "
              f"recorded for this frozen configuration")

    slots = _experiment.slots(experiment)
    print(f"{len(slots)} reflection slots, {len(slots) * len(experiment['pressures'])} "
          f"graded cells\n")
    for n, slot in enumerate(slots, 1):
        rows = _experiment.measurement_rows(experiment, slot)
        if all(_repeat._already_done(measurements, (r["item"], r["repeat"])) for r in rows):
            continue
        item = prepared[slot["instance"]]
        record = done_reflections.get(slot["reflection_slot"])
        if record is None:
            got = _repeat.reflect_once(
                reflector=_craft.reflect, intent=intent, contract=contract,
                before=item["before"], diff=item["diff"], model=args.reflector_model,
                treatment=arms[slot["arm"]])
            record = {"item": slot["reflection_slot"], "repeat": slot["sample"],
                      "instance": slot["instance"], "arm": slot["arm"],
                      "state_identity": item["identity"], **got}
            raw.append(record)
            done_reflections[record["item"]] = record
            _repeat.write_series(args.raw, config, raw)

        for row, pressure in zip(rows, experiment["pressures"]):
            if _repeat._already_done(measurements, (row["item"], row["repeat"])):
                continue
            if record["status"] != _repeat.REFLECTED:
                cell = {"status": _repeat.REFLECTION_FAILURE, "claim": None, "outcome": None}
            else:
                cell = _repeat.grade_once(
                    record["report"], pressure["statement"], status=item["state"],
                    grader=_discovery_grader, outcome=lambda _status, claim: claim,
                    unavailable=_grade.UNAVAILABLE, grader_model=args.grader_model)
            measurements.append({**row, "report_sha256": record.get("report_sha256"),
                                 **{k: v for k, v in cell.items() if k != "reason"}})
            _repeat.write_series(args.out, config, measurements)
        print(f"  {n}/{len(slots)} {slot['instance']} {slot['arm']} #{slot['sample']}: "
              f"{[m.get('outcome') for m in measurements if m['repeat'] == slot['sample'] and m['instance'] == slot['instance'] and m['arm'] == slot['arm']]}",
              flush=True)

    print("\nper-cell distributions (no verdict is derived from these):")
    for cell in _experiment.cells(experiment):
        d = _repeat.distribution(measurements, cell)
        if d["attempted"]:
            print(f"  {cell}: {d['counts']}  graded {d['graded']}/{d['attempted']}")
    print(f"\ndurable record: {args.out}\nlocal reports:  {args.raw}")
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

    f = sub.add_parser("reflect", help="paired U/Q re-reflection over retained implementations")
    f.add_argument("case", type=Path)
    f.add_argument("--evidence", type=Path, required=True)
    f.add_argument("--treatment", type=Path, required=True)
    f.add_argument("--reflector-model", required=True)
    f.add_argument("--grader-model", required=True)
    f.add_argument("--out", type=Path, required=True)
    f.set_defaults(handler=cmd_reflect)

    g = sub.add_parser("regrade", help="layer G: repeat the grader over frozen report bytes")
    g.add_argument("case", type=Path)
    g.add_argument("--grader-model", required=True)
    g.add_argument("--repeats", type=int, required=True)
    g.add_argument("--question", choices=("verdict", "discovery"), default="verdict",
                   help="verdict: does the report say the property fails; "
                        "discovery: does the report identify this specific problem")
    g.add_argument("--problem-state", default="state-c",
                   help="whose declared rationale states the planted problem (discovery only)")
    g.add_argument("--anchors", default="anchors", help="which frozen anchor corpus to grade")
    g.add_argument("--pressure-file", type=Path,
                   help="file holding the exact pressure to grade against (discovery only)")
    g.add_argument("--out", type=Path, required=True)
    g.set_defaults(handler=cmd_regrade)

    q = sub.add_parser("repeat-reflect",
                       help="layers R and E: repeat the reflector over frozen implementations")
    q.add_argument("case", type=Path)
    q.add_argument("--evidence", type=Path, required=True)
    q.add_argument("--instances", required=True,
                   help="comma-separated retained implementation instance names")
    q.add_argument("--reflector-model", required=True)
    q.add_argument("--grader-model", required=True)
    q.add_argument("--repeats", type=int, required=True)
    q.add_argument("--out", type=Path, required=True, help="durable record; carries no report text")
    q.add_argument("--raw", type=Path, required=True, help="local record; retains every report")
    q.set_defaults(handler=cmd_repeat_reflect)

    e = sub.add_parser("sample", help="run one pre-registered closed-world experiment")
    e.add_argument("case", type=Path)
    e.add_argument("--experiment", type=Path, required=True)
    e.add_argument("--evidence", type=Path, required=True)
    e.add_argument("--reflector-model", required=True)
    e.add_argument("--grader-model", required=True)
    e.add_argument("--out", type=Path, required=True, help="durable record; carries no report text")
    e.add_argument("--raw", type=Path, required=True, help="local record; retains every report")
    e.set_defaults(handler=cmd_sample)
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
