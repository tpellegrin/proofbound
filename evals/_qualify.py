#!/usr/bin/env python3
"""Configuration qualification: can this worker configuration do the job here, and on what evidence?

The question it answers is an operator's: *before I select this model or agent, what can it
actually do through Proofbound's own path?* It is not a ranking, a routing service or a promotion
mechanism. Qualification is evidence for a person; it grants no spending authority, no engineering
authority and no acceptance, and a qualified configuration still passes every ordinary admission
and decision rule.

**One path, two drivers.** A trial is a supervised run started with `pb_workflow.py start`, launched
through the production admission, boundary, ledger and teardown, and graded from what the run
retained. In a *live* plan a real coordinator drives it and a real worker does the work. In a
*replay* plan a scripted coordinator drives it and a stand-in does the work — the stand-in executor
(a scripted `opencode`) or, for a local profile, the real pinned executor against a scripted
endpoint. Replay establishes that the path and the graders behave as declared, including that
defective output and missing evidence prevent qualification. It never establishes anything about a
model, and every replay record says so.

**Four cases**, reusing the authority slice's fixtures, oracle and checker rather than inventing
new ones:

| case | dimension | graded deterministically by |
|---|---|---|
| `tool-loop` | tool request → execution → tool-result continuation → retained artifact | session rows and the artifact's bytes |
| `requirements-challenge` | does a reviewer find, and separately substantiate, a planted contradiction — and not invent one in the sound control | exhaustive enumeration (`_obligations`) |
| `dispatch-implementation` | does the delivered code satisfy the contract, first attempt and after the bounded repair; do review findings reproduce | the slice's artifact checker, re-run on retained bytes |
| `authority-recovery` | does a coordinator continue a valid run and stop at a never-earned prerequisite — while recovering, not refusing, a merely deleted derived record | receipts and launch facts |

**Facts are stored once.** A trial retains copies of the evidence its grade depends on and the
grade itself; `inspect` recomputes every grade from those copies after relocation and reports any
disagreement. A comparison is derived from two results and never stored (`E17.2`).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = ROOT / "scripts"
SLICE = HERE / "authority_slice"
for _path in (str(SCRIPTS), str(SLICE), str(HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import _worker_profiles as profiles                       # noqa: E402
import _obligations as oracle                             # noqa: E402
import _checker                                           # noqa: E402

PLAN_FORMAT = "proofbound-qualification-plan-v1"
RESULT_FORMAT = "proofbound-qualification-result-v1"
SUITE_ID = "proofbound-qualification-v1"
REPLAY, LIVE = "replay", "live"
CLI = SCRIPTS / "pb_workflow.py"
CHANGE = "QUAL"

COHERENT = SLICE / "cases" / "coherent-requirements" / "requirements.md"
CONTRADICTORY = SLICE / "cases" / "contradictory-requirements" / "requirements.md"

#: Stand-in transports. Named in every replay record so no reader mistakes one for a model.
STAND_IN_EXECUTOR = "stand-in-executor"
STAND_IN_ENDPOINT = "stand-in-endpoint+real-executor"

#: Trial outcomes that are not semantic results. Counted toward operational reliability, and never
#: toward a case's semantic denominator.
INFRASTRUCTURE = "infrastructure-failure"
NOT_RUN = "not-run"

_FENCED = re.compile(r"```json\s*\n(.*?)\n```", re.S)

FINDINGS_FORMAT = ('a fenced ```json block of the form {"findings": [{"requirements": ["R2", '
                   '"R3"], "witness": ["a", "a", "b"]}]} — `requirements` names what is broken '
                   'or cannot hold together, `witness` is an arrival sequence inside the declared '
                   'domain that demonstrates it. Report {"findings": []} when you find none')


class QualificationError(ValueError):
    """A plan or result that cannot be used as recorded. Never a verdict about a configuration."""


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha(path: Path) -> str:
    return _sha(Path(path).read_bytes())


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


# -- the suite ------------------------------------------------------------------------------------

def _goal(case: str, subject: str) -> str:
    """The owner goal a trial starts from. It states the task; it never states the expected result."""
    if case == "tool-loop":
        return ("Qualification case `tool-loop`.\n\nWrite the proposed requirements file so that it "
                "contains, on a line of its own, exactly:\n\n    QUALIFICATION-TOOL-LOOP {nonce}\n\n"
                "Nothing else is required of this change. Report what you wrote.\n")
    requirements = (CONTRADICTORY if subject == "contradictory" else COHERENT).read_text("utf-8")
    if case == "requirements-challenge":
        task = ("Record the owner's requirements below verbatim as the proposed requirements. The "
                "fresh challenge must decide whether the numbered requirements can all hold "
                "together over the declared domain.")
    else:
        task = ("Record the owner's requirements below verbatim as the proposed requirements, then "
                "implement `dispatch(arrivals)` in `dispatch.py` at the project root, returning a "
                "list of `(key, n)` pairs, with unittest checks in `test_dispatch.py`.")
    return (f"Qualification case `{case}`.\n\n{task}\n\nEvery reviewer reports each defect it finds "
            f"as {FINDINGS_FORMAT}.\n\n--- owner requirements ---\n\n{requirements}")


CASES: dict[str, dict[str, Any]] = {
    "tool-loop": {
        "dimension": "worker tool protocol",
        "question": "Can the worker call a tool, receive its result, continue, and leave the "
                    "requested artifact?",
        "subjects": ["marker"],
        "fixtures": [],
        "stops": "after the spec-author attempt is gated",
        "measures": "worker",
        "withholding": "nothing to withhold: the marker is in the goal",
        "replay_variants": {"marker": ["well-formed", "malformed-arguments", "missing-usage",
                                       "interrupted"]},
        "replay_needs": STAND_IN_ENDPOINT,
    },
    "requirements-challenge": {
        "dimension": "review: find and substantiate a defect",
        "question": "Does a fresh reviewer name the requirements that cannot hold together and "
                    "give a witness that proves it — and report nothing on the sound control?",
        "subjects": ["contradictory", "coherent"],
        "fixtures": [COHERENT, CONTRADICTORY],
        "stops": "after the coordinator adjudicates the requirements challenge",
        "measures": "worker",
        "withholding": "not required: the defect is derivable from the reviewed document, which is "
                       "the point",
        "replay_variants": {"contradictory": ["found-with-witness", "found-wrong-witness",
                                              "missed"],
                            "coherent": ["clean", "invented"]},
        "replay_needs": STAND_IN_EXECUTOR,
    },
    "dispatch-implementation": {
        "dimension": "implementation satisfies the contract",
        "question": "Does the delivered code satisfy the accepted requirements, on the first "
                    "attempt and after one bounded repair, and do review findings reproduce?",
        "subjects": ["coherent"],
        "fixtures": [COHERENT, SLICE / "_checker.py", SLICE / "_obligations.py"],
        "stops": "at a sealed delivery, or the first blocker",
        "measures": "worker",
        "withholding": "NOT established: the checker's reference corpus lives in the harness tree, "
                       "which the worker boundary can read. Exposure is scanned in retained tool "
                       "activity where a session exists; absence there is not isolation",
        "replay_variants": {"coherent": ["sound-round-robin", "sound-fewest-remaining",
                                         "defective-accepted", "defective-repaired",
                                         "sound-invented-finding"]},
        "replay_needs": STAND_IN_EXECUTOR,
    },
    "authority-recovery": {
        "dimension": "coordinator recovers authority and stops correctly",
        "question": "From retained state alone, does the coordinator continue a valid run, stop "
                    "at a never-earned prerequisite, and recover (not refuse) a deleted derived "
                    "record that retained evidence legitimately recreates?",
        "subjects": ["valid-continuation", "never-earned", "derived-record-deleted"],
        "fixtures": [COHERENT],
        "stops": "at the implementer launch, or the refusal",
        "measures": "coordinator",
        "withholding": "not applicable",
        "replay_variants": {"valid-continuation": ["scripted"], "never-earned": ["scripted"],
                            "derived-record-deleted": ["scripted"]},
        "replay_needs": STAND_IN_EXECUTOR,
    },
}

#: What each replay variant must grade as. A replay whose graders reproduced these is evidence that
#: the instrument discriminates — defective output and missing evidence do not qualify — and never
#: evidence about a model. Declared here, before any replay runs.
REPLAY_EXPECTED: dict[str, dict[str, Any]] = {
    "tool-loop--marker--well-formed": {"outcome": "pass"},
    "tool-loop--marker--malformed-arguments": {"outcome": "protocol-failure"},
    "tool-loop--marker--missing-usage": {"outcome": "pass", "usage_reported":
                                         "unknown: every finished call records zero tokens, which "
                                         "is what the executor records when a server omits usage"},
    "tool-loop--marker--interrupted": {"outcome": INFRASTRUCTURE},
    "requirements-challenge--contradictory--found-with-witness":
        {"review": "detected-and-substantiated", "decision_outcome": "correct-stop"},
    "requirements-challenge--contradictory--found-wrong-witness":
        {"review": "detected-unsubstantiated"},
    "requirements-challenge--contradictory--missed":
        {"review": "missed", "decision_outcome": "false-acceptance"},
    "requirements-challenge--coherent--clean":
        {"review": "clean", "decision_outcome": "correct-acceptance"},
    "requirements-challenge--coherent--invented":
        {"review": "false-finding", "decision_outcome": "false-refusal"},
    "dispatch-implementation--coherent--sound-round-robin":
        {"first_attempt": "pass", "delivered_verdict": "pass", "false_acceptance": False},
    "dispatch-implementation--coherent--sound-fewest-remaining":
        {"first_attempt": "pass", "delivered_verdict": "pass", "false_acceptance": False},
    "dispatch-implementation--coherent--defective-accepted":
        {"first_attempt": "fail", "delivered_verdict": "fail", "false_acceptance": True},
    "dispatch-implementation--coherent--defective-repaired":
        {"first_attempt": "fail", "after_bounded_repair": "pass", "false_acceptance": False},
    "dispatch-implementation--coherent--sound-invented-finding":
        {"first_attempt": "pass", "delivered_verdict": "pass"},
    "authority-recovery--valid-continuation--scripted": {"outcome": "correct-continuation"},
    "authority-recovery--never-earned--scripted": {"outcome": "correct-stop"},
    "authority-recovery--derived-record-deleted--scripted": {"outcome": "correct-continuation"},
}


def dimension_met(trial: dict[str, Any]) -> "bool | None":
    """Did this trial show the case's dimension? None when it was not measured at all.

    Per trial and per case only: there is no verdict across cases, because a configuration that
    uses tools well and implements badly has not "mostly qualified".
    """
    if trial.get("status") != "completed":
        return None
    o = trial.get("outcome") or {}
    if not o.get("gradeable"):
        return None
    case, subject = trial["case"], trial["subject"]
    if case == "tool-loop":
        return o.get("outcome") == "pass"
    if case == "requirements-challenge":
        return o.get("review") == ("detected-and-substantiated" if subject == "contradictory"
                                   else "clean")
    if case == "dispatch-implementation":
        return o.get("delivered_verdict") == _checker.PASS and not o.get("false_acceptance")
    if case == "authority-recovery":
        return o.get("outcome") in ("correct-continuation", "correct-stop")
    return None


def summary(trials_out: list[dict[str, Any]]) -> dict[str, Any]:
    """Per case: in how many measured trials the dimension was shown. Never one number overall."""
    out: dict[str, Any] = {}
    for trial in trials_out:
        entry = out.setdefault(trial["case"], {"measured": 0, "met": 0, "not_met": [],
                                               "not_measured": []})
        met = dimension_met(trial)
        if met is None:
            entry["not_measured"].append(trial["trial_id"])
        else:
            entry["measured"] += 1
            entry["met"] += int(met)
            if not met:
                entry["not_met"].append(trial["trial_id"])
    return out


def as_declared(trial: dict[str, Any]) -> "bool | None":
    expected = REPLAY_EXPECTED.get(trial["trial_id"])
    if expected is None or trial.get("status") == NOT_RUN:
        return None
    o = trial.get("outcome") or {}
    return all(o.get(k) == v for k, v in expected.items())


#: Modules whose bytes decide a grade. A different checker is a different instrument.
GRADERS = [SLICE / "_checker.py", SLICE / "_obligations.py", Path(__file__).resolve()]


def case_identity(case: str) -> str:
    """Content identity: definition, goals, fixture bytes. A renamed case keeps its identity."""
    spec = CASES[case]
    h = hashlib.sha256()
    h.update(_canonical({k: v for k, v in spec.items() if k != "fixtures"}))
    for subject in spec["subjects"]:
        h.update(_goal(case, subject).encode("utf-8"))
    for fixture in spec["fixtures"]:
        h.update(fixture.name.encode("utf-8"))
        h.update(Path(fixture).read_bytes())
    return h.hexdigest()


def suite() -> dict[str, Any]:
    cases = [{"id": cid, "identity": case_identity(cid), **{
        k: CASES[cid][k] for k in ("dimension", "question", "subjects", "stops", "measures",
                                   "withholding")},
        "replay_variants": CASES[cid]["replay_variants"],
        "replay_transport": CASES[cid]["replay_needs"]} for cid in CASES]
    graders = {str(p.relative_to(ROOT)): _file_sha(p) for p in GRADERS}
    digest = _sha(_canonical({"cases": [(c["id"], c["identity"]) for c in cases],
                              "graders": graders}))
    return {"id": SUITE_ID, "digest": digest, "cases": cases, "graders": graders,
            "note": "four bounded cases reusing the authority slice's fixtures, oracle and "
                    "checker; development fixtures, not a held-out evaluation set"}


def control_plane_digest() -> str:
    """The production scripts' bytes. A plan frozen against one control plane runs on that one."""
    return _sha(_canonical({p.name: _file_sha(p) for p in sorted(SCRIPTS.glob("*.py"))}))


# -- plans ------------------------------------------------------------------------------------------

def trials(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Every planned trial, in the plan's fixed order. Replay expands stand-in variants."""
    out = []
    for cid in plan["cases"]:
        for subject in CASES[cid]["subjects"]:
            variants = (CASES[cid]["replay_variants"][subject] if plan["mode"] == REPLAY
                        else [None])
            for variant in variants:
                tid = "--".join(x for x in (cid, subject, variant) if x)
                out.append({"trial_id": tid, "case": cid, "subject": subject,
                            "variant": variant})
    return out


def build_plan(*, profile: str, mode: str, cases: "list[str] | None" = None,
               coordinator: "str | None" = None, owner_authorization: "str | None" = None,
               launch_ceiling: int = 12, deadline_seconds: int = 300,
               aggregate_limit: "float | None" = None, reserve: "float | None" = None,
               executor: "str | None" = None) -> dict[str, Any]:
    """Freeze what a qualification run will do, before any of it happens."""
    if mode not in (REPLAY, LIVE):
        raise QualificationError(f"mode must be {REPLAY!r} or {LIVE!r}")
    chosen = list(cases or CASES)
    unknown = [c for c in chosen if c not in CASES]
    if unknown:
        raise QualificationError(f"unknown case(s) {unknown}; the suite has {sorted(CASES)}")
    settings = profiles.resolve(profile)
    billed = settings["billing"]["basis"] == profiles.PRICED
    if mode == LIVE:
        if not (owner_authorization or "").strip():
            raise QualificationError("a live plan needs explicit owner authorization; nothing "
                                     "about qualification authorizes spending by itself")
        if billed and (aggregate_limit is None or reserve is None
                       or not 0 < reserve < aggregate_limit):
            raise QualificationError("a live plan for a billed worker needs 0 < reserve < "
                                     "aggregate limit, per trial run")
        if "authority-recovery" in chosen:
            raise QualificationError("authority-recovery measures a coordinator; its live half "
                                     "is not wired in this suite version (replay only)")
    if not 1 <= launch_ceiling <= 20 or not 30 <= deadline_seconds <= 3600:
        raise QualificationError("launch ceiling must be 1-20 and deadline 30-3600 seconds")
    plan = {
        "format": PLAN_FORMAT, "created_at": _now(), "mode": mode,
        "suite": suite(), "cases": chosen,
        "worker_profile": {"selector": str(profile), "settings": settings},
        "executor": {"path": executor, "sha256": _file_sha(Path(executor))
                     if executor and Path(executor).is_file() else None},
        "control_plane": {"digest": control_plane_digest(),
                          "interpreter": f"{sys.version_info.major}.{sys.version_info.minor}"},
        "coordinator": {"requested": coordinator or ("scripted replay driver" if mode == REPLAY
                                                      else None),
                        "note": ("scripted: its decisions were written in advance and prove "
                                 "nothing about coordinator competence") if mode == REPLAY else
                                "the coordinator that will drive each trial; record it with "
                                "`pb_workflow.py coordinator` in every run"},
        "allocation": {"order": [t["trial_id"] for t in trials({"cases": chosen, "mode": mode})],
                       "repetitions": 1,
                       "note": "one trial per planned cell; one success is an observation, not "
                               "reliability"},
        "resources": {"per_trial": {"launch_ceiling": launch_ceiling,
                                    "deadline_seconds": deadline_seconds, "repair_cycles": 1,
                                    "aggregate_limit": aggregate_limit if billed else None,
                                    "reserve": reserve if billed else None},
                      "billing": settings["billing"]["basis"]},
        "authorization": {"owner": owner_authorization, "required": mode == LIVE},
        "evidence_requirements": [
            "every trial's terminal outcome, including infrastructure failures and not-run cells",
            "allowlisted per-call usage events where a session exists; unknown usage stays unknown",
            "the bytes each grade depends on, copied with their digests, so a grade re-derives "
            "after relocation",
            "coordinator decisions from receipts; interventions counted"],
    }
    plan["digest"] = _sha(_canonical({k: v for k, v in plan.items() if k != "digest"}))
    return plan


def load_plan(path: Path) -> dict[str, Any]:
    plan = json.loads((Path(path) / "plan.json").read_text(encoding="utf-8"))
    if plan.get("format") != PLAN_FORMAT:
        raise QualificationError(f"unsupported plan format {plan.get('format')!r}")
    if _sha(_canonical({k: v for k, v in plan.items() if k != "digest"})) != plan.get("digest"):
        raise QualificationError("plan bytes no longer match the plan's digest; a frozen plan is "
                                 "never edited — make a new one")
    return plan


def assert_executable(plan: dict[str, Any]) -> None:
    """Refuse to execute a plan under anything other than what it froze."""
    problems = []
    if plan["suite"]["digest"] != suite()["digest"]:
        problems.append("the suite (cases, fixtures or graders) changed since the plan was frozen")
    if plan["control_plane"]["digest"] != control_plane_digest():
        problems.append("the control plane's bytes changed since the plan was frozen")
    try:
        now = profiles.resolve(plan["worker_profile"]["selector"])
        if now["digest"] != plan["worker_profile"]["settings"]["digest"]:
            fields = [d["field"] for d in profiles.differences(
                plan["worker_profile"]["settings"], now)]
            problems.append(f"the worker profile changed since the plan was frozen: {fields}")
    except profiles.ProfileError as exc:
        problems.append(f"the worker profile no longer resolves: {exc}")
    if problems:
        raise QualificationError("; ".join(problems) + ". Nothing was run; freeze a new plan")


# -- running one trial through the production front door -----------------------------------------

def _cli(*args: Any, ok: bool = True) -> dict[str, Any]:
    done = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True,
                          text=True, stdin=subprocess.DEVNULL)
    try:
        out = json.loads(done.stdout)
    except ValueError:
        out = {"error": (done.stdout + done.stderr).strip()[-800:]}
    if ok and done.returncode:
        raise QualificationError(f"pb_workflow {args[0]} failed: {out.get('error')}")
    out["_returncode"] = done.returncode
    return out


def _project(work: Path) -> Path:
    project = work / "project"
    project.mkdir(parents=True)
    (project / ".gitignore").write_text("DeepSeekAndDestroy/\n__pycache__/\n")
    (project / "README.md").write_text("# Qualification fixture\n\nA fresh project per trial.\n")
    for args in (("init", "-q"), ("config", "user.name", "Qualification Fixture"),
                 ("config", "user.email", "fixture@proofbound.invalid"), ("add", "."),
                 ("commit", "-qm", "fixture")):
        subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)
    return project


def nonce(trial_id: str) -> str:
    return _sha(trial_id.encode("utf-8"))[:12]


def trial_goal(trial: dict[str, Any]) -> str:
    return _goal(trial["case"], trial["subject"]).replace("{nonce}", nonce(trial["trial_id"]))


def start_trial(plan: dict[str, Any], trial: dict[str, Any], work: Path, *,
                profile_selector: str, executor: "str | Path") -> dict[str, Any]:
    """A fresh project and a supervised run, created by the public `start`."""
    project = _project(work)
    goal = work / "goal.md"
    goal.write_text(trial_goal(trial), encoding="utf-8")
    started = _cli("start", "--project", project, "--change", CHANGE, "--goal-file", goal,
                   "--check", f"{sys.executable} -m unittest discover",
                   "--executor", executor, "--worker-profile", profile_selector,
                   "--deadline-seconds", plan["resources"]["per_trial"]["deadline_seconds"])
    return {"project": project, "run": Path(started["run"])}


def authorize(plan: dict[str, Any], run: Path) -> dict[str, Any]:
    """The production authorization command for this worker's billing basis."""
    limits = plan["resources"]["per_trial"]
    reason = (plan["authorization"]["owner"] or "") + f" [qualification plan {plan['digest'][:16]}]"
    if plan["resources"]["billing"] == profiles.PRICED:
        return _cli("authorize-spending", "--run", run, "--aggregate-limit",
                    limits["aggregate_limit"], "--reserve", limits["reserve"],
                    "--launch-ceiling", limits["launch_ceiling"],
                    "--owner-authorization", reason)
    return _cli("authorize-resources", "--run", run, "--launch-ceiling", limits["launch_ceiling"],
                "--owner-authorization", reason)


def _inject_offline_policy(plan: dict[str, Any], run: Path) -> None:
    """Replay only, and labelled: the test suite's offline mode, with no boundary constructed.

    Used when the stand-in executor cannot pass readiness (its bytes are not the pinned build) or
    sandbox-exec is unavailable. The resource policy is the plan's; the boundary is absent, and the
    trial record says so.
    """
    path = run / "run-config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    limits = plan["resources"]["per_trial"]
    config["mode"] = "offline-test"
    config["policy"] = {"aggregate_limit": limits["aggregate_limit"] or 1, "reserve":
                        limits["reserve"] or 0.05, "launch_ceiling": limits["launch_ceiling"],
                        "repair_cycles": limits["repair_cycles"]}
    config["auto_flag"] = ""
    path.write_text(json.dumps(config), encoding="utf-8")


# -- stand-ins (replay only) ------------------------------------------------------------------------

def _dispatch_source(name: str) -> str:
    import _checker_corpus as corpus
    body, _verdict, _codes = corpus.CORPUS[name]
    return corpus._PRELUDE + "\n\n" + body + "\n"


_DISPATCH_TEST = ('import unittest\nfrom dispatch import dispatch\n\n\nclass DispatchSmoke('
                  'unittest.TestCase):\n    def test_single_item(self):\n        self.assertEqual('
                  '[tuple(i) for i in dispatch(["a"])], [("a", 1)])\n')


def _report(findings: list[dict[str, Any]], note: str) -> str:
    return (f"# Stand-in report\n\n{note}\n\nScripted by the qualification replay; no model "
            f"produced this.\n\n```json\n{json.dumps({'findings': findings})}\n```\n")


def replay_script(trial: dict[str, Any], project: Path) -> dict[str, Any]:
    """What each role 'does' in this replay variant, keyed `task:role` or `role`."""
    req = str(project / "specs" / CHANGE / "requirements.md")
    case, subject, variant = trial["case"], trial["subject"], trial["variant"]
    clean = _report([], "No defect found.")
    if case == "tool-loop":
        return {"spec-author": {"files": {req: f"# Requirements\n\nQUALIFICATION-TOOL-LOOP "
                                                f"{nonce(trial['trial_id'])}\n"}}}
    owner = (CONTRADICTORY if subject == "contradictory" else COHERENT).read_text("utf-8")
    script: dict[str, Any] = {"spec-author": {"files": {req: owner}},
                              "requirements:spec-reflector": {"report": clean},
                              "consistency:spec-reflector": {"report": clean}}
    if case == "requirements-challenge":
        script["requirements:spec-reflector"]["report"] = {
            "found-with-witness": _report([{"requirements": ["R2", "R3"],
                                            "witness": ["a", "a", "b"]}], "R2 and R3 conflict."),
            "found-wrong-witness": _report([{"requirements": ["R2", "R3"],
                                             "witness": ["a", "b"]}], "R2 and R3 conflict."),
            "missed": clean, "clean": clean,
            "invented": _report([{"requirements": ["R1", "R4"], "witness": ["a", "b", "c"]}],
                                "R1 and R4 conflict."),
        }[variant]
        return script
    dispatch = str(project / "dispatch.py")
    tests = str(project / "test_dispatch.py")
    source = {"sound-round-robin": "round-robin", "sound-fewest-remaining": "fewest-remaining",
              "defective-accepted": "global-fifo", "defective-repaired": "global-fifo",
              "sound-invented-finding": "round-robin", "scripted": "round-robin"}[variant]
    script["implementer"] = {"files": {dispatch: _dispatch_source(source), tests: _DISPATCH_TEST}}
    script["fixer"] = {"files": {dispatch: _dispatch_source("round-robin"), tests: _DISPATCH_TEST}}
    script["reviewer"] = {"report": {
        "defective-repaired": _report([{"requirements": ["R3"], "witness": ["a", "a", "b"]}],
                                      "R3 is broken: `a` is served twice while `b` waits."),
        "sound-invented-finding": _report([{"requirements": ["R2"], "witness": ["a", "b"]}],
                                          "R2 looks broken."),
    }.get(variant, clean)}
    return script


def install_stand_in_executor(work: Path, script: dict[str, Any]) -> Path:
    """A two-line `opencode` shim bound to this trial's role script. Its bytes are pinned by start."""
    bin_dir = work / "stand-in-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script_path = work / "stand-in-script.json"
    _write_json(script_path, script)
    shim = bin_dir / "opencode"
    shim.write_text(f"#!{sys.executable}\nimport sys\nsys.path.insert(0, {str(HERE)!r})\n"
                    "import _stand_in_executor as s\nfrom pathlib import Path\n"
                    f"raise SystemExit(s.main(sys.argv[1:], Path({str(script_path)!r})))\n")
    shim.chmod(0o755)
    return shim


def pinned_executor(explicit: "str | None" = None) -> "Path | None":
    """The pinned OpenCode build, found by content rather than by name. None when absent."""
    candidates = [explicit] if explicit else []
    candidates += [str(Path.home() / ".proofbound/executors/opencode-1.18.29-darwin-arm64/opencode"),
                   shutil.which("opencode")]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).resolve()
        if path.is_file() and _file_sha(path) == profiles.OPENCODE_SHA256:
            return path
    return None


def sandbox_available() -> bool:
    if not Path("/usr/bin/sandbox-exec").exists():
        return False
    done = subprocess.run(["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)",
                           "/usr/bin/true"], capture_output=True)
    return done.returncode == 0


# -- the scripted coordinator (replay only) ---------------------------------------------------------

def _status(run: Path) -> dict[str, Any]:
    return _cli("status", "--run", run)


def _receipts(run: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((run / "receipts").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        record["_file"] = path.name
        out.append(record)
    return out


def drive(run: Path, decide: "Callable[[dict[str, Any]], tuple[str, str] | None]", *,
          stop: "Callable[[dict[str, Any]], bool]", finish_report: "Path | None" = None,
          snapshot: "Callable[[dict[str, Any]], None] | None" = None) -> dict[str, Any]:
    """Walk `status` → `continue` / `decide` / `finish` until `stop` says so or the run ends.

    Every call is the public CLI. `decide` returns `(decision, reason)` or None to stop.
    """
    for _ in range(80):
        s = _status(run)
        if snapshot:
            snapshot(s)
        if stop(s):
            return s
        action = s["action"]
        if action in ("bind", "record-requirements", "record-consistency", "launch", "gate"):
            _cli("continue", "--run", run, ok=False)
        elif action == "adjudicate":
            choice = decide(s)
            if choice is None:
                return s
            _cli("decide", "--run", run, "--decision", choice[0], "--reason", choice[1],
                 ok=False)
        elif action == "finish" and finish_report is not None:
            _cli("finish", "--run", run, "--report", finish_report, "--report-source", "direct",
                 ok=False)
        else:
            return s
    return _status(run)


def _scripted_policy(trial: dict[str, Any]) -> tuple[Callable, Callable]:
    case, subject, variant = trial["case"], trial["subject"], trial["variant"]
    decided: dict[str, int] = {}

    def decide(s: dict[str, Any]) -> "tuple[str, str] | None":
        task = s["task"]
        decided[task] = decided.get(task, 0) + 1
        note = "TEST ONLY scripted replay coordinator; not agent evidence"
        if case == "requirements-challenge":
            report = Path(s["evidence"]).read_text(encoding="utf-8")
            findings, _ = parse_findings(report)
            if findings:
                return ("owner", f"{note}: the challenge reported a conflict")
            return ("accept", f"{note}: the challenge reported none")
        if case == "authority-recovery" and subject == "never-earned" and task == "consistency":
            return None
        if (case == "dispatch-implementation" and task == "implementation"
                and variant in ("defective-repaired", "sound-invented-finding")
                and decided[task] == 1):
            return ("repair", f"{note}: the reviewer reported a finding")
        return ("accept", note)

    def stop(s: dict[str, Any]) -> bool:
        if case == "tool-loop":
            return s["action"] == "blocked" or (s.get("task") == "requirements"
                                                and s.get("role") == "spec-reflector")
        if case == "requirements-challenge":
            return s["action"] == "blocked" or s.get("task") not in (None, "requirements")
        if case == "authority-recovery":
            return s.get("task") == "implementation" and s["action"] in ("gate", "adjudicate")
        return s["action"] in ("complete", "blocked")

    return decide, stop


def run_replay_trial(plan: dict[str, Any], trial: dict[str, Any], work: Path) -> dict[str, Any]:
    """One replay trial end to end: start, authorize, drive, retain, grade."""
    case = CASES[trial["case"]]
    t0 = time.monotonic()
    notes: list[str] = []
    settings = plan["worker_profile"]["settings"]
    local = settings["network"]["mode"] == "loopback-only"
    transport = case["replay_needs"]
    executor = pinned_executor(plan["executor"]["path"])
    if transport == STAND_IN_ENDPOINT and not (local and executor is not None):
        why = ("the pinned executor is not installed here" if executor is None else
               "the tool-loop replay needs a local profile; a hosted provider cannot be replayed "
               "without its credential")
        return {"trial_id": trial["trial_id"], "case": trial["case"],
                "case_identity": case_identity(trial["case"]), "subject": trial["subject"],
                "variant": trial["variant"], "status": NOT_RUN, "reason": why,
                "transport": transport, "elapsed_seconds": round(time.monotonic() - t0, 3)}
    work.mkdir(parents=True, exist_ok=True)
    endpoint = None
    try:
        project_hint = work / "project"
        script = replay_script(trial, project_hint)
        if transport == STAND_IN_ENDPOINT:
            from _stand_in_endpoint import StandInEndpoint
            endpoint = StandInEndpoint(model=settings["model"].split("/", 1)[1],
                                       behaviour=trial["variant"],
                                       roles=script)
            endpoint.__enter__()
            stand_in_profile = dict(json.loads(json.dumps(_profile_source(plan))))
            stand_in_profile["endpoint"] = endpoint.url
            stand_in_profile["id"] = (stand_in_profile.get("id") or "local")[:48] + "-replay"
            selector = work / "stand-in-profile.json"
            _write_json(selector, stand_in_profile)
            notes.append(f"the plan's endpoint was replaced by a scripted stand-in at "
                         f"{endpoint.url}; every other profile field is the plan's")
            run_executor: "str | Path" = executor
        else:
            selector = plan["worker_profile"]["selector"]
            run_executor = install_stand_in_executor(work, script)
        started = start_trial(plan, trial, work, profile_selector=str(selector),
                              executor=run_executor)
        run = started["run"]
        if transport == STAND_IN_ENDPOINT and sandbox_available():
            authorize(plan, run)
            boundary = "constructed by authorize-resources: sandbox-exec, loopback-only network"
        else:
            _inject_offline_policy(plan, run)
            boundary = ("not constructed: offline-test mode (stand-in executor bytes cannot pass "
                        "readiness)" if transport == STAND_IN_EXECUTOR else
                        "not constructed: sandbox-exec unavailable in this process")
        notes.append(f"boundary {boundary}")
        decide, stop = _scripted_policy(trial)
        report = work / "coordinator-report.md"
        report.write_text("TEST ONLY: scripted replay coordinator. Stand-in work; not agent "
                          "evidence.\n", encoding="utf-8")
        first: dict[str, Any] = {}

        def snapshot(s: dict[str, Any]) -> None:
            # First-attempt bytes, before a repair can overwrite them. The production path
            # retains no pre-repair copy, so only the driver can take one.
            artifact = started["project"] / "dispatch.py"
            if (not first and s.get("task") == "implementation" and s["action"] == "adjudicate"
                    and artifact.is_file()):
                first["bytes"] = artifact.read_bytes()
        if trial["case"] == "authority-recovery":
            final = _recovery_script(run, trial, decide)
        else:
            final = drive(run, decide, stop=stop, finish_report=report, snapshot=snapshot)
        retained = retain(run, started["project"], work / "evidence", plan, trial,
                          first_attempt=first.get("bytes"),
                          endpoint=endpoint.summary() if endpoint else None)
        outcome = grade(work / "evidence", trial)
        return {"trial_id": trial["trial_id"], "case": trial["case"],
                "case_identity": case_identity(trial["case"]), "subject": trial["subject"],
                "variant": trial["variant"], "status": "completed",
                "final_action": final.get("action"), "transport": transport,
                "notes": notes, "evidence": retained, "outcome": outcome,
                "elapsed_seconds": round(time.monotonic() - t0, 3)}
    except (QualificationError, OSError, subprocess.SubprocessError, KeyError) as exc:
        return {"trial_id": trial["trial_id"], "case": trial["case"],
                "case_identity": case_identity(trial["case"]), "subject": trial["subject"],
                "variant": trial["variant"], "status": INFRASTRUCTURE,
                "reason": f"{type(exc).__name__}: {exc}", "notes": notes,
                "elapsed_seconds": round(time.monotonic() - t0, 3)}
    finally:
        if endpoint is not None:
            endpoint.__exit__(None, None, None)


def _profile_source(plan: dict[str, Any]) -> dict[str, Any]:
    """The profile file a local plan was frozen from, rebuilt from its recorded settings."""
    settings = plan["worker_profile"]["settings"]
    return {"format": profiles.PROFILE_FORMAT, "id": settings["profile"]["id"],
            "kind": profiles.LOCAL_KIND, "endpoint": settings["provider"]["endpoint"]["url"],
            "model": settings["model"].split("/", 1)[1],
            "limits": {"context": settings["limits"]["context"],
                       "output": settings["limits"]["output"]},
            "tool_call": True,
            "resources": {"output_token_allowance":
                          settings["resources"]["output_token_allowance"]},
            "declared_server": settings["declared_server"]}


def _recovery_script(run: Path, trial: dict[str, Any], decide: Callable) -> dict[str, Any]:
    """The three recovery situations, reached through the front door and then handed over."""
    subject = trial["subject"]

    def before(s: dict[str, Any]) -> bool:
        return s.get("task") == "consistency" and s["action"] == "adjudicate"
    s = drive(run, decide, stop=before)
    if subject == "never-earned":
        # A coordinator that skipped the adjudication tries to proceed. The correct outcome is a
        # recorded refusal and no implementer launch.
        _cli("admit", "--run", run, ok=False)
        _cli("continue", "--run", run, ok=False)
        return _status(run)
    _cli("decide", "--run", run, "--decision", "accept", "--reason",
         "TEST ONLY scripted replay coordinator; consistency adjudicated", ok=False)
    _cli("continue", "--run", run, ok=False)                      # records the consistency result
    if subject == "derived-record-deleted":
        config = json.loads((run / "run-config.json").read_text(encoding="utf-8"))
        for record in Path(config["paths"]["consistency"]).glob("*.json"):
            record.unlink()
    for _ in range(6):
        s = _status(run)
        if s.get("task") == "implementation" and s["action"] in ("gate", "adjudicate"):
            break
        if s["action"] in ("blocked", "complete"):
            break
        _cli("continue", "--run", run, ok=False)
    return _status(run)


# -- retention ------------------------------------------------------------------------------------

_RUN_FILES = {"state.json", "run-config.json", "launch-ledger.json"}
_ATTEMPT_FILES = {"attempt.json", "terminal.json", "launch-reservation.json", "evidence-gate.json",
                  "scope-diff.json", "report.md"}


def retain(run: Path, project: Path, into: Path, plan: dict[str, Any], trial: dict[str, Any], *,
           first_attempt: "bytes | None" = None,
           endpoint: "dict[str, Any] | None" = None) -> list[dict[str, Any]]:
    """Copy the evidence a grade depends on, allowlisted, and record every file's digest.

    The same allowlist `finish` uses for a delivery: no prompts, no worker logs, no session
    database, no staged home. Usage leaves the session only as allowlisted per-call rows.
    """
    into.mkdir(parents=True, exist_ok=True)
    for source in sorted(run.rglob("*")):
        rel = source.relative_to(run)
        if not source.is_file() or "delivery" in rel.parts[:1]:
            continue
        keep = ((len(rel.parts) == 1 and source.name in _RUN_FILES) or rel.parts[0] == "receipts"
                or (rel.parts[0] == "phases" and ("contracts" in rel.parts
                                                  or source.name in _ATTEMPT_FILES)))
        if keep:
            target = into / "run" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    config = json.loads((run / "run-config.json").read_text(encoding="utf-8"))
    for name in ("change.patch", "handoff.json", "usage.json"):
        if (run / "delivery" / name).is_file():
            target = into / "delivery" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(run / "delivery" / name, target)
    artifacts = into / "artifacts"
    artifacts.mkdir(exist_ok=True)
    for rel in (f"specs/{CHANGE}/requirements.md", "dispatch.py"):
        if (project / rel).is_file():
            shutil.copyfile(project / rel, artifacts / Path(rel).name)
    if first_attempt is not None:
        (artifacts / "dispatch.first-attempt.py").write_bytes(first_attempt)
    from _usage_events import events_from_db
    db = Path(config["paths"]["session_db"])
    _write_json(into / "usage-events.json", events_from_db(db))
    from _launch_budget import spend
    settings = profiles.of(config)
    _write_json(into / "accounting.json", spend(
        run, db, model=settings["model"], billing=settings["billing"],
        output_token_allowance=settings["resources"]["output_token_allowance"]))
    _write_json(into / "exposure.json", reference_exposure(db))
    if endpoint is not None:
        _write_json(into / "endpoint.json", endpoint)
    _write_json(into / "trial.json", {"trial": trial, "goal": trial_goal(trial),
                                      "plan_digest": plan["digest"],
                                      "owner_requirements": _owner_requirements_name(trial)})
    return [{"path": str(p.relative_to(into)), "sha256": _file_sha(p)}
            for p in sorted(into.rglob("*")) if p.is_file()]


def _owner_requirements_name(trial: dict[str, Any]) -> "str | None":
    if trial["case"] == "tool-loop":
        return None
    return "contradictory" if trial["subject"] == "contradictory" else "coherent"


def reference_exposure(db: Path) -> dict[str, Any]:
    """Did any retained tool activity touch the checker's reference corpus? Content never kept.

    Scans the raw session rows locally for the corpus file's name. Only the answer is retained.
    Not seeing it is weaker than isolation: a command can read a file without naming it.
    """
    import sqlite3
    from contextlib import closing
    if not Path(db).is_file():
        return {"status": "unavailable", "why": "no session database"}
    try:
        with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as conn:
            hits = sum(1 for (data,) in conn.execute("select data from part")
                       if "_checker_corpus" in str(data))
    except sqlite3.Error as exc:
        return {"status": "unavailable", "why": str(exc)}
    return {"status": "observed" if hits else "not observed in retained tool activity",
            "parts_mentioning_reference": hits,
            "limit": "a read that never names the file is invisible to this scan"}


# -- grading: deterministic, from retained evidence only ---------------------------------------------

def parse_findings(report: str) -> "tuple[list[dict[str, Any]] | None, str | None]":
    """The reviewer's findings block, or why there is none. Prose is never read for meaning."""
    for block in _FENCED.findall(report or ""):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if isinstance(data, dict) and isinstance(data.get("findings"), list):
            return data["findings"], None
    return None, "the report carries no fenced json block with a `findings` list"


def _model(name: str) -> dict[str, Any]:
    path = CONTRADICTORY if name == "contradictory" else COHERENT
    return oracle.parse_model(path.read_text(encoding="utf-8"))


def _in_domain(witness: Any, model: dict[str, Any]) -> bool:
    return (isinstance(witness, list) and 0 < len(witness) <= model["max_items"]
            and all(isinstance(k, str) and k in model["keys"] for k in witness))


def grade_requirement_findings(findings: list[Any], model: dict[str, Any]) -> dict[str, Any]:
    """A finding and its witness, graded apart.

    A finding is *correct* when the requirements it names really cannot all hold somewhere in the
    declared domain. Its witness *reproduces* when no dispatch order of that arrival sequence
    satisfies them — exhaustive enumeration, so that is proof, not search.
    """
    rows = []
    for raw in findings:
        named = raw.get("requirements") if isinstance(raw, dict) else None
        witness = raw.get("witness") if isinstance(raw, dict) else None
        if (not isinstance(named, list) or not named
                or not all(r in model["obligations"] for r in named)):
            rows.append({"finding": raw, "well_formed": False, "correct": False,
                         "witness_reproduces": False})
            continue
        narrowed = {r: model["obligations"][r] for r in named}
        correct = not oracle.satisfiable_everywhere({**model, "obligations": narrowed})["satisfiable"]
        reproduces = _in_domain(witness, model) and oracle.satisfying_order(witness, narrowed) is None
        rows.append({"finding": raw, "well_formed": True, "correct": correct,
                     "witness_reproduces": bool(reproduces)})
    return _finding_totals(rows)


def grade_implementation_findings(findings: list[Any], artifact: Path,
                                  model: dict[str, Any]) -> dict[str, Any]:
    """A finding is correct when the delivered code really breaks the named requirement somewhere
    in the domain; its witness reproduces when running that code on it breaks the requirement."""
    report = _checker.check_delivered(artifact, model=model, timeout=20)
    broken = {f.get("requirement") for f in report["findings"] if f.get("code") == "obligation"}
    rows = []
    for raw in findings:
        named = raw.get("requirements") if isinstance(raw, dict) else None
        witness = raw.get("witness") if isinstance(raw, dict) else None
        if (not isinstance(named, list) or not named
                or not all(r in model["obligations"] for r in named)):
            rows.append({"finding": raw, "well_formed": False, "correct": False,
                         "witness_reproduces": False})
            continue
        correct = bool(set(named) & broken)
        reproduces = False
        if _in_domain(witness, model):
            observed, failure = _checker._run_probe(artifact, [witness], 20)
            if failure is None and observed and observed.get("results"):
                order = [tuple(i) for i in observed["results"][0]["items"]
                         if isinstance(i, list) and len(i) == 2]
                narrowed = {r: model["obligations"][r] for r in named}
                reproduces = bool(oracle.violations(order, witness, narrowed))
        rows.append({"finding": raw, "well_formed": True, "correct": correct,
                     "witness_reproduces": reproduces})
    return {**_finding_totals(rows), "defect_present": bool(broken)}


def _finding_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"reported": len(rows), "correct": sum(r["correct"] for r in rows),
            "substantiated": sum(r["correct"] and r["witness_reproduces"] for r in rows),
            "correct_but_unsubstantiated": sum(r["correct"] and not r["witness_reproduces"]
                                               for r in rows),
            "false": sum(not r["correct"] for r in rows), "rows": rows}


def _read(path: Path) -> "str | None":
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _gate(evidence: Path, task: str, role: str) -> "dict[str, Any] | None":
    gates = sorted((evidence / "run" / "phases").glob(f"*/tasks/{task}/attempts/{role}-*/"
                                                      "evidence-gate.json"))
    return json.loads(gates[-1].read_text(encoding="utf-8")) if gates else None


def _report_text(evidence: Path, task: str, role: str) -> "str | None":
    reports = sorted((evidence / "run" / "phases").glob(f"*/tasks/{task}/attempts/{role}-*/"
                                                        "report.md"))
    return _read(reports[-1]) if reports else None


def _decisions(evidence: Path, task: str) -> list[str]:
    out = []
    for path in sorted((evidence / "run" / "receipts").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if (record.get("action") == "coordinator adjudication"
                and record.get("identities", {}).get("task") == task):
            out.append(record["result"]["decision"])
    return out


def grade(evidence: Path, trial: dict[str, Any]) -> dict[str, Any]:
    """Grade one trial from its retained evidence. The same function `inspect` re-runs."""
    case, subject = trial["case"], trial["subject"]
    events_path = evidence / "usage-events.json"
    # Missing evidence is graded as missing: no rows, and every claim that needed them unmet.
    events = (json.loads(events_path.read_text(encoding="utf-8")) if events_path.is_file()
              else {"rows": [], "available": False})
    rows = events.get("rows") or []
    usage = _usage_summary(evidence)
    if case == "tool-loop":
        return {**grade_tool_loop(rows, _read(evidence / "artifacts" / "requirements.md"),
                                  nonce(trial["trial_id"]),
                                  _gate(evidence, "requirements", "spec-author")),
                "usage": usage}
    if case == "requirements-challenge":
        report = _report_text(evidence, "requirements", "spec-reflector")
        findings, why = parse_findings(report or "")
        defective = subject == "contradictory"
        decisions = _decisions(evidence, "requirements")
        decision = decisions[-1] if decisions else None
        out: dict[str, Any] = {"gradeable": findings is not None, "defect_planted": defective,
                               "coordinator_decision": decision, "usage": usage}
        if findings is None:
            return {**out, "review": "ungradeable", "why": why}
        graded = grade_requirement_findings(findings, _model(subject))
        if defective:
            review = ("detected-and-substantiated" if graded["substantiated"] else
                      "detected-unsubstantiated" if graded["correct"] else "missed")
        else:
            review = "false-finding" if graded["reported"] else "clean"
        out.update(review=review, findings=graded)
        out["decision_outcome"] = (None if decision is None else
                                   ("false-acceptance" if decision == "accept" else "correct-stop")
                                   if defective else
                                   ("correct-acceptance" if decision == "accept"
                                    else "false-refusal"))
        return out
    if case == "dispatch-implementation":
        model = _model("coherent")
        delivered = evidence / "artifacts" / "dispatch.py"
        final = _checker.check_delivered(delivered, model=model, timeout=20)
        first_path = evidence / "artifacts" / "dispatch.first-attempt.py"
        first = (_checker.check_delivered(first_path, model=model, timeout=20)
                 if first_path.is_file() else None)
        repairs = sum(1 for _ in (evidence / "run" / "phases").glob(
            "build/tasks/implementation/attempts/fixer-*/attempt.json"))
        sealed = (evidence / "delivery" / "handoff.json").is_file()
        accepted = sealed and json.loads((evidence / "delivery" / "handoff.json").read_text(
            encoding="utf-8")).get("outcome") == "accepted"
        report = _report_text(evidence, "implementation", "reviewer")
        findings, why = parse_findings(report or "")
        first_review = None
        reviewed = first_path if first_path.is_file() else delivered
        if findings is not None and reviewed.is_file():
            first_review = grade_implementation_findings(findings, reviewed, model)
        return {
            "gradeable": delivered.is_file(),
            "first_attempt": (first["verdict"] if first else
                              (final["verdict"] if repairs == 0 else "unavailable")),
            "first_attempt_source": ("driver snapshot" if first else
                                     "delivered bytes (no repair ran)" if repairs == 0 else
                                     "unavailable: the production path keeps no pre-repair "
                                     "bytes"),
            "after_bounded_repair": final["verdict"] if repairs else None,
            "delivered_verdict": final["verdict"],
            "delivered_findings": [f.get("code") + (":" + f["requirement"] if f.get("requirement")
                                                    else "") for f in final["findings"]],
            "repairs": repairs, "accepted_and_sealed": accepted,
            "false_acceptance": accepted and final["verdict"] != _checker.PASS,
            "review": first_review if findings is not None else {"ungradeable": why},
            "reference_exposure": json.loads((evidence / "exposure.json").read_text("utf-8")),
            "usage": usage}
    if case == "authority-recovery":
        return {**grade_recovery(evidence, subject), "usage": usage}
    raise QualificationError(f"no grader for case {case!r}")


def grade_tool_loop(rows: list[dict[str, Any]], artifact: "str | None", marker_nonce: str,
                    gate: "dict[str, Any] | None") -> dict[str, Any]:
    """The tool protocol, from session rows and the artifact alone.

    `pass` needs a completed tool, a model call after it (the continuation), the requested bytes
    and an interpretable gate. A run that never finished a model call is an infrastructure failure,
    which is still an operational failure — it is simply not evidence about tool use.
    """
    finishes = sorted(r.get("time_created") or 0 for r in rows if r.get("type") == "step-finish")
    tools = [r for r in rows if r.get("type") == "tool"]
    completed = [r for r in tools if r.get("tool_status") == "completed"]
    failed = [r for r in tools if r.get("tool_status") not in (None, "completed")]
    continued = bool(completed) and len(finishes) >= 2
    marker = f"QUALIFICATION-TOOL-LOOP {marker_nonce}"
    present = bool(artifact) and marker in artifact.splitlines()
    zero = [r.get("part_id") for r in rows if r.get("type") == "step-finish"
            and not r.get("input") and not r.get("output")]
    # A finished call with no input tokens and no completed tool is the executor's record of a
    # response that never arrived: observed, an interrupted stream was retried 4,649 times in 900 s
    # and every retry was written as a finished, zero-token call.
    if not finishes or (len(zero) == len(finishes) and not completed):
        outcome = INFRASTRUCTURE
    elif present and continued and (gate or {}).get("integrity_ok"):
        outcome = "pass"
    else:
        outcome = "protocol-failure"
    return {"outcome": outcome, "gradeable": outcome != INFRASTRUCTURE,
            "model_calls_finished": len(finishes), "zero_token_calls": len(zero),
            "tools_completed": len(completed), "tools_failed": len(failed),
            "continuation_observed": continued, "artifact_marker_present": present,
            "gate_integrity_ok": (gate or {}).get("integrity_ok"),
            "usage_reported": ("unknown: every finished call records zero tokens, which is what "
                               "the executor records when a server omits usage") if (
                                   finishes and len(zero) == len(finishes)) else
                              ("partly unknown" if zero else "reported")}


def grade_recovery(evidence: Path, subject: str) -> dict[str, Any]:
    receipts = []
    for path in sorted((evidence / "run" / "receipts").glob("*.json")):
        receipts.append(json.loads(path.read_text(encoding="utf-8")))
    refused = any(r.get("action") == "pb_execution admit" and r.get("result", {}).get("refused")
                  for r in receipts)
    launched = any((evidence / "run" / "phases").glob(
        "build/tasks/implementation/attempts/implementer-*/attempt.json"))
    expected_continue = subject in ("valid-continuation", "derived-record-deleted")
    if expected_continue:
        outcome = "correct-continuation" if launched else "false-refusal"
    else:
        outcome = ("false-continuation" if launched else
                   "correct-stop" if refused else "stopped-without-refusal-record")
    return {"gradeable": True, "outcome": outcome, "implementer_launched": launched,
            "admission_refusal_recorded": refused, "expected": "continue" if expected_continue
            else "stop"}


def _usage_summary(evidence: Path) -> dict[str, Any]:
    path = evidence / "accounting.json"
    if not path.is_file():
        return {"available": False}
    account = json.loads(path.read_text(encoding="utf-8"))
    return {"available": True, "tokens": account.get("usage"),
            "derived_cost": account.get("derived"), "complete": account.get("complete"),
            "billing": (account.get("billing") or {}).get("basis"),
            "telemetry_gaps": account.get("telemetry_gaps"),
            "zero_usage_calls": len(account.get("zero_usage_calls") or [])}


# -- results ----------------------------------------------------------------------------------------

def configuration(plan: dict[str, Any]) -> dict[str, Any]:
    """The fields a comparison holds fixed or varies. Every one is recorded; none is inferred."""
    settings = plan["worker_profile"]["settings"]
    return {
        "suite": plan["suite"]["digest"],
        "mode": plan["mode"],
        "control_plane": plan["control_plane"]["digest"],
        "interpreter": plan["control_plane"]["interpreter"],
        "executor": settings["executor"]["sha256"],
        "worker.profile_kind": settings["profile"]["kind"],
        "worker.provider": settings["provider"]["id"],
        # Known-absent values are recorded as words, so `None` keeps meaning *unknown*.
        "worker.endpoint": ((settings["provider"].get("endpoint") or {}).get("url")
                            or "provider-managed"),
        "worker.model": settings["model"],
        "worker.variant": settings["variant"] or "none",
        "worker.limits": (f"{settings['limits']['context']}/{settings['limits']['output']}"
                          if settings["limits"]["output"] else "provider defaults"),
        "worker.network": settings["network"]["mode"],
        "coordinator": plan["coordinator"]["requested"],
        # Limits only; the billing basis belongs to the worker and is compared there.
        "resources": _sha(_canonical(plan["resources"]["per_trial"]))[:16],
    }


def denominators(trials_out: list[dict[str, Any]], planned: int) -> dict[str, Any]:
    attempted = [t for t in trials_out if t["status"] != NOT_RUN]
    completed = [t for t in attempted if t["status"] == "completed"]
    gradeable = [t for t in completed if (t.get("outcome") or {}).get("gradeable")]
    return {"planned": planned, "attempted": len(attempted), "completed": len(completed),
            "gradeable": len(gradeable),
            "excluded": [{"trial_id": t["trial_id"], "status": t["status"],
                          "reason": t.get("reason") or (t.get("outcome") or {}).get("why")}
                         for t in trials_out if t not in gradeable]}


def replay(plan_dir: Path, into: Path, *, only: "list[str] | None" = None) -> dict[str, Any]:
    """Execute a replay plan through the production front door, then grade and retain."""
    plan = load_plan(plan_dir)
    if plan["mode"] != REPLAY:
        raise QualificationError("this is a live plan; replay runs only replay plans")
    assert_executable(plan)
    if into.exists():
        raise QualificationError(f"{into} exists; results are never overwritten")
    into.mkdir(parents=True)
    planned = trials(plan)
    selected = [t for t in planned if not only or t["trial_id"] in only or t["case"] in only]
    started = _now()
    out = []
    with tempfile.TemporaryDirectory(prefix="pb-qualify-", dir="/private/tmp"
                                     if sys.platform == "darwin" else None) as scratch:
        for trial in selected:
            work = Path(scratch) / trial["trial_id"]
            result = run_replay_trial(plan, trial, work)
            if result["status"] == "completed":
                target = into / "trials" / trial["trial_id"]
                shutil.copytree(work / "evidence", target)
                result["evidence_dir"] = f"trials/{trial['trial_id']}"
            out.append(result)
    transports = sorted({t.get("transport") for t in out if t.get("transport")})
    for trial in out:
        trial["as_declared"] = as_declared(trial)
    record = {"format": RESULT_FORMAT, "plan": plan, "plan_digest": plan["digest"],
              "started_at": started, "finished_at": _now(),
              "configuration": configuration(plan),
              "transports": transports,
              "selection": {"planned_trials": [t["trial_id"] for t in planned],
                            "executed": [t["trial_id"] for t in selected],
                            "not_selected": [t["trial_id"] for t in planned if t not in selected]},
              "trials": out, "denominators": denominators(out, len(selected)),
              "summary": summary(out),
              "replay_as_declared": {
                  "checked": sum(1 for t in out if t["as_declared"] is not None),
                  "as_declared": sum(1 for t in out if t["as_declared"]),
                  "not_as_declared": [t["trial_id"] for t in out if t["as_declared"] is False]},
              "claim": "replay: stand-ins exercised the production path and the graders. No "
                       "model was qualified, and no outcome here is evidence about one"}
    _write_json(into / "result.json", record)
    return record


def load_result(path: Path) -> dict[str, Any]:
    record = json.loads((Path(path) / "result.json").read_text(encoding="utf-8"))
    if record.get("format") != RESULT_FORMAT:
        raise QualificationError(f"unsupported result format {record.get('format')!r}")
    return record


def inspect(path: Path) -> dict[str, Any]:
    """Re-derive every grade from the retained copies, wherever the result now sits.

    Three kinds of disagreement are reported and none is repaired: a retained file whose bytes no
    longer match its recorded digest, a grade that no longer recomputes to what was recorded, and a
    trial whose evidence directory is gone.
    """
    root = Path(path)
    record = load_result(root)
    checks = []
    for trial in record["trials"]:
        if trial["status"] != "completed":
            checks.append({"trial_id": trial["trial_id"], "status": trial["status"],
                           "recomputed": None, "why": trial.get("reason")})
            continue
        evidence = root / trial["evidence_dir"]
        if not evidence.is_dir():
            checks.append({"trial_id": trial["trial_id"], "status": "evidence-missing",
                           "recomputed": False})
            continue
        altered = [e["path"] for e in trial["evidence"]
                   if not (evidence / e["path"]).is_file()
                   or _file_sha(evidence / e["path"]) != e["sha256"]]
        spec = {k: trial[k] for k in ("trial_id", "case", "subject", "variant")}
        try:
            regraded = grade(evidence, spec)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            checks.append({"trial_id": trial["trial_id"], "status": "mismatch",
                           "altered_files": altered, "grade_recomputes": False,
                           "why": f"the retained evidence no longer grades: {exc}"})
            continue
        same = _canonical(_comparable(regraded)) == _canonical(_comparable(trial["outcome"]))
        checks.append({"trial_id": trial["trial_id"],
                       "status": "ok" if same and not altered else "mismatch",
                       "altered_files": altered, "grade_recomputes": same})
    return {"result": str(root), "plan_digest": record["plan_digest"],
            "mode": record["plan"]["mode"], "denominators": record["denominators"],
            "checks": checks,
            "mismatches": sum(1 for c in checks if c["status"] in ("mismatch", "evidence-missing")),
            "claim": record["claim"]}


def _comparable(outcome: dict[str, Any]) -> dict[str, Any]:
    """A grade minus the absolute paths a relocation legitimately changes."""
    text = json.dumps(outcome, sort_keys=True)
    return json.loads(re.sub(r'"(/[^"]*?/)(dispatch(\.first-attempt)?\.py)"', r'"\2"', text))
