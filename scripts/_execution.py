#!/usr/bin/env python3
"""Execution authority: which engineering candidate governs an implementation task.

M2C-C is deliberately thin, and that thinness is the result rather than a shortcut. Every
fact it needs was already shipped:

* `_freeze.current_candidate` derives what the project currently produces;
* `_consistency.lookup` says whether that candidate was independently challenged;
* `_consistency.check_provenance` says whether the challenge's evidence still agrees;
* the inherited immutable-contract machinery binds a task to whatever its contract says.

So this module composes, and introduces **no new identity and no new persistent state**. A
contract naming `C` already has a different hash from one naming `C2`, which is why a
review of one can never be accepted for the other — no nonce, no reservation field, no
`current_freeze` pointer.

Two responsibilities:

**Authorization** answers *may implementation work begin against this candidate now?* It is
a launch-time question. Once a task is authorized and its immutable contract written, that
contract is the task's engineering authority for the rest of its life — through
implementation, review, the fixer loop and acceptance. Later movement of engineering intent
does not silently rebind running work, and nothing here rechecks currentness at acceptance:
doing so would either discard correct work or require deciding whether the newer candidate
*mattered* to the task, which is applicability inference and is deferred.

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
