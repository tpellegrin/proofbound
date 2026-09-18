#!/usr/bin/env python3
"""Execution authority: which engineering candidate governs an implementation task.

M2C-C is deliberately thin, and that thinness is the result rather than a shortcut. Every
fact it needs was already shipped:

* `_freeze.current_candidate` derives what the project currently produces;
* `_consistency.lookup` says whether that candidate was independently challenged;
* `_consistency.check_provenance` says whether the challenge's evidence still agrees;
* the inherited immutable-contract machinery binds a task to whatever its contract says.

So this module composes, and introduces **no new identity**. A contract naming `C` already has a
different hash from one naming `C2`, which is why a review of one can never be accepted for the
other — no nonce, no reservation field, no `current_freeze` pointer.

It does now write one piece of state, and only because an invariant consumes it: the admission
record (A6.10). See `ADMISSION_FORMAT` below for what it is and why it lives where it does.

Three responsibilities:

**Authorization** answers *may implementation work begin against this candidate now?* It is
a launch-time question. Once a task is authorized and its immutable contract written, that
contract is the task's engineering authority for the rest of its life — through
implementation, review, the fixer loop and acceptance. Later movement of engineering intent
does not silently rebind running work, and nothing here rechecks currentness at acceptance:
doing so would either discard correct work or require deciding whether the newer candidate
*mattered* to the task, which is applicability inference and is deferred.

**Admission** is the transition that *acts* on that answer: it authorizes and binds a
candidate-bound contract to its task in one atomic state write, so a launch can tell an admitted
task from one whose contract merely names a candidate. Authorization alone confers nothing.

**Reporting** answers *which candidate governs each task in this run?* Divergence is
information, not a failure: engineering intent legitimately evolves mid-run, and there is no
phase barrier here — inherited DSD has no mechanical phase close, and an adversarial test
exists specifically to stop gating state accumulating in phases.

**Known boundary.** Task contracts and acceptance both live inside the run tree, so this is
execution binding, not durable implementation provenance. After the run tree is deleted no
project file records that an accepted task was governed by `C`.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _consistency import ConsistencyError, check_provenance, lookup
from _contract import declared_candidate
from _freeze import FreezeError, current_candidate, freeze_identity

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _finding(code: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "reason": reason, **extra}


def authorize(*, candidate: str, graph_path: Path, ledger_path: Path, project_root: Path,
              consistency_dir: Path, run_root: Path | None = None) -> dict[str, Any]:
    """May implementation work be authorized against this exact candidate, now?

    Composes three shipped facts. Returns findings rather than a bare boolean so a refusal
    names its mechanical reason. This is a parent-side guard, not a gate: nothing stops a
    determined operator hand-writing a contract, and `P5` is explicit that integrity is not
    authority. The guard exists so the normal path is the correct one.
    """
    findings: list[dict[str, Any]] = []
    provenance = "unavailable"

    if not isinstance(candidate, str) or not _HEX64.match(candidate):
        return {"authorized": False, "candidate": candidate, "provenance": provenance,
                "findings": [_finding("malformed-candidate",
                                      f"not a lowercase hex SHA-256 candidate identity: "
                                      f"{candidate!r}")]}

    # 1. Does the project currently produce this contract at all?
    derived: str | None = None
    try:
        _graph, _ledger, current = current_candidate(graph_path, ledger_path, project_root)
        derived = freeze_identity(current)
    except (FreezeError, ValueError) as exc:
        findings.append(_finding(
            "candidate-not-derivable",
            f"the project does not currently produce a contract candidate: {exc}"))
    else:
        if derived != candidate:
            findings.append(_finding(
                "candidate-not-current",
                f"the project currently produces {derived[:12]}, not {candidate[:12]}; a "
                "historical candidate does not authorize new implementation work",
                current=derived))

    # 2. Was it independently challenged as a whole?
    record = None
    try:
        found = lookup(consistency_dir, candidate)
        if found["state"] == "absent":
            findings.append(_finding(
                "no-consistency-acceptance",
                "no accepted aggregate consistency reflection is recorded for this candidate"))
        else:
            record = found["record"]
    except ConsistencyError as exc:
        findings.append(_finding("malformed-consistency-record", str(exc)))

    # 3. Does retained evidence contradict that challenge?
    #
    # `unavailable` authorizes. Execution evidence is expendable by design, so if its
    # absence blocked new work, deleting an old run tree would convert accepted engineering
    # authority into unauthorized authority — making availability into authority and
    # inverting the L3/L4 separation. `contradicted` is different in kind: retained evidence
    # actively disagrees with the durable claim, and building on that would launder a known
    # inconsistency.
    if record is not None:
        try:
            prov = check_provenance(record, run_root)
        except ConsistencyError as exc:
            findings.append(_finding("malformed-consistency-record", str(exc)))
        else:
            provenance = prov["provenance"]
            if provenance == "contradicted":
                findings.append(_finding(
                    "consistency-provenance-contradicted",
                    "retained evidence contradicts the recorded consistency acceptance: "
                    + "; ".join(prov["reasons"])))

    return {"authorized": not findings, "candidate": candidate,
            "current": derived, "provenance": provenance, "findings": findings}


#: The one fact A6.6 said would be needed the moment an invariant consumed it. That invariant now
#: exists: a launch on the guarded path must be able to tell an *admitted* task from a task whose
#: contract merely names a candidate. The record is written into the task's own state entry by the
#: same atomic write that binds the contract, so there is no instant at which a contract is bound
#: and unadmitted, and rebinding drops it.
ADMISSION_FORMAT = "proofbound-implementation-admission-v1"


def build_admission(*, candidate: str, contract_path: Path, contract_sha256: str,
                    project_root: Path, authorization: dict[str, Any], graph_path: Path,
                    ledger_path: Path, consistency_dir: Path) -> dict[str, Any]:
    """The admission fact, bound to exactly what was checked."""
    return {
        "format": ADMISSION_FORMAT,
        "candidate": candidate,
        "contract_path": str(contract_path),
        "contract_sha256": contract_sha256,
        "project_root": str(project_root),
        "admitted_at": datetime.now(tz=timezone.utc).isoformat(),
        "authority": {"graph": str(graph_path), "ledger": str(ledger_path),
                      "consistency": str(consistency_dir)},
        "authorization": {"provenance": authorization.get("provenance"),
                          "current": authorization.get("current")},
    }


def admission_findings(admission: Any, *, candidate: str, contract_sha256: str,
                       project_root: Path) -> list[dict[str, Any]]:
    """Why a recorded admission does not qualify this launch — empty when it does.

    Every field is compared rather than trusted. An admission is a fact about one task's exact
    contract revision, candidate and project; it must not carry over to another task, a different
    revision, a different candidate, or a run tree copied somewhere else.

    Note what is deliberately *not* rechecked: whether the candidate is still the one the project
    currently derives. Authority is fixed at admission (A6.4). A task admitted under `C1` keeps
    working when the project moves to `C2`; only a *new* admission would have to pass against the
    newer state.
    """
    if not isinstance(admission, dict):
        return [_finding("not-admitted",
                         "this contract is candidate-bound execution and the task carries no "
                         "admission record; admit it with `pb_execution.py admit`")]
    if admission.get("format") != ADMISSION_FORMAT:
        return [_finding("malformed-admission",
                         f"unexpected admission format: {admission.get('format')!r}")]
    findings: list[dict[str, Any]] = []
    if admission.get("candidate") != candidate:
        findings.append(_finding(
            "admission-candidate-mismatch",
            f"the task was admitted for candidate {str(admission.get('candidate'))[:12]}, and this "
            f"contract names {candidate[:12]}"))
    if admission.get("contract_sha256") != contract_sha256:
        findings.append(_finding(
            "admission-contract-mismatch",
            "the admission was granted against a different contract revision; a new revision needs "
            "a new admission"))
    try:
        same_project = Path(str(admission.get("project_root"))).resolve() == project_root.resolve()
    except OSError:                                          # pragma: no cover - unresolvable path
        same_project = False
    if not same_project:
        findings.append(_finding(
            "admission-project-mismatch",
            f"the admission was granted for project {admission.get('project_root')!r}, not "
            f"{str(project_root)!r}"))
    return findings


def bound_candidates(run_root: Path) -> dict[str, Any]:
    """Which engineering candidate governs each task in this run.

    Derived entirely from the immutable task contracts the run already holds — nothing is
    stored, and no task is classified as failed for naming a different candidate than its
    neighbour. A task with no declared candidate is an inherited task that never went
    through Proofbound authorization, which is reported as `null` rather than as an error.
    """
    run_root = Path(run_root).resolve()
    try:
        state = json.loads((run_root / "state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"run state unreadable: {run_root / 'state.json'}: {exc}") from exc

    tasks: list[dict[str, Any]] = []
    for phase_id, phase in sorted((state.get("phases") or {}).items()):
        for task_id, task in sorted((phase.get("tasks") or {}).items()):
            if not isinstance(task, dict):
                continue
            entry: dict[str, Any] = {"task": f"{phase_id}/{task_id}",
                                     "status": task.get("status"), "candidate": None}
            binding = task.get("current_contract") or {}
            contract = Path(binding.get("path") or "")
            if contract.is_file():
                try:
                    entry["candidate"] = declared_candidate(
                        contract.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    entry["candidate"] = None
                    entry["note"] = f"contract candidate unreadable: {exc}"
            else:
                entry["note"] = "current contract is not present in this run tree"
            tasks.append(entry)

    named = sorted({t["candidate"] for t in tasks if t["candidate"]})
    return {"run_root": str(run_root), "tasks": tasks, "candidates": named,
            "divergent": len(named) > 1}
