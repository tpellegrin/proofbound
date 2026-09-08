#!/usr/bin/env python3
"""Repeated measurement of the craft instrument, holding the measurand exactly fixed.

Calibration V2 established something more basic than its own result: on thirteen implementations
re-measured with byte-identical inputs, the instrument agreed with its earlier judgement nine
times and disagreed four. A treatment effect smaller than that is uninterpretable, so before any
further calibration the instrument has to be measured against itself.

Two things can move while the architecture stands still — the reflector's reading of it, and the
grader's reading of the reflector. This module keeps them apart. Layer G repeats the grader over
frozen report bytes; layer R repeats the reflector over a frozen implementation and grades each
result once. Neither layer decides whether an answer is correct: that is not a question repeated
measurement can answer, and treating agreement as correctness is the specific mistake this
milestone exists to avoid.

Every repeat is a separate process with no session continuation, so no repeat can see another —
repeated measurement, not deliberation.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

GRADED = "graded"
PARSE_FAILURE = "parse-failure"
CALL_FAILURE = "call-failure"

REFLECTED = "reflected"
REFLECTION_FAILURE = "reflection-failure"

GRADER_LAYER = "G"
REFLECTOR_LAYER = "R"


class RepeatConfigError(Exception):
    """Raised when a run would mix measurements taken under different frozen configurations."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def frozen_identity(config: dict[str, Any]) -> str:
    """One hash over everything that must not vary between repeats of a series.

    Resuming an interrupted series is safe here in a way it was not for the paired routing
    matrix: a repeat is independent of every other repeat, so appending the ones that never ran
    changes nothing about the ones that did. It is safe **only** while the configuration is
    identical, which is what this hash establishes — a resume across a different Proofbound SHA,
    model, prompt, anchor set or N is a spliced experiment, and is refused rather than recorded.
    """
    return hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _already_done(measurements: list[dict], key: tuple[str, int]) -> bool:
    return any((m["item"], m["repeat"]) == key for m in measurements)


def load_series(out: Path, config: dict[str, Any]) -> list[dict]:
    """Measurements already recorded for exactly this configuration, or none.

    A record written under a different configuration is never extended and never silently
    replaced: the caller is told, and decides.
    """
    if not out.is_file():
        return []
    try:
        prior = json.loads(out.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepeatConfigError(f"existing record at {out} is unreadable: {exc}") from exc
    if prior.get("frozen_identity") != frozen_identity(config):
        raise RepeatConfigError(
            f"{out} holds measurements from a different frozen configuration; "
            "resuming would splice two experiments")
    return prior.get("measurements") or []


def write_series(out: Path, config: dict[str, Any], measurements: list[dict],
                 extra: dict[str, Any] | None = None) -> None:
    """Persist after every single measurement, atomically.

    One repeat is one paid model call. A host timeout took an entire paired matrix during the
    routing control, and the repair there was checkpointing; here the same discipline also makes
    resume meaningful, because each recorded repeat stands alone.
    """
    record = {"frozen_identity": frozen_identity(config), **config,
              **(extra or {}), "measurements": measurements}
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".partial")
    tmp.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(out)


def grade_once(report: str, scenario: str, *, status: str, grader: Callable[..., dict],
               outcome: Callable[[str, str], str], unavailable: str,
               **kw: Any) -> dict[str, Any]:
    """One independent grading of fixed text, recorded with its failure mode intact.

    A grader that could not be reached and a grader whose answer could not be parsed are both
    missing measurements, and neither is a semantic disagreement. Collapsing them into an
    outcome would manufacture exactly the kind of result this experiment exists to question.
    """
    started = time.monotonic()
    got = grader(report, scenario, **kw)
    elapsed = round(time.monotonic() - started, 3)
    claim = got.get("claim")
    if claim == unavailable:
        reason = got.get("reason") or ""
        kind = PARSE_FAILURE if "unparseable" in reason else CALL_FAILURE
        return {"status": kind, "claim": None, "outcome": None,
                "reason": reason[:300], "seconds": elapsed}
    return {"status": GRADED, "claim": claim, "outcome": outcome(status, claim),
            "reason": (got.get("reason") or "")[:300], "seconds": elapsed}


def reflect_once(*, reflector: Callable[..., dict], **kw: Any) -> dict[str, Any]:
    """One independent craft reflection over fixed architectural evidence."""
    started = time.monotonic()
    got = reflector(**kw)
    elapsed = round(time.monotonic() - started, 3)
    report = got.get("report")
    if not report:
        return {"status": REFLECTION_FAILURE, "report": None,
                "reason": (got.get("reason") or "")[:300], "seconds": elapsed}
    return {"status": REFLECTED, "report": report, "report_sha256": sha256_text(report),
            "report_bytes": len(report.encode("utf-8")), "seconds": elapsed}


def redact(measurements: list[dict]) -> list[dict]:
    """The durable form of a measurement: what it was, never what it said.

    Raw reflector text is kept locally for human coding and stays out of the committed record,
    exactly as the calibration and routing records do. The hash is what makes the local copy
    falsifiable.
    """
    out = []
    for m in measurements:
        out.append({k: v for k, v in m.items() if k not in ("report", "reason")})
    return out


def distribution(measurements: list[dict], item: str) -> dict[str, Any]:
    """Exact per-item outcome counts. No score, no rank, no aggregate quality number.

    The dispersion is the result, so this reports every distinct outcome and how often it
    occurred rather than a single summary. `modal_share` is over graded measurements only:
    missing measurements are missing, and dividing by them would quietly convert an
    infrastructure failure into semantic disagreement.
    """
    mine = [m for m in measurements if m["item"] == item]
    graded = [m for m in mine if m.get("status") == GRADED and m.get("outcome")]
    counts: dict[str, int] = {}
    for m in graded:
        counts[m["outcome"]] = counts.get(m["outcome"], 0) + 1
    modal = max(counts, key=lambda k: (counts[k], k)) if counts else None
    return {
        "item": item,
        "attempted": len(mine),
        "graded": len(graded),
        "parse_failures": sum(1 for m in mine if m.get("status") == PARSE_FAILURE),
        "call_failures": sum(1 for m in mine if m.get("status") == CALL_FAILURE),
        "reflection_failures": sum(1 for m in mine if m.get("status") == REFLECTION_FAILURE),
        "counts": counts,
        "distinct_outcomes": len(counts),
        "modal_outcome": modal,
        "modal_share": (round(counts[modal] / len(graded), 4) if modal else None),
        "unanimous": len(counts) == 1 and len(graded) > 1,
        "order": [m.get("outcome") for m in sorted(mine, key=lambda m: m["repeat"])],
    }
