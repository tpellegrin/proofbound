#!/usr/bin/env python3
"""The external check on the artifact an implementer actually delivered.

Three failures this exists to prevent, each of which has happened somewhere in this repository or
was found by inspecting code that was about to:

* **Checking something other than the delivered bytes.** The file is loaded by its *resolved path*
  through an explicit spec, never by module name, and its path and sha256 are recorded in the
  result. An installed package, a cached `__pycache__` entry or a reference implementation sitting
  on `sys.path` cannot be graded by accident.
* **Grading the model and calling it the API.** `_obligations.check_implementation` converts a
  result with `list(...)`, so a generator or a tuple satisfies every ordering obligation while
  `RQ-impl` AC-001 asks for a list. Enumeration over a model is not exhaustive over a public API,
  so the API is checked separately and explicitly.
* **Rewarding resemblance.** Only what the implementer's contract states is checked. A sound
  implementation using a different algorithm must pass, and `validate()` proves that on a
  structurally different one rather than asserting it.

**Submitted code runs in a subprocess under a time bound**, because a delivered artifact may hang,
crash or exhaust memory, and a checker that dies with it produces no verdict. Three outcomes stay
distinct: the artifact failed, the artifact did not terminate, and *the checker itself* broke. The
last is never reported as an implementation failure.

    python3 evals/authority_slice/_checker.py --artifact <dispatch.py> [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _obligations as oracle          # noqa: E402

#: Wall-clock seconds the delivered artifact gets for the whole declared domain. The reference
#: implementation does 363 sequences in well under a second; this is slack, not a tuning parameter.
PROBE_TIMEOUT_SECONDS = 60

#: A `(key, n)` item may be a 2-tuple or a 2-list. The contract's notation is a pair, and
#: rejecting one spelling of a pair would grade the delivery against a preferred style rather than
#: against what was asked for. The *outer* container is what AC-001 constrains: a list.
PAIR_SHAPES = ("tuple[2]", "list[2]")

PASS = "pass"
FAIL = "fail"
CHECKER_ERROR = "checker-error"


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# -- the probe, which runs in its own process ----------------------------------------------------

PROBE = r'''
import importlib.util, json, sys

artifact, domain_json = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("pb_delivered_artifact", artifact)
if spec is None or spec.loader is None:
    print(json.dumps({"loaded": False, "why": "no import spec for the artifact path"}))
    raise SystemExit(0)
module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(module)
except BaseException as exc:                     # noqa: BLE001 - reported, never raised onward
    print(json.dumps({"loaded": False, "why": f"import raised {type(exc).__name__}: {exc}"}))
    raise SystemExit(0)

fn = getattr(module, "dispatch", None)
if fn is None or not callable(fn):
    print(json.dumps({"loaded": True, "callable": False,
                      "why": "the module defines no callable `dispatch`",
                      "defines": sorted(n for n in vars(module) if not n.startswith("_"))}))
    raise SystemExit(0)

results, errors = [], []
for arrivals in json.loads(domain_json):
    try:
        returned = fn(list(arrivals))
    except BaseException as exc:                 # noqa: BLE001
        errors.append({"arrivals": arrivals, "raised": f"{type(exc).__name__}: {exc}"})
        continue
    # The exact returned object is described before anything coerces it: the type is part of what
    # the contract asks for, and `list(...)` would erase the difference.
    shape = {"type": type(returned).__name__, "is_list": type(returned) is list}
    try:
        items = list(returned)
    except BaseException as exc:                 # noqa: BLE001
        errors.append({"arrivals": arrivals, "raised": f"not iterable: {type(exc).__name__}: {exc}"})
        continue
    shape["items"] = [list(i) if isinstance(i, (list, tuple)) else i for i in items]
    shape["item_types"] = sorted({type(i).__name__ for i in items})
    shape["element_shapes"] = sorted({
        f"{type(i).__name__}[{len(i)}]" if isinstance(i, (list, tuple)) else type(i).__name__
        for i in items})
    results.append({"arrivals": arrivals, **shape})
print(json.dumps({"loaded": True, "callable": True, "results": results, "errors": errors}))
'''


def _run_probe(artifact: Path, sequences: "list[list[str]]",
               timeout: int) -> "tuple[dict[str, Any] | None, dict[str, Any] | None]":
    """Returns (observation, failure). Exactly one is not None."""
    try:
        done = subprocess.run(
            [sys.executable, "-I", "-c", PROBE, str(artifact), json.dumps(sequences)],
            capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return None, {"verdict": FAIL, "code": "does-not-terminate",
                      "reason": f"the artifact did not complete the declared domain within "
                                f"{timeout}s"}
    except OSError as exc:
        return None, {"verdict": CHECKER_ERROR, "code": "probe-not-startable",
                      "reason": f"{type(exc).__name__}: {exc}"}
    if not done.stdout.strip():
        return None, {"verdict": CHECKER_ERROR, "code": "probe-produced-nothing",
                      "reason": (done.stderr or "").strip()[-600:] or "no output, no error"}
    try:
        return json.loads(done.stdout), None
    except ValueError as exc:
        return None, {"verdict": CHECKER_ERROR, "code": "probe-output-unreadable",
                      "reason": f"{exc}; stderr: {(done.stderr or '').strip()[-300:]}"}


# -- the checks ----------------------------------------------------------------------------------

def check_delivered(artifact: "str | Path", *, model: "dict[str, Any] | None" = None,
                    timeout: int = PROBE_TIMEOUT_SECONDS) -> "dict[str, Any]":
    """Check the delivered artifact against what `RQ-impl` actually asks for.

    `AC-001` is the public API: a callable `dispatch(arrivals)` returning a **list** of `(key, n)`
    items. `AC-002` is the ordering behaviour over the requirements' declared domain. `AC-003`
    (scope) is a property of the working tree, not of this file, and is checked by `check_scope`.
    """
    artifact = Path(artifact)
    if model is None:
        model = oracle.parse_model(
            (HERE / "cases" / "coherent-requirements" / "requirements.md").read_text(
                encoding="utf-8"))
    report: "dict[str, Any]" = {
        "artifact": {"path": str(artifact.resolve()) if artifact.exists() else str(artifact),
                     "exists": artifact.is_file()},
        "domain": {"keys": model["keys"], "max_items": model["max_items"]},
        "obligations": dict(model["obligations"]),
        "coverage": ("every arrival sequence the requirements' declared domain admits; the API "
                     "checks are finite probes over those same calls, and say nothing about "
                     "inputs outside the domain"),
        "prose_to_model_judgements": [
            "AC-001's `list of (key, n) items` is read as: the returned object is a list, and each "
            "item is a 2-tuple or 2-list of (str, int)",
            "purity, idempotence and behaviour on malformed input are not stated by the contract "
            "and are not checked",
        ],
        "findings": [],
    }
    if not artifact.is_file():
        return {**report, "verdict": FAIL,
                "findings": [{"code": "artifact-missing", "criterion": "AC-001",
                              "reason": f"no file at {artifact}"}]}
    report["artifact"]["sha256"] = digest(artifact)
    report["artifact"]["bytes"] = artifact.stat().st_size

    sequences = oracle.domain(model)
    report["domain"]["sequences"] = len(sequences)
    observed, failure = _run_probe(artifact, sequences, timeout)
    if failure is not None:
        return {**report, "verdict": failure["verdict"],
                "findings": [{"code": failure["code"], "criterion": "AC-001",
                              "reason": failure["reason"]}]}

    findings: "list[dict[str, Any]]" = []
    if not observed.get("loaded"):
        return {**report, "verdict": FAIL,
                "findings": [{"code": "artifact-not-importable", "criterion": "AC-001",
                              "reason": observed.get("why", "")}]}
    if not observed.get("callable"):
        return {**report, "verdict": FAIL,
                "findings": [{"code": "no-dispatch-callable", "criterion": "AC-001",
                              "reason": observed.get("why", ""),
                              "defines": observed.get("defines")}]}

    for error in observed.get("errors", [])[:4]:
        findings.append({"code": "raised", "criterion": "AC-002",
                         "reason": error["raised"], "arrivals": error["arrivals"]})

    # AC-001, the return type and element shape. Checked on the returned object itself.
    not_lists = [r for r in observed["results"] if not r["is_list"]]
    if not_lists:
        findings.append({
            "code": "return-type", "criterion": "AC-001",
            "reason": f"`dispatch` must return a list; it returned "
                      f"{sorted({r['type'] for r in not_lists})} on "
                      f"{len(not_lists)} of {len(observed['results'])} calls",
            "arrivals": not_lists[0]["arrivals"]})
    bad_elements = [r for r in observed["results"]
                    if any(shape not in PAIR_SHAPES for shape in r["element_shapes"])]
    if bad_elements:
        findings.append({
            "code": "item-shape", "criterion": "AC-001",
            "reason": "each item must be a `(key, n)` pair; observed element shapes "
                      f"{sorted({s for r in bad_elements for s in r['element_shapes']})}",
            "arrivals": bad_elements[0]["arrivals"]})
    bad_types = []
    for r in observed["results"]:
        for item in r["items"]:
            if not (isinstance(item, list) and len(item) == 2
                    and isinstance(item[0], str) and isinstance(item[1], int)
                    and not isinstance(item[1], bool)):
                bad_types.append((r["arrivals"], item))
                break
    if bad_types and not bad_elements:
        findings.append({"code": "item-types", "criterion": "AC-001",
                         "reason": "each item must pair a string key with an integer index; "
                                   f"observed {bad_types[0][1]!r}",
                         "arrivals": bad_types[0][0]})

    # AC-002, the ordering obligations, over the same calls. Only the requirements the implementer
    # received are applied: any order meeting them passes, whatever algorithm produced it.
    violated: "dict[str, dict[str, Any]]" = {}
    for r in observed["results"]:
        if any(shape not in PAIR_SHAPES for shape in r["element_shapes"]):
            continue                                   # already reported as a shape failure
        order = [(item[0], item[1]) for item in r["items"]]
        for rid in oracle.violations(order, r["arrivals"], model["obligations"]):
            entry = violated.setdefault(rid, {"count": 0, "first": r["arrivals"]})
            entry["count"] += 1
    for rid, detail in sorted(violated.items()):
        findings.append({"code": "obligation", "criterion": "AC-002", "requirement": rid,
                         "obligation": model["obligations"][rid],
                         "reason": f"broken on {detail['count']} of {len(sequences)} sequences",
                         "arrivals": detail["first"]})

    report["checked_calls"] = len(observed["results"])
    report["findings"] = findings
    report["verdict"] = PASS if not findings else FAIL
    return report


def check_scope(project: "str | Path", baseline: "dict[str, str]",
                allowed: "tuple[str, ...]" = ("dispatch.py",)) -> "dict[str, Any]":
    """`AC-003`: did anything outside the allowed set move?

    Independent of the attempt's own scope diff on purpose. The launcher's check is evidence the
    run produces about itself; this one is taken by the evaluator from a baseline recorded before
    the work began.
    """
    project = Path(project)
    now = {}
    for path in sorted(project.rglob("*")):
        if not path.is_file() or any(part in {".git", "__pycache__", "DeepSeekAndDestroy"}
                                     for part in path.parts):
            continue
        now[path.relative_to(project).as_posix()] = digest(path)
    changed = sorted(p for p in set(now) | set(baseline)
                     if now.get(p) != baseline.get(p))
    undeclared = [p for p in changed if p not in allowed]
    return {"changed": changed, "allowed": list(allowed), "undeclared": undeclared,
            "verdict": PASS if not undeclared else FAIL,
            "findings": ([] if not undeclared else
                         [{"code": "undeclared-change", "criterion": "AC-003",
                           "reason": f"files outside the allowed set changed: {undeclared}"}])}


def baseline_manifest(project: "str | Path") -> "dict[str, str]":
    """What the project looked like before implementation. Recorded by the evaluator."""
    project = Path(project)
    return {path.relative_to(project).as_posix(): digest(path)
            for path in sorted(project.rglob("*"))
            if path.is_file() and not any(part in {".git", "__pycache__", "DeepSeekAndDestroy"}
                                          for part in path.parts)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a delivered dispatch.py.")
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=PROBE_TIMEOUT_SECONDS)
    args = parser.parse_args()
    report = check_delivered(args.artifact, timeout=args.timeout)
    print(json.dumps(report, indent=2, sort_keys=True))
    return {PASS: 0, FAIL: 1, CHECKER_ERROR: 2}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())

