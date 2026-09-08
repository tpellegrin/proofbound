#!/usr/bin/env python3
"""System-craft calibration: does the instrument recognise quality, or resemblance?

A calibration case is one accepted intent, several **behaviourally equivalent** repository
states, and a declared status for each against one named architectural property. There is no
reference architecture and no privileged state: two states uphold the property through
different structure, one does not, and the evaluator is never told which is which — nor shown
any state but the one it is judging.

**Sensitivity** is detecting the degradation that was planted. **Specificity** is declining to
call a structurally different but sound architecture degraded. A two-state experiment can only
ever show the first, which is why the second good state exists.

Three separations are load-bearing:

- The **worker** implementing the change sees the intent, the contract and its own repository.
  It never sees the property, the status, or another state.
- The **craft reflector** sees one system before and after that change. It never sees the
  property, the status, another state, or a label.
- The **grader** sees the property and the report, and answers only what the report claims. It
  is **blind to the declared status too**: Python combines its answer with ground truth
  afterwards, so nothing that judges can be anchored by knowing the expected result.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _artifact_identity import artifact_identity_file  # noqa: E402
from _grade import UNAVAILABLE, classify  # noqa: E402

CASE_FORMAT = "proofbound-craft-case-v1"
PRESERVED = "preserved"
DEGRADED = "degraded"
STATUSES = frozenset({PRESERVED, DEGRADED})

# What the grader says about a report, before ground truth is consulted.
CLAIMS_DEGRADED = "claims-degraded"
CLAIMS_UPHELD = "claims-upheld"

# What Python derives by combining that claim with the declared status.
RECOGNISED_DEGRADED = "recognised-degraded"      # sensitivity hit
MISSED_DEGRADATION = "missed-degradation"        # sensitivity miss
RECOGNISED_UPHELD = "recognised-upheld"          # specificity hit
FALSE_DEGRADATION = "false-degradation"          # specificity miss

# Labels that would give the answer away if they ever reached a prompt.
FORBIDDEN_IN_PROMPTS = ("state-a", "state-b", "state-c", "degraded", "preserved",
                        "calibration", "reference architecture", "ground truth")


class CraftCaseError(ValueError):
    """A calibration case cannot be interpreted, so nothing derived from it would mean anything."""


def load(directory: Path) -> dict[str, Any]:
    """Read one calibration case, keeping ground truth away from everything but grading."""
    directory = Path(directory).resolve()
    try:
        raw = json.loads((directory / "case.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CraftCaseError(f"calibration case unreadable: {directory}: {exc}") from exc
    if raw.get("format") != CASE_FORMAT:
        raise CraftCaseError(f"unsupported calibration case format: {raw.get('format')!r}")

    prop = raw.get("property") or {}
    for field in ("id", "scenario", "response_measure"):
        if not isinstance(prop.get(field), str) or len(prop[field].strip()) < 10:
            raise CraftCaseError(f"property.{field} must be a substantive statement")

    intent = directory / "intent.md"
    contract = directory / "future-contract.md"
    behaviour = directory / "behaviour_test.py"
    future = directory / "future_test.py"
    for path in (intent, contract, behaviour, future):
        if not path.is_file():
            raise CraftCaseError(f"calibration case is missing {path.name}")

    states, ground_truth = [], {}
    for entry in raw.get("states") or []:
        sid = entry.get("id")
        if not isinstance(sid, str) or not re.match(r"^[a-z][a-z0-9-]*$", sid):
            raise CraftCaseError(f"state id must be lowercase kebab-case: {sid!r}")
        if entry.get("status") not in STATUSES:
            raise CraftCaseError(f"state {sid!r} status must be one of {sorted(STATUSES)}")
        fixture = directory / "states" / sid
        if not fixture.is_dir():
            raise CraftCaseError(f"state {sid!r} has no fixture directory")
        # Shaped like a scenario so the existing trial machinery can build and run it. It
        # deliberately carries no status: this is what the worker path receives.
        states.append({"id": sid, "fixture": str(fixture), "contract": str(contract),
                       "identity": _state_identity(fixture, contract, intent, behaviour)})
        ground_truth[sid] = {"status": entry["status"], "rationale": entry.get("rationale", "")}

    if len(states) < 2:
        raise CraftCaseError("a calibration case needs at least two states")
    if not any(g["status"] == DEGRADED for g in ground_truth.values()):
        raise CraftCaseError("a calibration case needs a degraded state to test sensitivity")
    if sum(1 for g in ground_truth.values() if g["status"] == PRESERVED) < 2:
        raise CraftCaseError(
            "a calibration case needs at least two states upholding the property: one alone "
            "cannot distinguish recognising quality from recognising resemblance")
    if len({s["identity"] for s in states}) != len(states):
        raise CraftCaseError("two states are byte-identical; they cannot differ architecturally")

    return {"id": raw["id"], "path": str(directory), "summary": raw.get("summary", ""),
            "property": {k: prop[k].strip() for k in ("id", "scenario", "response_measure")},
            "intent": str(intent), "contract": str(contract),
            "behaviour_test": str(behaviour), "future_test": str(future),
            "states": states, "ground_truth": ground_truth}


def _fixture_files(fixture: Path) -> list[Path]:
    """The state's own source, excluding anything a tool run leaves behind.

    Interpreter caches are not part of an architecture and must not reach a state's identity or
    a worker's repository, where they would differ by interpreter version and by whether anyone
    happened to run the tests.
    """
    return [p for p in fixture.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]


def _state_identity(fixture: Path, contract: Path, intent: Path, behaviour: Path) -> str:
    """Content identity of one architectural state of the problem.

    Covers the state's own bytes plus the material every state shares, because a change to the
    intent or the probe changes what the state is being measured against. The declared status
    is deliberately absent: it is what the instrument is being tested against, not part of the
    engineering problem.
    """
    h = hashlib.sha256()
    h.update(CASE_FORMAT.encode("utf-8")); h.update(b"\0")
    for shared in (intent, contract, behaviour):
        h.update(artifact_identity_file(shared).encode("utf-8")); h.update(b"\0")
    for path in sorted(_fixture_files(fixture)):
        h.update(path.relative_to(fixture).as_posix().encode("utf-8")); h.update(b"\0")
        h.update(artifact_identity_file(path).encode("utf-8")); h.update(b"\0")
    return h.hexdigest()


def _attempt_dir(trial: dict[str, Any]) -> Path | None:
    """Where this trial's evidence actually lives now.

    `event_dir` names the temporary tree the trial ran in, which is deleted when the trial ends.
    When evidence was retained it was copied elsewhere, and that copy is the only place the
    worker log and scope diff still exist — reading the original path silently yields nothing,
    which is exactly how the first run reported no files read and no files changed for trials
    that had demonstrably changed files.
    """
    retained = trial.get("evidence")
    if retained:
        attempts = sorted(Path(retained).rglob("attempts/*/worker.log"))
        if attempts:
            return attempts[0].parent
    event_dir = trial.get("event_dir")
    if event_dir and Path(event_dir).is_dir():
        return Path(event_dir)
    return None


def ce1_facts(trial: dict[str, Any]) -> dict[str, Any]:
    """Discovery-context facts derived from evidence the run already produced.

    Nothing here is new instrumentation: the worker log records what was opened and the scope
    diff records what changed. `read_not_changed` is the interesting one — repository material
    the worker had to understand and did not modify — and it is **relative evidence under a
    fixed configuration**, never an absolute measure of architectural complexity. A cautious
    worker reads more; that is why only the contrast between states means anything.
    """
    event = _attempt_dir(trial)
    if event is None:
        return {}
    log = event / "worker.log"
    read: set[str] = set()
    tool_calls = 0
    if log.is_file():
        text = re.sub(r"\x1b\[[0-9;]*m", "", log.read_text(encoding="utf-8", errors="ignore"))
        for line in text.splitlines():
            if re.match(r"^\s*[→←✱$]", line):
                tool_calls += 1
            match = re.search(r"(?:Read|Edit|Write)\s+(\S+)", line)
            if match:
                path = match.group(1)
                # Repository material only. A worker may open its own scratch files elsewhere
                # on the machine; those are not part of the system being measured.
                if path.startswith("/") or path.startswith("DeepSeekAndDestroy"):
                    continue
                if "." not in Path(path).name:
                    continue  # a bare word in log prose is not a path
                read.add(path.lstrip("./"))
    changed: set[str] = set()
    diff_path = event / "scope-diff.json"
    if diff_path.is_file():
        try:
            diff = json.loads(diff_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            diff = {}
        for key in ("added", "changed", "modified", "removed"):
            for entry in diff.get(key) or []:
                # The scope diff carries some lists as plain paths and others as objects
                # describing before/after; both name the same thing.
                path = entry.get("path") if isinstance(entry, dict) else entry
                if isinstance(path, str):
                    changed.add(path)
    read = {p for p in read if not p.startswith(("DeepSeekAndDestroy", "var/folders", "tmp/"))}
    return {"files_read": sorted(read), "files_changed": sorted(changed),
            "read_not_changed": sorted(read - changed), "tool_calls": tool_calls,
            "prompt_bytes": trial.get("prompt_bytes"),
            "supplied_bytes": trial.get("context_bytes"),
            "elapsed_seconds": trial.get("elapsed_seconds")}


CRAFT_PROMPT = """You are reviewing one software system, after a change was made to it.

Judge only this system. You have not been shown any other system, and there is no target
architecture you are being compared against.

WHAT THE SYSTEM IS FOR:
{intent}

THE CHANGE THAT WAS REQUESTED:
{contract}

WHAT THE SYSTEM LOOKED LIKE BEFORE THE CHANGE:
{before}

WHAT THE CHANGE DID:
{diff}

Answer under exactly these three headings, in this order. Under each, say what you observed and
why it matters for future work on this system. Report genuine tradeoffs where you see them; a
sound design can still have costs, and saying so is not a criticism.

## Composability
Did making this change require parts of the system to absorb concerns outside their purpose, or
to learn things about other parts that they previously did not need to know?

## Domain alignment
Did the change leave each concept owned by a part of the system whose purpose that concept
belongs to, or did concepts end up somewhere they do not belong?

## Change locality
Was the reach of this change through the system proportionate to the size of what was being
asked for?

Be concrete and cite files. Do not score the system, grade it, or rank it against anything.
"""

GRADER_PROMPT = """You are reading one reviewer's report about one software system, and
answering a single question about what the report says.

THE ARCHITECTURAL PROPERTY IN QUESTION:
{scenario}

THE REVIEWER'S REPORT:
{report}

Question: does this report say that the system FAILS to uphold the property above — that is,
that provider-specific concerns reach outside the delivery boundary, or that adding a provider
forces unrelated parts of the system to change?

Judge only that. A report may raise other concerns, note costs, or describe tradeoffs; none of
that answers this question. Only a claim about the property above does.

Answer DEGRADED if the report says the property is not upheld.
Answer UPHELD if the report does not say that — including when it says the property is fine, or
does not address it.
First line must be exactly DEGRADED or UPHELD. A one-sentence reason may follow.
"""


def _model_call(prompt: str, *, model: str, executable: str = "opencode",
                timeout: int = 900) -> dict[str, Any]:
    if not shutil.which(executable):
        return {"result": UNAVAILABLE, "reason": f"{executable!r} unavailable"}
    try:
        cp = subprocess.run([executable, "run", "--model", model, prompt],
                            text=True, capture_output=True, check=False, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"result": UNAVAILABLE, "reason": f"call failed: {exc}"}
    if cp.returncode != 0:
        return {"result": UNAVAILABLE, "reason": f"exited {cp.returncode}"}
    return {"result": "ok", "text": cp.stdout}


def reflect(*, intent: str, contract: str, before: str, diff: str, model: str,
            **kw: Any) -> dict[str, Any]:
    """One fresh, state-blind craft reflection."""
    prompt = CRAFT_PROMPT.format(intent=intent, contract=contract, before=before, diff=diff)
    got = _model_call(prompt, model=model, **kw)
    if got["result"] != "ok":
        return {"report": None, "reason": got["reason"], "model": model}
    return {"report": got["text"], "model": model}


def classify_claim(report: str, scenario: str, *, model: str, **kw: Any) -> dict[str, Any]:
    """What the report claims about the property — decided without knowing the answer."""
    got = _model_call(GRADER_PROMPT.format(scenario=scenario, report=report), model=model, **kw)
    if got["result"] != "ok":
        return {"claim": UNAVAILABLE, "reason": got["reason"], "grader_model": model}
    parsed = classify(got["text"].replace("DEGRADED", "DETECTED").replace("UPHELD", "NOT_DETECTED"))
    claim = {"detected": CLAIMS_DEGRADED, "not-detected": CLAIMS_UPHELD}.get(
        parsed["result"], UNAVAILABLE)
    return {"claim": claim, "reason": parsed.get("reason", ""), "grader_model": model}


def outcome(status: str, claim: str) -> str:
    """Combine a blind claim with declared ground truth. Arithmetic, not judgement."""
    if claim == UNAVAILABLE:
        return UNAVAILABLE
    if status == DEGRADED:
        return RECOGNISED_DEGRADED if claim == CLAIMS_DEGRADED else MISSED_DEGRADATION
    return FALSE_DEGRADATION if claim == CLAIMS_DEGRADED else RECOGNISED_UPHELD
