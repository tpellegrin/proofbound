#!/usr/bin/env python3
"""Closed-world semantic experiments: the column is declared before the run.

The distinction this module exists to hold is the one
[`evaluation.md` §E20](../docs/architecture/proofbound/evaluation.md) settles. A *closed-world*
measurement names its semantic column in advance — "does this report identify this specific
problem?" — so every sample is scored on its own and two samples never meet. An *open-world*
discovery would have to decide what counts as one distinct finding before it could count
anything, which is a different and much harder problem, and deliberately not one this substrate
attempts.

Almost nothing here is new. A cell is addressed by a composite slot id, which lets the repeated
measurement machinery built for the reliability run — preallocated slots, a hash over the whole
frozen configuration, atomic checkpointing, and a resume that refuses to splice across
configurations — apply unchanged. What this module adds is the manifest: what is being claimed,
against which baseline, with which budget, and what would make the answer uninterpretable, all
written down before any measurement exists.

Python validates the *shape* of an experiment and never its merit. Whether a pressure is entailed
by the authority the evaluator receives, whether N is adequate, whether an effect matters, and
whether a treatment is an improvement are semantic judgements that stay outside this file (`P1`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FORMAT = "proofbound-closed-world-experiment-v1"

# Declared before any treatment measurement exists, because a hypothesis edited after seeing
# results is not a hypothesis. Each field is a sentence a reader can later hold the run to.
REQUIRED_TEXT = ("claim", "measurand", "baseline", "treatment", "primary_comparison",
                 "falsifier", "adoption_rule")
REQUIRED_LIST = ("frozen", "guardrails", "invalid_if")

BASELINE_ARM = "baseline"


class ExperimentError(Exception):
    """A mechanically malformed experiment. Never a judgement about a well-formed one."""


def _slot_id(instance: str, arm: str, pressure: str) -> str:
    """One measurement cell: this implementation, under this arm, for this declared pressure.

    Composite rather than a new multi-key store, because the existing series machinery already
    keys on one item plus a repeat index. Separating the coordinates with a character that no
    identifier may contain keeps the composite unambiguous, and makes it impossible for a sample
    taken for one pressure or one arm to satisfy another's slot.
    """
    return f"{instance}|{arm}|{pressure}"


def split_slot(slot: str) -> tuple[str, str, str]:
    instance, arm, pressure = slot.split("|")
    return instance, arm, pressure


def _reflection_slot(instance: str, arm: str, sample: int) -> str:
    """One reflection serves every pressure graded against it, so it is addressed without one."""
    return f"{instance}|{arm}#{sample}"


def load(path: Path) -> dict[str, Any]:
    """Read one pre-registered experiment, refusing anything mechanically unusable."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ExperimentError(f"experiment unreadable: {path}: {exc}") from exc
    if raw.get("format") != FORMAT:
        raise ExperimentError(f"unsupported experiment format: {raw.get('format')!r}")

    for field in REQUIRED_TEXT:
        if not isinstance(raw.get(field), str) or len(raw[field].strip()) < 10:
            raise ExperimentError(f"{field} must be a substantive statement")
    for field in REQUIRED_LIST:
        if not isinstance(raw.get(field), list) or not raw[field]:
            raise ExperimentError(f"{field} must list at least one entry")

    samples = raw.get("samples_per_cell")
    if not isinstance(samples, int) or samples < 1:
        raise ExperimentError("samples_per_cell must be a positive integer")

    instances = raw.get("instances") or []
    if not instances or len(set(instances)) != len(instances):
        raise ExperimentError("instances must be a non-empty list of distinct names")

    pressures = raw.get("pressures") or []
    if not pressures:
        raise ExperimentError("a closed-world experiment declares at least one pressure")
    seen: set[str] = set()
    for pressure in pressures:
        pid = pressure.get("id")
        if not isinstance(pid, str) or not pid or "|" in pid or "#" in pid:
            raise ExperimentError(f"pressure id must be a simple name: {pid!r}")
        if pid in seen:
            raise ExperimentError(f"duplicate pressure id: {pid}")
        seen.add(pid)
        if not isinstance(pressure.get("statement"), str) or len(pressure["statement"]) < 20:
            raise ExperimentError(f"pressure {pid} needs a statement of the planted problem")

    arms = raw.get("arms") or []
    if not arms:
        raise ExperimentError("an experiment declares at least one arm")
    arm_ids = [a.get("id") for a in arms]
    if len(set(arm_ids)) != len(arm_ids):
        raise ExperimentError("duplicate arm id")
    for arm in arms:
        if not isinstance(arm.get("id"), str) or "|" in arm["id"] or "#" in arm["id"]:
            raise ExperimentError(f"arm id must be a simple name: {arm.get('id')!r}")
    # A comparison needs something to compare against. One arm alone is a measurement, not an
    # experiment, and is allowed — but a treatment arm without its baseline is neither.
    if len(arms) > 1 and BASELINE_ARM not in arm_ids:
        raise ExperimentError(
            f"a paired experiment needs a {BASELINE_ARM!r} arm to compare against")
    for name in ("instances", "pressures", "arms"):
        raw.setdefault(name, [])
    return raw


def slots(experiment: dict[str, Any]) -> list[dict[str, Any]]:
    """Every measurement slot, preallocated before the first call.

    Sampling order is generated here and never revisited: which cell is measured next cannot
    depend on what earlier cells returned, so an interrupted run resumes into fixed slots rather
    than choosing its remaining work from the results it already has.

    Arms are interleaved rather than run in blocks. A run spans hours, providers drift, and a
    schedule that put every baseline first would let drift line up exactly with the comparison.
    """
    arms = [a["id"] for a in experiment["arms"]]
    out: list[dict[str, Any]] = []
    for sample in range(1, experiment["samples_per_cell"] + 1):
        for index, instance in enumerate(experiment["instances"]):
            # Rotate the arm order per (sample, instance) so no arm holds a fixed position.
            offset = (sample + index) % len(arms)
            for arm in arms[offset:] + arms[:offset]:
                out.append({"instance": instance, "arm": arm, "sample": sample,
                            "reflection_slot": _reflection_slot(instance, arm, sample)})
    return out


def measurement_rows(experiment: dict[str, Any], slot: dict[str, Any]) -> list[dict[str, Any]]:
    """The graded cells one reflection produces: one per declared pressure, never one verdict."""
    return [{"item": _slot_id(slot["instance"], slot["arm"], pressure["id"]),
             "repeat": slot["sample"], "instance": slot["instance"], "arm": slot["arm"],
             "pressure": pressure["id"]}
            for pressure in experiment["pressures"]]


def cells(experiment: dict[str, Any]) -> list[str]:
    """Every (instance, arm, pressure) cell a distribution may be reported for."""
    return [_slot_id(i, a["id"], p["id"])
            for i in experiment["instances"]
            for a in experiment["arms"]
            for p in experiment["pressures"]]


def configuration(experiment: dict[str, Any], system: dict[str, Any]) -> dict[str, Any]:
    """What must not vary between two measurements of the same series.

    Everything the comparison depends on, and nothing that merely describes when it ran: the
    frozen identity computed over this is what refuses a resume from a different experiment.
    """
    return {
        "format": FORMAT,
        "experiment": experiment["id"],
        "claim": experiment["claim"],
        "measurand": experiment["measurand"],
        "samples_per_cell": experiment["samples_per_cell"],
        "instances": list(experiment["instances"]),
        "pressures": [{"id": p["id"], "statement": p["statement"]}
                      for p in experiment["pressures"]],
        "arms": [{"id": a["id"], "treatment_sha256": a.get("treatment_sha256")}
                 for a in experiment["arms"]],
        "system": system,
    }
