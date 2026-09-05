#!/usr/bin/env python3
"""Durable acceptance of an aggregate consistency challenge.

M2C-A can say which exact engineering contract existed. It cannot say that anyone
challenged it as a whole, and individually reflected artifacts can still contradict each
other — a design that quietly violates its own proposal, two specifications that disagree.
Freezing such a set produces an authoritative record of an incoherent contract.

The fact this record carries, worded precisely because the wording decides what Proofbound
claims authority over:

    candidate C received a qualifying consistency-reflection review, and the parent
    accepted it

Not *"C is consistent"*: that is a semantic verdict, and Python asserting it would recreate
the PASS enum DSD deliberately deleted. Not *"C is authorized for execution"*: that is task
binding, a later milestone. This is provenance of a **challenge**, exactly as the artifact
ledger records that an artifact was accepted under a purpose rather than that it is good.

Why it is project state rather than run state: DSD's own acceptance is written into
`run_root/state.json`, which is execution evidence and expendable by design. Deleting a run
tree must cost provenance *verification* and nothing else, so the durable consequence is
copied into the project exactly as `pb_ledger record` does for artifacts.

This record introduces **no new engineering identity**. Candidate identity is freeze
identity; this file is a durable relationship *about* that identity, keyed by it.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

CONSISTENCY_FORMAT = "proofbound-consistency-acceptance-v1"
SUPPORTED_CONSISTENCY_FORMATS = (CONSISTENCY_FORMAT,)
CONSISTENCY_FIELDS = frozenset({"format", "candidate", "gate", "gate_sha256"})

# Pinned by v1, deliberately NOT read from `_review_purpose.REVIEW_PURPOSE_ROLES`. A v1
# record must keep meaning what it meant even after the live registry adds, removes or
# reassigns a purpose; resolving history through today's table is the M0 failure. These
# constants are also why the record stores neither purpose nor role: v1 *is* the
# consistency-reflection record, and the hash-pinned gate already states the actual role.
V1_CONSISTENCY_PURPOSE = "consistency-reflection"
V1_CONSISTENCY_ROLES = frozenset({"spec-reflector"})

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ConsistencyError(ValueError):
    """A consistency record cannot be interpreted, or an operation on it would be unsound."""


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _HEX64.match(value):
        raise ConsistencyError(f"{label} is not a lowercase hex SHA-256: {value!r}")
    return value


def _run_relative(raw: Any, label: str) -> str:
    """A run-relative POSIX path. Never absolute: a committed record must not embed a
    machine path, and never `..`, which could escape the run root it is resolved against."""
    if not isinstance(raw, str) or not raw.strip():
        raise ConsistencyError(f"{label} must be a non-empty string")
    if raw != raw.strip() or "\\" in raw or raw.endswith("/"):
        raise ConsistencyError(f"unsafe or non-canonical {label}: {raw!r}")
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts or "." in p.parts or p.as_posix() != raw:
        raise ConsistencyError(f"unsafe or non-canonical {label}: {raw!r}")
    return raw


def canonical_record_text(record: dict[str, Any]) -> str:
    """The committed form. Deterministic and human-readable; a reviewer must be able to see
    what was recorded."""
    return json.dumps({field: record[field] for field in sorted(CONSISTENCY_FIELDS)},
                      indent=2, sort_keys=True) + "\n"


def record_path(directory: Path, candidate: str) -> Path:
    """Where a record for `candidate` lives. Content-addressed by the candidate it concerns,
    so `C1` and `C2` coexist as the different subjects they are — not as revisions."""
    return Path(directory) / f"{_digest(candidate, 'candidate identity')}.json"


def load_record(path: Path) -> dict[str, Any]:
    """Read and validate a record **from the file alone** — no ledger, graph, freeze or run
    tree. If interpretation depended on current state, withdrawing an artifact would
    retroactively make a historical acceptance unreadable."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConsistencyError(f"consistency record missing: {path}") from exc
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConsistencyError(f"consistency record unreadable: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConsistencyError("consistency record must be a JSON object")

    fmt = raw.get("format")
    if fmt not in SUPPORTED_CONSISTENCY_FORMATS:
        raise ConsistencyError(f"unsupported consistency-acceptance format: {fmt!r}")
    missing = sorted(CONSISTENCY_FIELDS - set(raw))
    if missing:
        raise ConsistencyError(f"consistency record is missing {', '.join(missing)}")
    extra = sorted(set(raw) - CONSISTENCY_FIELDS)
    if extra:
        raise ConsistencyError(f"unknown consistency-record field(s): {', '.join(extra)}")

    out = {"format": fmt,
           "candidate": _digest(raw["candidate"], "candidate"),
           "gate": _run_relative(raw["gate"], "gate path"),
           "gate_sha256": _digest(raw["gate_sha256"], "gate_sha256"),
           "findings": []}

    # The filename is a convenience index, never the authority: the record names its own
    # subject so a copy under any name still means the same thing. A 64-hex name that
    # disagrees with that subject is a defect worth surfacing.
    stem = path.stem
    if _HEX64.match(stem) and stem != out["candidate"]:
        out["findings"].append({
            "code": "filename-candidate-mismatch", "path": str(path),
            "reason": f"file is named for {stem[:12]} but records acceptance of "
                      f"{out['candidate'][:12]}"})
    return out


def lookup(directory: Path, candidate: str) -> dict[str, Any]:
    """Has this exact candidate been challenged and accepted?

    A domain question, so callers never need `Path.exists()` — or the storage layout — as
    the definition of acceptance. Absent and accepted are distinguishable states; a
    malformed record raises rather than reading as absent.
    """
    candidate = _digest(candidate, "candidate identity")
    path = record_path(directory, candidate)
    if not path.is_file():
        return {"candidate": candidate, "state": "absent", "path": str(path)}
    record = load_record(path)
    return {"candidate": candidate, "state": "accepted", "path": str(path), "record": record}


def check_provenance(record: dict[str, Any], run_root: Path | None) -> dict[str, Any]:
    """What retained execution evidence can additionally show about a recorded acceptance.

    Absent evidence yields `unavailable` — never `verified`, and never a retraction of the
    durable record. Present-but-contradictory evidence is `contradicted`, a materially
    different and more serious signal than absence. Neither ever changes the record itself:
    creation policy and later verification policy are separate questions.
    """
    gate_rel = _run_relative(record["gate"], "gate path")
    if run_root is None:
        return {"provenance": "unavailable",
                "reasons": ["no run root supplied; execution evidence not consulted"]}
    run_root = Path(run_root).resolve()
    gate_path = (run_root / gate_rel).resolve()
    try:
        gate_path.relative_to(run_root)
    except ValueError as exc:
        raise ConsistencyError(f"recorded gate path escapes the run root: {gate_rel}") from exc
    if not gate_path.is_file():
        return {"provenance": "unavailable",
                "reasons": [f"recorded integrity gate is no longer retained: {gate_rel}"]}

    reasons: list[str] = []
    if hashlib.sha256(gate_path.read_bytes()).hexdigest() != record["gate_sha256"]:
        reasons.append(f"integrity gate bytes changed since acceptance: {gate_rel}")
    else:
        try:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            gate = None
            reasons.append(f"integrity gate unreadable: {exc}")
        if isinstance(gate, dict):
            if gate.get("integrity_ok") is not True or gate.get("errors"):
                reasons.append("recorded integrity gate is not clean")
            if gate.get("ready_for_interpretation") is not True:
                reasons.append("recorded integrity gate was not ready for interpretation")
            role = str(gate.get("role") or "").strip().lower()
            # Checked against the v1 constant, never the live registry.
            if role not in V1_CONSISTENCY_ROLES:
                reasons.append(
                    f"gate records role {role!r}, which does not qualify for "
                    f"{V1_CONSISTENCY_PURPOSE} under freeze v1 semantics")
    return {"provenance": "contradicted" if reasons else "verified", "reasons": reasons}
