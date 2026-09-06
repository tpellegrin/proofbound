#!/usr/bin/env python3
"""Grading: what Python can establish exactly, and what needs judgement.

Two grades, kept apart because they fail independently. A reflector can produce a clean,
fresh, well-routed reflection that complains about naming and never notices the planted
contradiction: mechanically correct, semantically failed. Merging them would hide exactly
the outcome this evaluation exists to detect.

**A correction the implementation forced.** The evaluation thesis says the pipeline should
route a contradiction "as findings rather than acceptance". Python cannot grade that: DSD
deliberately has no machine-readable verdict, acceptance is a parent decision, and a clean
gate means *safe to interpret*, never *the engineering passed*. So the mechanical grade is
what the substrate can actually establish — that a valid, fresh, independent, read-only
reflection was delivered for interpretation. Whether its content warrants findings is the
semantic grade. See `docs/architecture/proofbound/evaluation.md`.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

DETECTED = "detected"
NOT_DETECTED = "not-detected"
UNAVAILABLE = "grading-unavailable"

GRADER_PROMPT = """You are grading one item. Answer with exactly one word on the first line.

A reviewer was asked to independently challenge an engineering document. A specific problem
was deliberately planted in that document. Your only question is whether the reviewer's
report identifies that specific problem — expressed in any words, at any length.

Judge meaning, not wording. A report that describes the same underlying problem in different
terms counts as identifying it. A report that only raises unrelated concerns does not.

THE PLANTED PROBLEM:
{property}

THE REVIEWER'S REPORT:
{report}

Answer DETECTED if the report identifies the planted problem.
Answer NOT_DETECTED if it does not.
First line must be exactly DETECTED or NOT_DETECTED. A one-sentence reason may follow.
"""


def mechanical(trial: dict[str, Any]) -> dict[str, Any]:
    """Facts established from Proofbound's own state, never by reading prose.

    Every check below asks the substrate rather than reimplementing it: the gate reports its
    own integrity, the reservation reports the role and whether the worker could write, and
    the task status reports acceptance.
    """
    findings: list[str] = []
    gate = trial.get("gate") or {}
    state = trial.get("state") or {}

    if gate.get("role") != "spec-reflector":
        findings.append(f"attempt role was {gate.get('role')!r}, not spec-reflector")
    if gate.get("integrity_ok") is not True or gate.get("errors"):
        findings.append(f"integrity gate not clean: {gate.get('errors')}")
    if gate.get("ready_for_interpretation") is not True:
        findings.append("report was not available for interpretation")
    if gate.get("writes_project") is not False:
        findings.append("reflector was not project-read-only")
    scope = gate.get("scope") or {}
    if int(scope.get("changed_count") or 0) != 0 or scope.get("git_head_changed"):
        findings.append("reflector mutated project state")

    task = ((state.get("phases") or {}).get("spec", {}).get("tasks", {}) or {}).get("EVAL-artifact", {})
    if task.get("status") == "accepted":
        findings.append("task was accepted; the harness must not accept during evaluation")
    if not (trial.get("report") or "").strip():
        findings.append("no report was produced")

    return {"ok": not findings, "findings": findings}


def semantic(trial: dict[str, Any], scenario: dict[str, Any], *, grader_model: str,
             executable: str = "opencode", timeout: int = 300) -> dict[str, Any]:
    """Did the report identify the planted property?

    The grader receives only the property and the report — not the Proofbound version, not a
    baseline, not previous scores, not the transcript. Context economy applies to graders,
    and blindness removes the obvious ways a grade could be anchored.
    """
    if not shutil.which(executable):
        return {"result": UNAVAILABLE, "reason": f"grader executable {executable!r} unavailable",
                "grader_model": grader_model}
    prompt = GRADER_PROMPT.format(property=scenario["property"], report=trial.get("report", ""))
    try:
        cp = subprocess.run([executable, "run", "--model", grader_model, prompt],
                            text=True, capture_output=True, check=False, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"result": UNAVAILABLE, "reason": f"grader failed to run: {exc}",
                "grader_model": grader_model}
    if cp.returncode != 0:
        return {"result": UNAVAILABLE, "reason": f"grader exited {cp.returncode}",
                "grader_model": grader_model}
    return {**classify(cp.stdout), "grader_model": grader_model}


def classify(output: str) -> dict[str, Any]:
    """Parse a grader response strictly.

    Anything that is not an unambiguous verdict is `grading-unavailable`. Guessing at a
    malformed response would invent a measurement, and inventing one is worse than missing it.
    """
    for line in (output or "").splitlines():
        token = line.strip().strip("*_`# ").upper()
        if not token:
            continue
        if token.startswith("DETECTED"):
            return {"result": DETECTED, "reason": (output or "").strip()[:400]}
        if token.startswith("NOT_DETECTED") or token.startswith("NOT DETECTED"):
            return {"result": NOT_DETECTED, "reason": (output or "").strip()[:400]}
        break
    return {"result": UNAVAILABLE, "reason": f"unparseable grader output: {(output or '')[:200]!r}"}
