#!/usr/bin/env python3
"""The declared change graph: which artifacts constitute a change, and how they depend.

M2A's ledger records relationships that were already accepted. It has no notion of
completeness, because nothing ever declared what complete means: ask it whether a change's
engineering contract is finished and it has no opinion. This module supplies exactly that
missing statement, and nothing else.

    authority declares graph G  ->  Python proves the repository satisfies G

It never claims G was the *right* decomposition. That is semantic and stays with humans and
agents. Python compares declared paths against recorded paths; it does not know what a
"design" is, and there is deliberately no artifact kind anywhere in this file.

Two truth layers, kept in separate files:

    specs/<change>/graph.json    intended topology   (L1 intent)
    specs/<change>/ledger.json   accepted records    (L4 provenance)

The distinction this module exists to protect:

    artifact validity  !=  graph satisfaction

An artifact's M2A state describes that artifact. Graph satisfaction describes a topology.
Adding a sibling node leaves every existing artifact `valid`; only a change to a node's own
required dependency set may require its re-review, and that is reported as a *finding*,
never by mutating an M2A state.
"""
from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from _dag import CycleError, assert_acyclic

GRAPH_FORMAT = "proofbound-change-graph-v1"
# v1 semantics are exact: the declared nodes are exactly the change's contract-candidate
# artifacts and the declared edges are exactly the edges its members may record. A future
# v2 gets its own reader; it must never reinterpret a v1 file as a minimum graph.
SUPPORTED_GRAPH_FORMATS = (GRAPH_FORMAT,)

GRAPH_FIELDS = frozenset({"format", "artifacts"})

# Proofbound's own control files are never contract-candidate artifacts. Excluding them is
# not cosmetic: without it, a graph could be made permanently unsatisfiable by a record
# that no declaration is allowed to cover.
CONTROL_FILENAMES = frozenset({"graph.json", "ledger.json"})


class ChangeGraphError(ValueError):
    """The graph cannot be interpreted. Distinct from a graph that is merely unsatisfied."""


def _relative_path(raw: Any, label: str) -> str:
    """One repository-relative POSIX spelling per artifact.

    Alternate spellings are *rejected*, not normalized. Normalizing would let two
    declarations name one artifact, and the graph's membership set would stop being a set.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ChangeGraphError(f"{label} must be a non-empty string")
    if raw != raw.strip():
        raise ChangeGraphError(f"{label} has leading or trailing whitespace: {raw!r}")
    if "\\" in raw:
        raise ChangeGraphError(f"{label} must use POSIX separators: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or raw.endswith("/"):
        raise ChangeGraphError(f"unsafe or non-canonical {label}: {raw!r}")
    if path.as_posix() != raw:
        raise ChangeGraphError(f"{label} is not in canonical form: {raw!r}")
    return raw


def scope_of(graph_path: Path, project_root: Path) -> str:
    """The exactness scope: the graph file's own directory, project-relative.

    Derived rather than declared, so it cannot disagree with where the file actually lives.
    """
    try:
        rel = graph_path.resolve().relative_to(project_root.resolve())
    except ValueError as exc:
        raise ChangeGraphError(f"graph is outside the project: {graph_path}") from exc
    return rel.parent.as_posix()


def in_scope(path: str, scope: str) -> bool:
    """Path-segment containment, never a string prefix.

    `specs/CH-0012/x.md` must not fall inside `specs/CH-001/`, which a `startswith` test
    would get wrong.
    """
    if scope in ("", "."):
        return True
    scope_parts = PurePosixPath(scope).parts
    return PurePosixPath(path).parts[: len(scope_parts)] == scope_parts


def is_control_file(path: str) -> bool:
    return PurePosixPath(path).name in CONTROL_FILENAMES


def load_graph(path: Path, project_root: Path) -> dict[str, Any]:
    """Read and fully validate a graph declaration, failing closed on anything unrecognized."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ChangeGraphError(f"change graph missing: {path}") from exc
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ChangeGraphError(f"change graph unreadable: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ChangeGraphError("change graph must be a JSON object")

    fmt = raw.get("format")
    if fmt not in SUPPORTED_GRAPH_FORMATS:
        raise ChangeGraphError(f"unsupported change-graph format: {fmt!r}")
    unknown = sorted(set(raw) - GRAPH_FIELDS)
    if unknown:
        # v1 is strict. A field this version does not understand may carry meaning that
        # changes what the file requires, and silently ignoring it would misreport.
        raise ChangeGraphError(f"unknown change-graph field(s): {', '.join(unknown)}")

    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ChangeGraphError("change graph `artifacts` must be an object")

    scope = scope_of(path, project_root)
    members: dict[str, list[str]] = {}
    folded: dict[str, str] = {}
    for key, deps in artifacts.items():
        member = _relative_path(key, "artifact path")
        if is_control_file(member):
            raise ChangeGraphError(
                f"a change graph cannot declare a Proofbound control file as an artifact: {member}")
        if not in_scope(member, scope):
            raise ChangeGraphError(
                f"declared artifact is outside the graph's scope {scope!r}: {member}")
        if member in members:
            raise ChangeGraphError(f"duplicate artifact entry: {member}")
        lowered = member.lower()
        if lowered in folded:
            raise ChangeGraphError(
                f"artifact paths differ only by case and would be ambiguous on a "
                f"case-insensitive filesystem: {folded[lowered]} and {member}")
        folded[lowered] = member

        if not isinstance(deps, list):
            raise ChangeGraphError(f"{member}: dependency list must be an array")
        seen: list[str] = []
        for dep in deps:
            target = _relative_path(dep, f"{member}: dependency path")
            if target in seen:
                raise ChangeGraphError(f"{member}: duplicate dependency entry: {target}")
            if target == member:
                raise ChangeGraphError(f"{member}: artifact cannot depend on itself")
            seen.append(target)
        members[member] = sorted(seen)

    try:
        assert_acyclic(members)
    except CycleError as exc:
        raise ChangeGraphError(f"dependency cycle in change graph: {exc}") from exc

    return {"format": fmt, "scope": scope, "artifacts": members}


def canonical_graph_text(graph: dict[str, Any]) -> str:
    """Committed form. Deterministic, human-diffable, one edge per line."""
    return json.dumps({"format": graph["format"],
                       "artifacts": {k: sorted(v) for k, v in sorted(graph["artifacts"].items())}},
                      indent=2, sort_keys=True) + "\n"


def _finding(code: str, artifact: str, reason: str, related: list[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"code": code, "artifact": artifact, "reason": reason}
    if related:
        out["related"] = sorted(related)
    return out


def evaluate(graph: dict[str, Any], ledger: dict[str, Any],
             states: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare declared topology against accepted records. Returns findings, never state.

    `states` is M2A's derived artifact validity, passed in rather than recomputed — the
    graph reports artifact staleness, it never redefines it.
    """
    records = ledger["artifacts"]
    scope = graph["scope"]
    members = graph["artifacts"]
    findings: list[dict[str, Any]] = []

    for member in sorted(members):
        record = records.get(member)
        if record is None:
            # One clear finding beats a cascade of edge complaints about an artifact that
            # has never been accepted, so edge comparison is skipped for this member.
            findings.append(_finding(
                "missing-accepted-record", member,
                "declared by the graph but has no accepted record in the ledger"))
            continue

        state = states.get(member, {})
        if state.get("state") != "valid":
            findings.append(_finding(
                "artifact-not-valid", member,
                f"accepted artifact is {state.get('state')}: "
                f"{'; '.join(state.get('reasons') or []) or 'no reason recorded'}"))

        required = set(members[member])
        recorded = set(record["depends_on"])
        missing = required - recorded
        if missing:
            findings.append(_finding(
                "missing-required-edge", member,
                "accepted record does not depend on every artifact the graph requires",
                sorted(missing)))
        extra = recorded - required
        if extra:
            findings.append(_finding(
                "undeclared-edge", member,
                "accepted record depends on artifacts the graph does not declare",
                sorted(extra)))

    # Exactness, evaluated over accepted records inside the graph's scope — never over the
    # filesystem. An ordinary file in the directory was never accepted and is not a member.
    for path in sorted(records):
        if path in members or is_control_file(path) or not in_scope(path, scope):
            continue
        findings.append(_finding(
            "undeclared-member", path,
            f"accepted record lies in the graph's scope {scope!r} but the graph does not declare it"))

    # A dependency target must resolve to an accepted identity. A path merely existing in
    # the repository is not something an artifact can have been reviewed against.
    for member in sorted(members):
        for target in members[member]:
            if target not in members and target not in records:
                findings.append(_finding(
                    "unresolved-dependency-target", member,
                    "required dependency has no accepted record in this ledger", [target]))

    return findings
