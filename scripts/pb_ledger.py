#!/usr/bin/env python3
"""The Proofbound durable change ledger: record and validate accepted artifacts.

What this is
------------
DSD mechanics prove one thing per task: a bounded project mutation was reviewed by a
fresh, independent, non-mutating attempt, and the parent accepted it. That proof lives in
a run tree, which is large, machine-local and eventually deleted.

This module persists the small, durable consequence of that event:

    which content was accepted, what it depended on, and under which declared review
    purpose and qualifying role.

From that record alone — a clean Git checkout, no run history — Proofbound can re-derive
whether the accepted artifacts are still the artifacts on disk, and whether anything a
reviewed artifact depended on has moved underneath it.

What this deliberately is not
-----------------------------
Not a second acceptance engine. It never decides that a review was adequate, never
recomputes reviewer freshness, never parses reviewer prose, never infers a purpose, and
never invents a task state. `record` refuses to run unless DSD acceptance already
happened, and it copies facts out of that event rather than re-deriving them. Validation
compares hashes and a closed table.

Trust boundary
--------------
SHA-256 here is integrity, not authority. A committed ledger is not a signature: anyone
with repository write access can hand-write an internally consistent one. What structural
validation proves is that recorded content, dependencies and schema are self-consistent
and match the working tree. Whether the review actually happened is provable only while
the execution evidence still exists, and even then only to the extent the run tree is
itself trusted. Proofbound has no signing or trust roots, and this file claims none.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from _artifact_identity import (
    ARTIFACT_IDENTITY_FORMAT,
    SUPPORTED_ARTIFACT_IDENTITY_FORMATS,
    ArtifactIdentityError,
    artifact_identity_file,
)
from _dag import CycleError, assert_acyclic, topological_order
from _contract import (allowed_source_changes, declared_review_purpose,
                       has_explicit_write_restriction, path_allowed)
from _review_purpose import assert_role_qualifies

LEDGER_FORMAT = "proofbound-change-ledger-v1"
# Historical formats stay verifiable under their own semantics. When v2 exists, it gets its
# own reader; v1 records are never loaded into later assumptions. M0 already paid for
# getting exactly this wrong once with worker-rules manifests.
SUPPORTED_LEDGER_FORMATS = (LEDGER_FORMAT,)

REQUIRED_ARTIFACT_KEYS = ("content_sha256", "depends_on", "review")
REQUIRED_REVIEW_KEYS = ("purpose", "role", "gate", "gate_sha256")

VALID = "valid"
INVALID = "invalid"
NEEDS_REVALIDATION = "needs-revalidation"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class LedgerError(ValueError):
    """The ledger cannot be interpreted, or an operation on it would be unsound."""


# ---------------------------------------------------------------- serialization


def canonical_ledger_text(ledger: dict[str, Any]) -> str:
    """Committed form: sorted keys, 2-space indent, trailing newline.

    Stable and human-diffable, matching how DSD already writes its manifests. The ledger
    is not itself content-addressed in v1 — Git supplies its history and integrity — so no
    hash-stable compact encoding is invented here for a mechanism nothing consumes.
    """
    return json.dumps(ledger, indent=2, sort_keys=True) + "\n"


def _relative_key(raw: str, *, label: str) -> str:
    """Normalize a project-relative artifact path, rejecting anything that could escape."""
    if not isinstance(raw, str) or not raw.strip():
        raise LedgerError(f"{label} must be a non-empty string")
    value = raw.replace("\\", "/").strip()
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value in {".", "./"}:
        raise LedgerError(f"unsafe {label}: {raw}")
    return path.as_posix()


# ---------------------------------------------------------------- schema


def _check_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _HEX64.match(value.lower()):
        raise LedgerError(f"{label} is not a lowercase hex SHA-256: {value!r}")
    return value.lower()


def load_ledger(path: Path) -> dict[str, Any]:
    """Read and fully schema-check a ledger, failing closed on anything unrecognized."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LedgerError(f"ledger missing: {path}") from exc
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise LedgerError(f"ledger unreadable: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise LedgerError("ledger must be a JSON object")

    fmt = raw.get("format")
    if fmt not in SUPPORTED_LEDGER_FORMATS:
        raise LedgerError(f"unsupported change-ledger format: {fmt!r}")
    identity = raw.get("artifact_identity")
    if identity not in SUPPORTED_ARTIFACT_IDENTITY_FORMATS:
        raise LedgerError(f"unsupported artifact identity protocol: {identity!r}")

    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, dict):
        raise LedgerError("ledger `artifacts` must be an object")

    normalized: dict[str, Any] = {}
    for key, entry in artifacts.items():
        path_key = _relative_key(key, label="artifact path")
        if path_key in normalized:
            raise LedgerError(f"duplicate artifact path after normalization: {path_key}")
        if not isinstance(entry, dict):
            raise LedgerError(f"{path_key}: artifact record must be an object")
        for required in REQUIRED_ARTIFACT_KEYS:
            if required not in entry:
                raise LedgerError(f"{path_key}: artifact record is missing `{required}`")
        _check_digest(entry["content_sha256"], f"{path_key}: content_sha256")

        depends_on = entry["depends_on"]
        if not isinstance(depends_on, dict):
            raise LedgerError(f"{path_key}: `depends_on` must be an object")
        deps: dict[str, str] = {}
        for dep_key, dep_hash in depends_on.items():
            dep_path = _relative_key(dep_key, label=f"{path_key}: dependency path")
            deps[dep_path] = _check_digest(dep_hash, f"{path_key}: dependency {dep_path}")

        rev = entry["review"]
        if not isinstance(rev, dict):
            raise LedgerError(f"{path_key}: `review` must be an object")
        for required in REQUIRED_REVIEW_KEYS:
            if required not in rev:
                raise LedgerError(f"{path_key}: review record is missing `{required}`")
        # Checkable from a clean checkout: the recorded role must be authorized for the
        # recorded purpose. A record that contradicts the purpose table is malformed, not
        # merely stale — no amount of re-reading the working tree could make it consistent.
        try:
            assert_role_qualifies(rev["purpose"], rev["role"])
        except ValueError as exc:
            raise LedgerError(f"{path_key}: {exc}") from exc
        gate = _relative_key(rev["gate"], label=f"{path_key}: review gate path")
        _check_digest(rev["gate_sha256"], f"{path_key}: review gate_sha256")

        normalized[path_key] = {
            "content_sha256": entry["content_sha256"].lower(),
            "depends_on": deps,
            "review": {"purpose": str(rev["purpose"]).strip().lower(),
                       "role": str(rev["role"]).strip().lower(),
                       "gate": gate,
                       "gate_sha256": str(rev["gate_sha256"]).lower()},
        }

    for path_key, entry in normalized.items():
        for dep in entry["depends_on"]:
            if dep not in normalized:
                raise LedgerError(f"{path_key}: depends on an artifact absent from the ledger: {dep}")

    _assert_acyclic(normalized)
    return {"format": fmt, "artifact_identity": identity, "artifacts": normalized}


def _dependency_edges(artifacts: dict[str, Any]) -> dict[str, list[str]]:
    """Adapt accepted-ledger records to the shared DAG shape."""
    return {name: list(entry["depends_on"]) for name, entry in artifacts.items()}


def _assert_acyclic(artifacts: dict[str, Any]) -> None:
    """Reject cycles before any traversal derives state.

    The dependency graph is a DAG by construction; a cycle means the ledger is malformed.
    Traversal itself lives in `_dag`, shared with the declared change graph so the two can
    never disagree about what a cycle is.
    """
    try:
        assert_acyclic(_dependency_edges(artifacts))
    except CycleError as exc:
        raise LedgerError(f"dependency cycle in ledger: {exc}") from exc


# ---------------------------------------------------------------- derived state


def derive_states(ledger: dict[str, Any], project_root: Path) -> dict[str, dict[str, Any]]:
    """Derive each artifact's state. Nothing here is ever persisted.

    Precedence, in order:

      1. own content does not match the accepted identity  -> invalid
      2. a dependency's accepted identity moved, or any artifact in the dependency
         closure is not valid                              -> needs-revalidation
      3. otherwise                                         -> valid

    `invalid` means "this is not the artifact that was accepted". `needs-revalidation`
    means "this artifact is intact, but the ground it was reviewed against moved". An
    invalid dependency therefore does not make its dependents invalid; it makes them
    need re-review, which is the honest engineering statement.
    """
    artifacts = ledger["artifacts"]
    own: dict[str, list[str]] = {}
    for path_key, entry in artifacts.items():
        target = project_root / path_key
        if not target.is_file():
            own[path_key] = [f"accepted artifact is missing from the working tree: {path_key}"]
            continue
        try:
            current = artifact_identity_file(target)
        except ArtifactIdentityError as exc:
            own[path_key] = [f"accepted artifact has no readable text identity: {exc}"]
            continue
        if current != entry["content_sha256"]:
            own[path_key] = [
                f"content changed from {entry['content_sha256'][:12]} to {current[:12]}"
            ]
        else:
            own[path_key] = []

    resolved: dict[str, dict[str, Any]] = {}

    def visit(node: str) -> dict[str, Any]:
        if node in resolved:
            return resolved[node]
        if own[node]:
            resolved[node] = {"state": INVALID, "reasons": list(own[node])}
            return resolved[node]
        reasons: list[str] = []
        for dep, recorded_dep_hash in sorted(artifacts[node]["depends_on"].items()):
            accepted_now = artifacts[dep]["content_sha256"]
            if accepted_now != recorded_dep_hash:
                reasons.append(
                    f"dependency {dep} changed from {recorded_dep_hash[:12]} to {accepted_now[:12]} "
                    "since this artifact was reviewed"
                )
            dep_state = visit(dep)["state"]
            if dep_state != VALID:
                reasons.append(f"dependency {dep} is {dep_state}")
        resolved[node] = {"state": NEEDS_REVALIDATION if reasons else VALID, "reasons": reasons}
        return resolved[node]

    # Resolve dependencies before dependents. `visit` recurses, but every dependency it
    # reaches is already cached by then, so effective recursion depth stays at one and a
    # legitimately deep chain cannot hit the interpreter limit (proved at depth 5000).
    order = topological_order(_dependency_edges(artifacts))
    for node in order:
        visit(node)
    return resolved


# ---------------------------------------------------------------- provenance


def _resolve_in_run(run_root: Path, relative: str) -> Path:
    resolved = (run_root / relative).resolve()
    try:
        resolved.relative_to(run_root.resolve())
    except ValueError as exc:
        raise LedgerError(f"recorded gate path escapes the run root: {relative}") from exc
    return resolved


def check_provenance(ledger: dict[str, Any], run_root: Path | None) -> dict[str, dict[str, Any]]:
    """Second validation level: what retained execution evidence can additionally show.

    Absent evidence yields `unavailable` — never `verified`, and never a downgrade of a
    structurally valid artifact. Present-but-contradictory evidence is `contradicted`,
    which is a genuinely different and much more serious signal than absence.
    """
    out: dict[str, dict[str, Any]] = {}
    for path_key, entry in ledger["artifacts"].items():
        rev = entry["review"]
        if run_root is None:
            out[path_key] = {"provenance": "unavailable",
                             "reasons": ["no run root supplied; execution evidence not consulted"]}
            continue
        gate_path = _resolve_in_run(run_root, rev["gate"])
        if not gate_path.is_file():
            out[path_key] = {"provenance": "unavailable",
                             "reasons": [f"recorded integrity gate is no longer retained: {rev['gate']}"]}
            continue
        reasons: list[str] = []
        actual_sha = hashlib.sha256(gate_path.read_bytes()).hexdigest()
        if actual_sha != rev["gate_sha256"]:
            reasons.append(f"integrity gate bytes changed since acceptance: {rev['gate']}")
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
                actual_role = str(gate.get("role") or "").strip().lower()
                if actual_role != rev["role"]:
                    reasons.append(
                        f"recorded role {rev['role']!r} does not match the gate's role {actual_role!r}")
                else:
                    try:
                        assert_role_qualifies(rev["purpose"], actual_role)
                    except ValueError as exc:
                        reasons.append(str(exc))
        out[path_key] = {"provenance": "contradicted" if reasons else "verified", "reasons": reasons}
    return out


# ---------------------------------------------------------------- validate


def validate(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    ledger_path = args.ledger.resolve()
    ledger = load_ledger(ledger_path)
    project_root = args.project_root.resolve()
    run_root = args.run_root.resolve() if args.run_root else None

    states = derive_states(ledger, project_root)
    provenance = check_provenance(ledger, run_root)

    artifacts = []
    for path_key in sorted(ledger["artifacts"]):
        entry = ledger["artifacts"][path_key]
        artifacts.append({
            "path": path_key,
            "state": states[path_key]["state"],
            "reasons": states[path_key]["reasons"],
            "depends_on": entry["depends_on"],
            "review": {"purpose": entry["review"]["purpose"], "role": entry["review"]["role"],
                       **provenance[path_key]},
        })

    levels = {a["review"]["provenance"] for a in artifacts}
    if not levels:
        overall = "unavailable"
    elif "contradicted" in levels:
        overall = "contradicted"
    elif levels == {"verified"}:
        overall = "verified"
    else:
        overall = "unavailable"

    structural_ok = all(a["state"] == VALID for a in artifacts)
    result = {
        "ledger": str(ledger_path),
        "format": ledger["format"],
        "artifact_identity": ledger["artifact_identity"],
        "project_root": str(project_root),
        "run_root": str(run_root) if run_root else None,
        "structural_ok": structural_ok,
        # `unavailable` is not a failure: a clean checkout legitimately has no run history.
        "provenance": overall,
        "artifacts": artifacts,
    }
    return (0 if structural_ok and overall != "contradicted" else 1), result


# ---------------------------------------------------------------- record


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LedgerError(f"{label} missing: {path}") from exc
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise LedgerError(f"{label} unreadable: {path}: {exc}") from exc


def record(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    """Persist one already-accepted artifact. Parent-owned; never a worker operation.

    Every fact written here is copied from an acceptance that has already happened. This
    function can refuse, but it can never approve: if DSD did not accept the task, there
    is nothing to record.
    """
    run_root = args.run_root.resolve()
    state = _load_json(run_root / "state.json", "run state")
    project_root = Path(state.get("project_worktree") or "")
    if not project_root.is_absolute() or not project_root.is_dir():
        raise LedgerError(f"run state has no usable project_worktree: {project_root}")

    phases = state.get("phases")
    task = (phases or {}).get(args.phase_id, {}).get("tasks", {}).get(args.task_id)
    if not isinstance(task, dict):
        raise LedgerError(f"unknown task: {args.phase_id}/{args.task_id}")
    if task.get("status") != "accepted":
        raise LedgerError(
            f"refusing to record an artifact for a task with status {task.get('status')!r}: "
            "the ledger records acceptance, it does not confer it"
        )

    accepted = task.get("accepted") or {}
    source_gate = accepted.get("source_gate") or {}
    gate_path = Path(source_gate.get("path") or "")
    recorded_gate_sha = source_gate.get("sha256")
    if not gate_path.is_absolute() or not gate_path.is_file():
        raise LedgerError(f"accepted integrity gate missing: {gate_path}")
    gate_sha = hashlib.sha256(gate_path.read_bytes()).hexdigest()
    if gate_sha != recorded_gate_sha:
        raise LedgerError("accepted integrity gate changed after acceptance")
    gate = _load_json(gate_path, "accepted integrity gate")
    if gate.get("integrity_ok") is not True or gate.get("errors") or gate.get("ready_for_interpretation") is not True:
        raise LedgerError("accepted integrity gate is not clean")
    role = str(gate.get("role") or "").strip().lower()

    contract_binding = task.get("current_contract") or {}
    contract = Path(contract_binding.get("path") or "")
    if not contract.is_file():
        raise LedgerError(f"accepted task contract missing: {contract}")
    contract_text = contract.read_text(encoding="utf-8")
    if hashlib.sha256(contract.read_bytes()).hexdigest() != contract_binding.get("sha256"):
        raise LedgerError("accepted task contract changed after acceptance")

    # The M2A compatibility seam. Acceptance enforces a declared purpose only when one is
    # declared, so inherited DSD contracts keep their exact semantics. Recording a durable
    # Proofbound artifact *requires* one: an artifact whose review purpose is unknown could
    # never support the guarantee this ledger exists to make.
    purpose = declared_review_purpose(contract_text)
    if purpose is None:
        raise LedgerError(
            f"task contract declares no `## Review purpose`: {contract}. A Proofbound "
            "specification artifact cannot be recorded without a declared review purpose."
        )
    assert_role_qualifies(purpose, role)

    artifact = args.artifact.resolve()
    try:
        artifact_key = artifact.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise LedgerError(f"artifact is outside the project worktree: {artifact}") from exc
    if not artifact.is_file():
        raise LedgerError(f"artifact missing: {artifact}")

    # Recording fidelity, not a second acceptance decision: when authority declared a write
    # boundary for this task, the artifact being recorded must be inside it. This cannot
    # approve anything — it only stops the parent from filing an artifact under an
    # acceptance that provably never covered it.
    if has_explicit_write_restriction(contract_text):
        allowed = allowed_source_changes(contract_text)
        if not path_allowed(artifact_key, allowed):
            raise LedgerError(
                f"artifact {artifact_key} is outside the accepted contract's declared write "
                f"boundary {allowed}"
            )

    ledger_path = args.ledger.resolve()
    if ledger_path.is_file():
        ledger = load_ledger(ledger_path)
    else:
        ledger = {"format": LEDGER_FORMAT, "artifact_identity": ARTIFACT_IDENTITY_FORMAT, "artifacts": {}}

    depends_on: dict[str, str] = {}
    if args.depends_on:
        states = derive_states(ledger, project_root)
        for raw in args.depends_on:
            dep = Path(raw).resolve()
            try:
                dep_key = dep.relative_to(project_root).as_posix()
            except ValueError as exc:
                raise LedgerError(f"dependency is outside the project worktree: {dep}") from exc
            if dep_key not in ledger["artifacts"]:
                raise LedgerError(f"dependency has no accepted record in the ledger: {dep_key}")
            if dep_key == artifact_key:
                raise LedgerError(f"artifact cannot depend on itself: {dep_key}")
            if states[dep_key]["state"] != VALID:
                raise LedgerError(
                    f"dependency {dep_key} is {states[dep_key]['state']}: "
                    f"{'; '.join(states[dep_key]['reasons'])}. Recording against a dependency "
                    "that is not currently valid would fabricate provenance."
                )
            depends_on[dep_key] = ledger["artifacts"][dep_key]["content_sha256"]

    ledger["artifacts"][artifact_key] = {
        "content_sha256": artifact_identity_file(artifact),
        "depends_on": depends_on,
        "review": {
            "purpose": purpose,
            "role": role,
            "gate": gate_path.resolve().relative_to(run_root).as_posix(),
            "gate_sha256": gate_sha,
        },
    }
    # Prove the result is loadable under its own schema — including acyclicity — before it
    # is written, so a bad edge can never be persisted.
    _assert_acyclic(ledger["artifacts"])

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = ledger_path.with_name(ledger_path.name + ".tmp")
    tmp.write_text(canonical_ledger_text(ledger), encoding="utf-8")
    tmp.replace(ledger_path)
    load_ledger(ledger_path)

    return 0, {"ledger": str(ledger_path), "artifact": artifact_key,
               "content_sha256": ledger["artifacts"][artifact_key]["content_sha256"],
               "depends_on": depends_on, "review": ledger["artifacts"][artifact_key]["review"]}


def withdraw(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    """Remove one accepted record. Parent-owned; never a worker operation.

    Withdrawal is consistent with what the ledger already is. `record` overwrites an
    existing entry, so a re-accepted artifact's previous identity is already gone from
    current state: the ledger is a snapshot of *currently* accepted provenance, and Git is
    the history chain. Withdrawal is that same class of operation, made explicit — it is
    not supersession of a frozen baseline, which is a different mechanism for a different
    object and is not implemented here.

    It cannot fabricate acceptance, does not touch artifact content or run evidence, and
    refuses to leave the ledger unloadable.
    """
    ledger_path = args.ledger.resolve()
    ledger = load_ledger(ledger_path)
    project_root = args.project_root.resolve()

    artifact = args.artifact.resolve()
    try:
        artifact_key = artifact.relative_to(project_root).as_posix()
    except ValueError as exc:
        raise LedgerError(f"artifact is outside the project worktree: {artifact}") from exc
    if artifact_key not in ledger["artifacts"]:
        raise LedgerError(f"no accepted record to withdraw: {artifact_key}")

    # A record something else was accepted against cannot simply vanish: the remaining
    # records would name a dependency absent from the ledger, which `load_ledger` rejects,
    # and the ledger would no longer load at all.
    dependents = sorted(
        name for name, entry in ledger["artifacts"].items()
        if artifact_key in entry["depends_on"] and name != artifact_key
    )
    if dependents:
        raise LedgerError(
            f"cannot withdraw {artifact_key}: still a recorded dependency of "
            f"{', '.join(dependents)}. Withdraw or re-accept those first."
        )

    ledger["artifacts"].pop(artifact_key)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = ledger_path.with_name(ledger_path.name + ".tmp")
    tmp.write_text(canonical_ledger_text(ledger), encoding="utf-8")
    tmp.replace(ledger_path)
    load_ledger(ledger_path)

    return 0, {"ledger": str(ledger_path), "withdrawn": artifact_key,
               "remaining": sorted(ledger["artifacts"])}


# ---------------------------------------------------------------- cli


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("record", help="persist one already-accepted artifact (parent-owned)")
    rec.add_argument("--run-root", type=Path, required=True)
    rec.add_argument("--phase-id", required=True)
    rec.add_argument("--task-id", required=True)
    rec.add_argument("--artifact", type=Path, required=True)
    rec.add_argument("--depends-on", action="append", default=[],
                     help="an accepted artifact this one was reviewed against; repeatable")
    rec.add_argument("--ledger", type=Path, required=True)
    rec.set_defaults(handler=record)

    wd = sub.add_parser("withdraw", help="remove one accepted record (parent-owned)")
    wd.add_argument("--ledger", type=Path, required=True)
    wd.add_argument("--project-root", type=Path, required=True)
    wd.add_argument("--artifact", type=Path, required=True)
    wd.set_defaults(handler=withdraw)

    val = sub.add_parser("validate", help="derive artifact validity from content and closure")
    val.add_argument("--ledger", type=Path, required=True)
    val.add_argument("--project-root", type=Path, required=True)
    val.add_argument("--run-root", type=Path, default=None,
                     help="optional retained execution evidence; absence yields provenance=unavailable")
    val.set_defaults(handler=validate)
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        code, payload = args.handler(args)
    except LedgerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (ArtifactIdentityError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
