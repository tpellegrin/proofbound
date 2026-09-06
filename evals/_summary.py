#!/usr/bin/env python3
"""The committed measurement record.

Small, versioned, and interpretable years later without the transcripts it summarizes. Raw
evidence — prompts, worker logs, provider output, scope diffs — stays local: it is large,
provider-specific, and is execution evidence rather than a measurement.

**A metric vector, never a composite.** A pipeline can get more reliable and more expensive
at the same time, and a weighted score would hide precisely that. There is no
`Proofbound Score`, no `winner`, no `approved`, and no automatic regression verdict: this
record reports counts, and whether a difference between two runs matters is a human call.

**Attempted is reported alongside valid.** A suite whose provider failed half the time must
not be able to look like one that genuinely scored 50%.

An evaluation summary is a measurement record. It is *not* engineering provenance: nothing
here participates in artifact validity, candidate identity, consistency acceptance or
execution authorization.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _grade import DETECTED, NOT_DETECTED, UNAVAILABLE
from _trial import HARNESS_FAILURE, SETUP_FAILURE, VALID

SUMMARY_FORMAT = "proofbound-eval-summary-v1"
SUPPORTED_SUMMARY_FORMATS = (SUMMARY_FORMAT,)


class SummaryError(ValueError):
    """A summary cannot be interpreted under the semantics it recorded."""


def _counts(graded: list[dict[str, Any]]) -> dict[str, int]:
    trials = [g["trial"] for g in graded]
    valid = [g for g in graded if g["trial"]["validity"] == VALID]
    return {
        "attempted": len(graded),
        "valid": len(valid),
        "setup_failures": sum(1 for t in trials if t["validity"] == SETUP_FAILURE),
        "harness_failures": sum(1 for t in trials if t["validity"] == HARNESS_FAILURE),
        "mechanical_ok": sum(1 for g in valid if g["mechanical"]["ok"]),
        "semantic_detected": sum(1 for g in valid if g["semantic"]["result"] == DETECTED),
        "semantic_not_detected": sum(1 for g in valid if g["semantic"]["result"] == NOT_DETECTED),
        "grading_unavailable": sum(1 for g in valid if g["semantic"]["result"] == UNAVAILABLE),
    }


def _resources(graded: list[dict[str, Any]]) -> dict[str, Any]:
    """Only facts the harness reliably observes. Prompt bytes are bytes, not tokens."""
    def median(values: list[float]) -> float | None:
        vals = sorted(v for v in values if v is not None)
        return None if not vals else round(vals[len(vals) // 2], 3)
    valid = [g["trial"] for g in graded if g["trial"]["validity"] == VALID]
    return {
        "median_prompt_bytes": median([t.get("prompt_bytes") for t in valid]),
        "median_supplied_bytes": median([t.get("context_bytes") for t in valid]),
        "median_elapsed_seconds": median([t.get("elapsed_seconds") for t in valid]),
    }


def summarize(scenario_results: list[dict[str, Any]], *, system: dict[str, Any]) -> dict[str, Any]:
    """Build the committed record from per-scenario graded trials."""
    scenarios = []
    for entry in scenario_results:
        scenario, graded = entry["scenario"], entry["graded"]
        scenarios.append({
            "id": scenario["id"],
            "identity": scenario["identity"],
            "kind": scenario["kind"],
            "review_purpose": scenario["review_purpose"],
            "counts": _counts(graded),
            "resources": _resources(graded),
            # Per-trial semantic outcomes, so a reader can see reliability rather than a rate.
            "trials": [{"validity": g["trial"]["validity"],
                        "mechanical_ok": g["mechanical"]["ok"] if g["trial"]["validity"] == VALID else None,
                        "semantic": g["semantic"]["result"] if g["trial"]["validity"] == VALID else None}
                       for g in graded],
        })
    totals: dict[str, int] = {}
    for s in scenarios:
        for key, value in s["counts"].items():
            totals[key] = totals.get(key, 0) + value
    return {"format": SUMMARY_FORMAT, "system": system,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "scenarios": scenarios, "totals": totals}


def load(path: Path) -> dict[str, Any]:
    """Read a summary under the semantics it recorded; unknown versions fail closed."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SummaryError(f"evaluation summary unreadable: {path}: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("format") not in SUPPORTED_SUMMARY_FORMATS:
        raise SummaryError(f"unsupported evaluation summary format: "
                           f"{raw.get('format') if isinstance(raw, dict) else type(raw).__name__}")
    return raw


def render(summary: dict[str, Any]) -> str:
    """A human-readable view. Derived, so it never becomes a protocol field."""
    lines = [f"Proofbound Eval V1 — {summary['recorded_at']}",
             f"  proofbound {summary['system'].get('proofbound_sha', '?')[:12]}"
             f"  model {summary['system'].get('model')}"
             f"  grader {summary['system'].get('grader_model')}", ""]
    for s in summary["scenarios"]:
        c = s["counts"]
        lines.append(f"  {s['id']}  ({s['kind']})")
        lines.append(f"    attempted {c['attempted']}  valid {c['valid']}"
                     f"  setup-fail {c['setup_failures']}  harness-fail {c['harness_failures']}")
        lines.append(f"    mechanical {c['mechanical_ok']}/{c['valid']}"
                     f"   detected {c['semantic_detected']}/{c['valid']}"
                     f"   missed {c['semantic_not_detected']}"
                     f"   ungraded {c['grading_unavailable']}")
        r = s["resources"]
        lines.append(f"    median prompt bytes {r['median_prompt_bytes']}"
                     f"   median seconds {r['median_elapsed_seconds']}")
    t = summary["totals"]
    lines += ["", f"  TOTAL attempted {t.get('attempted', 0)}  valid {t.get('valid', 0)}"
                  f"  detected {t.get('semantic_detected', 0)}"
                  f"  missed {t.get('semantic_not_detected', 0)}"]
    return "\n".join(lines)
