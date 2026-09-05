#!/usr/bin/env python3
"""Record and inspect acceptance of an aggregate consistency challenge.

Two commands. This is a provenance primitive, not a workflow: there is no `approve`, no
`authorize`, no `current`, and nothing here decides whether an engineering contract is
coherent. A spec-reflector judges that; this records that the judgement was made under a
qualifying review the parent accepted.

    record   copy a completed acceptance into durable project state (parent-owned)
    status   has this exact candidate been challenged, and is the evidence still intact?

Exit codes:

    2  the record, freeze or run state cannot be interpreted, or recording is unsound
    1  interpreted fine, but the answer is negative — no acceptance, or evidence contradicts
    0  accepted, with evidence verified or legitimately unavailable
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from _consistency import (CONSISTENCY_FORMAT, V1_CONSISTENCY_PURPOSE, V1_CONSISTENCY_ROLES,
                          ConsistencyError, canonical_record_text, check_provenance, load_record,
                          lookup, record_path)
from _contract import declared_candidate, declared_review_purpose
from _freeze import FreezeError, freeze_identity, load_freeze


def _load_json(path: Path, label: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConsistencyError(f"{label} missing: {path}") from exc
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConsistencyError(f"{label} unreadable: {path}: {exc}") from exc


def record(args: argparse.Namespace) -> tuple[int, dict]:
    """Persist one already-accepted aggregate challenge. Parent-owned; never a worker step.

    Everything written here is copied from an acceptance that already happened. This can
    refuse, but it can never approve: if DSD did not accept the review, there is nothing to
    record. Unlike freeze creation — where absent evidence is normal for an old repository —
    a *new* acceptance whose evidence is already gone would be a claim the parent cannot
    evidence at the moment it makes it, so the gate must be present and clean.
    """
    run_root = args.run_root.resolve()
    state = _load_json(run_root / "state.json", "run state")

    task = (state.get("phases") or {}).get(args.phase_id, {}).get("tasks", {}).get(args.task_id)
    if not isinstance(task, dict):
        raise ConsistencyError(f"unknown task: {args.phase_id}/{args.task_id}")
    if task.get("status") != "accepted":
        raise ConsistencyError(
            f"refusing to record a consistency acceptance for a task with status "
            f"{task.get('status')!r}: this records acceptance, it does not confer it")

    accepted = task.get("accepted") or {}
    source_gate = accepted.get("source_gate") or {}
    gate_path = Path(source_gate.get("path") or "")
    if not gate_path.is_absolute() or not gate_path.is_file():
        raise ConsistencyError(f"accepted integrity gate missing: {gate_path}")
    gate_sha = hashlib.sha256(gate_path.read_bytes()).hexdigest()
    if gate_sha != source_gate.get("sha256"):
        raise ConsistencyError("accepted integrity gate changed after acceptance")
    gate = _load_json(gate_path, "accepted integrity gate")
    if (gate.get("integrity_ok") is not True or gate.get("errors")
            or gate.get("ready_for_interpretation") is not True):
        raise ConsistencyError("accepted integrity gate is not clean")

    contract_binding = task.get("current_contract") or {}
    contract = Path(contract_binding.get("path") or "")
    if not contract.is_file():
        raise ConsistencyError(f"accepted task contract missing: {contract}")
    if hashlib.sha256(contract.read_bytes()).hexdigest() != contract_binding.get("sha256"):
        raise ConsistencyError("accepted task contract changed after acceptance")
    contract_text = contract.read_text(encoding="utf-8")

    # Checked against the pinned v1 constants rather than the live registry, so a record
    # written today will still verify under v1 semantics after the registry evolves.
    purpose = declared_review_purpose(contract_text)
    if purpose != V1_CONSISTENCY_PURPOSE:
        raise ConsistencyError(
            f"task contract declares review purpose {purpose!r}; a consistency acceptance "
            f"requires {V1_CONSISTENCY_PURPOSE!r}")
    role = str(gate.get("role") or "").strip().lower()
    if role not in V1_CONSISTENCY_ROLES:
        raise ConsistencyError(
            f"accepted gate records role {role!r}, which does not qualify for "
            f"{V1_CONSISTENCY_PURPOSE} under v1 semantics")

    candidate = declared_candidate(contract_text)
    if candidate is None:
        raise ConsistencyError(
            f"task contract declares no `## Proofbound candidate`: {contract}. The review "
            "must be bound to the exact candidate it challenged.")

    # The subject must be a real, well-formed contract candidate, and the contract must have
    # named that exact one. Without this, an acceptance could be recorded for an identity
    # that never denoted anything.
    freeze = load_freeze(args.freeze)
    identity = freeze_identity(freeze)
    if identity != candidate:
        raise ConsistencyError(
            f"contract names candidate {candidate[:12]} but the supplied freeze is "
            f"{identity[:12]}")

    try:
        gate_rel = gate_path.resolve().relative_to(run_root).as_posix()
    except ValueError as exc:
        raise ConsistencyError(f"accepted gate is outside the run root: {gate_path}") from exc

    entry = {"format": CONSISTENCY_FORMAT, "candidate": candidate,
             "gate": gate_rel, "gate_sha256": gate_sha}
    out_dir = args.into.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = record_path(out_dir, candidate)
    text = canonical_record_text(entry)
    existed = path.is_file()
    if existed and path.read_text(encoding="utf-8") == text:
        return 0, {"record": str(path), "candidate": candidate, "written": False}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    load_record(path)
    # Re-reviewing the same candidate refreshes its provenance in place: the candidate is
    # one subject, and Git carries the history of what evidenced it.
    return 0, {"record": str(path), "candidate": candidate, "written": True,
               "refreshed": existed}


def status(args: argparse.Namespace) -> tuple[int, dict]:
    """Has this exact candidate been challenged, and what can retained evidence still show?

    Deliberately does not ask whether the candidate is *current* — that is
    `pb_freeze compare`, a separate dimension that may legitimately disagree with this one.
    """
    found = lookup(args.into.resolve(), args.candidate)
    result = {"candidate": found["candidate"], "state": found["state"], "path": found["path"]}
    if found["state"] == "absent":
        return 1, {**result, "provenance": "unavailable",
                   "reasons": ["no accepted consistency review is recorded for this candidate"]}
    rec = found["record"]
    result["findings"] = rec["findings"]
    prov = check_provenance(rec, args.run_root.resolve() if args.run_root else None)
    result.update(prov)
    return (1 if prov["provenance"] == "contradicted" or rec["findings"] else 0), result


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    r = sub.add_parser("record", help="persist an accepted aggregate challenge (parent-owned)")
    r.add_argument("--run-root", type=Path, required=True)
    r.add_argument("--phase-id", required=True)
    r.add_argument("--task-id", required=True)
    r.add_argument("--freeze", type=Path, required=True, help="the candidate that was challenged")
    r.add_argument("--into", type=Path, required=True, help="directory of consistency records")
    r.set_defaults(handler=record)

    s = sub.add_parser("status", help="has this candidate been challenged and accepted?")
    s.add_argument("--into", type=Path, required=True)
    s.add_argument("--candidate", required=True)
    s.add_argument("--run-root", type=Path, default=None,
                   help="optional retained evidence; absence yields provenance=unavailable")
    s.set_defaults(handler=status)
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        code, payload = args.handler(args)
    except (ConsistencyError, FreezeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
