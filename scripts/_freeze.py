#!/usr/bin/env python3
"""The freeze: one durable identity for an exact engineering contract.

M2B proves a topology is satisfied *now*, and that proof evaporates. The ledger is a
current snapshot whose records are overwritten by re-acceptance and removable by
withdrawal; the graph is an editable file. Nothing else in Proofbound can say which exact
engineering contract existed at a moment, once either has moved.

The fact that makes this a distinct milestone rather than a hash of the artifacts: content
identity cannot express an accepted relationship. Let B's bytes be `H_B`, accepted against
`{A: H1}`. Later authority requires `B -> {A, C}` and B is re-accepted byte-identically.
`content_sha256` is `H_B` in both worlds, and a record binding only content would silently
mean the wrong contract.

So a binding is content **plus** the exact accepted dependency identities **plus** the
semantic review purpose — and deliberately nothing else. Role, gate and attempt are
execution mechanics (`L3`, deletable, run-relative); binding them would make engineering
identity depend on ephemeral machine-local state and would churn the contract every time
an equivalent fresh review happened. Graph identity is redundant: for a satisfied graph the
required and recorded edges are equal in both directions, so the copied dependency maps
*are* the topology.

A freeze **copies** its bindings and is thereafter self-contained: it needs no ledger, no
graph and no run tree to state what it requires. That is the whole point — a reference into
the mutable ledger could be rewritten later, which is the retroactive mutation freeze exists
to prevent.

What a freeze is *not*: an authorization to execute, or a claim that the contract is
semantically coherent. A mechanically satisfied graph of individually reflected artifacts
can still contradict itself. That challenge is a separate milestone.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from _dag import CycleError, assert_acyclic

FREEZE_FORMAT = "proofbound-freeze-v1"
SUPPORTED_FREEZE_FORMATS = (FREEZE_FORMAT,)

FREEZE_FIELDS = frozenset({"format", "artifacts"})
BINDING_FIELDS = frozenset({"content_sha256", "depends_on", "review_purpose"})

# Pinned by v1, deliberately NOT read from `_review_purpose.REVIEW_PURPOSE_ROLES`.
# A v1 freeze must keep meaning what it meant even after the live registry gains or loses a
# purpose; resolving history through today's table is exactly the M0 failure. Freeze
# validation never re-authorizes purpose against roles either — authorization already
# happened at acceptance, and a freeze only records which purpose it was.
V1_REVIEW_PURPOSES = frozenset({
    "proposal-reflection",
    "design-reflection",
    "specification-reflection",
    "consistency-reflection",
    "implementation-review",
})

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class FreezeError(ValueError):
    """A freeze cannot be interpreted. Distinct from a project that no longer matches one."""


# ---------------------------------------------------------------- bindings


def binding_of(record: dict[str, Any]) -> dict[str, Any]:
    """The engineering meaning of one accepted ledger record.

    Keeps content, dependencies and purpose. Drops role, gate and attempt — see the module
    docstring for why those are execution mechanics rather than engineering identity.
    """
    review = record.get("review") or {}
    return {
        "content_sha256": record["content_sha256"],
        "depends_on": dict(record["depends_on"]),
        "review_purpose": review.get("purpose"),
    }


# ---------------------------------------------------------------- canonical form


def canonical_freeze_text(freeze: dict[str, Any]) -> str:
    """The one v1 serialization. Its bytes define the identity, so this *is* protocol.

    Every ordering input is made explicit rather than inherited from dictionary insertion
    order, which is a language guarantee and not a wire format. M0's snapshot fingerprint
    recorded membership but not the order its identity depended on; that is not repeated.
    """
    artifacts = {
        path: {
            "content_sha256": entry["content_sha256"],
            "depends_on": {dep: entry["depends_on"][dep] for dep in sorted(entry["depends_on"])},
            "review_purpose": entry["review_purpose"],
        }
        for path in sorted(freeze["artifacts"])
        for entry in (freeze["artifacts"][path],)
    }
    return json.dumps({"format": freeze["format"], "artifacts": artifacts},
                      indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def freeze_identity(freeze: dict[str, Any]) -> str:
    """SHA-256 over the canonical bytes. No stored self-hash: it could only disagree."""
    return hashlib.sha256(canonical_freeze_text(freeze).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- validation


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _HEX64.match(value):
        raise FreezeError(f"{label} is not a lowercase hex SHA-256: {value!r}")
    return value


def _path(raw: Any, label: str) -> str:
    """One repository-relative POSIX spelling. Alternates are rejected, never normalized.

    Historical freeze identity depends on exact path bytes, so accepting two spellings for
    one artifact would make two different identities mean the same contract.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise FreezeError(f"{label} must be a non-empty string")
    if raw != raw.strip() or "\\" in raw or raw.endswith("/"):
        raise FreezeError(f"unsafe or non-canonical {label}: {raw!r}")
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts or "." in p.parts or p.as_posix() != raw:
        raise FreezeError(f"unsafe or non-canonical {label}: {raw!r}")
    return raw


def load_freeze(path: Path) -> dict[str, Any]:
    """Read and fully validate a freeze **from the file alone**.

    Deliberately consults no ledger, no graph and no run tree. If internal validity depended
    on current state, withdrawing a record would retroactively make a historical freeze
    "invalid", which is the exact failure the copy-don't-reference rule prevents.
    """
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FreezeError(f"freeze missing: {path}") from exc
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FreezeError(f"freeze unreadable: {path}: {exc}") from exc
    return load_freeze_object(raw)


def load_freeze_object(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise FreezeError("freeze must be a JSON object")
    fmt = raw.get("format")
    if fmt not in SUPPORTED_FREEZE_FORMATS:
        raise FreezeError(f"unsupported freeze format: {fmt!r}")
    unknown = sorted(set(raw) - FREEZE_FIELDS)
    if unknown:
        raise FreezeError(f"unknown freeze field(s): {', '.join(unknown)}")

    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, dict):
        raise FreezeError("freeze `artifacts` must be an object")

    members: dict[str, Any] = {}
    folded: dict[str, str] = {}
    for key, entry in artifacts.items():
        member = _path(key, "artifact path")
        if member in members:
            raise FreezeError(f"duplicate artifact entry: {member}")
        lowered = member.lower()
        if lowered in folded:
            raise FreezeError(
                f"artifact paths differ only by case and would be ambiguous on a "
                f"case-insensitive filesystem: {folded[lowered]} and {member}")
        folded[lowered] = member

        if not isinstance(entry, dict):
            raise FreezeError(f"{member}: binding must be an object")
        missing = sorted(BINDING_FIELDS - set(entry))
        if missing:
            raise FreezeError(f"{member}: binding is missing {', '.join(missing)}")
        extra = sorted(set(entry) - BINDING_FIELDS)
        if extra:
            raise FreezeError(f"{member}: unknown binding field(s): {', '.join(extra)}")

        content = _digest(entry["content_sha256"], f"{member}: content_sha256")
        purpose = entry["review_purpose"]
        if purpose not in V1_REVIEW_PURPOSES:
            raise FreezeError(
                f"{member}: review purpose is not in the freeze v1 vocabulary: {purpose!r}")
        deps_raw = entry["depends_on"]
        if not isinstance(deps_raw, dict):
            raise FreezeError(f"{member}: `depends_on` must be an object")
        deps: dict[str, str] = {}
        for dep_key, dep_hash in deps_raw.items():
            target = _path(dep_key, f"{member}: dependency path")
            if target == member:
                raise FreezeError(f"{member}: artifact cannot depend on itself")
            deps[target] = _digest(dep_hash, f"{member}: dependency {target}")
        members[member] = {"content_sha256": content, "depends_on": deps,
                           "review_purpose": purpose}

    # A dependency on a *member* must name that member's frozen content. A target that is
    # not a member is external context the contract was reviewed against — legal, and its
    # own binding belongs to whatever contract declared it (see the module docstring).
    for member, entry in members.items():
        for target, digest in entry["depends_on"].items():
            if target in members and members[target]["content_sha256"] != digest:
                raise FreezeError(
                    f"{member}: frozen dependency identities disagree — depends on {target}@"
                    f"{digest[:12]} but that member is frozen at "
                    f"{members[target]['content_sha256'][:12]}")

    try:
        assert_acyclic({m: list(e["depends_on"]) for m, e in members.items()})
    except CycleError as exc:
        raise FreezeError(f"dependency cycle in freeze: {exc}") from exc

    return {"format": fmt, "artifacts": members}


# ---------------------------------------------------------------- derivation


def derive(graph: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    """Build the freeze for a satisfied graph from currently accepted records.

    Members are exactly the graph's declared artifacts — no transitive closure. Graph
    membership *is* authority's statement of what constitutes this contract; pulling in
    dependency targets would put artifacts into the frozen contract that no authority
    declared, inferring membership from structure instead of from declaration.

    Callers must confirm graph satisfaction first (`pb_graph`), which is what guarantees the
    recorded dependency maps equal the required topology — and therefore that copying the
    ledger's `depends_on` captures the declared shape without the graph being copied.
    """
    records = ledger["artifacts"]
    artifacts: dict[str, Any] = {}
    for member in sorted(graph["artifacts"]):
        record = records.get(member)
        if record is None:
            raise FreezeError(f"cannot freeze: {member} has no accepted record")
        artifacts[member] = binding_of(record)
    freeze = {"format": FREEZE_FORMAT, "artifacts": artifacts}
    # Prove the result is loadable under its own schema before anyone sees it, so a
    # malformed record can never become a persisted freeze.
    return load_freeze_object(json.loads(canonical_freeze_text(freeze)))


def compare(freeze: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Differences between a freeze and a freshly derived candidate, as findings.

    Compares engineering meaning only. Role, gate and attempt are absent from both sides by
    construction, so an equivalent fresh re-review produces no findings at all.
    """
    out: list[dict[str, Any]] = []
    frozen, current = freeze["artifacts"], candidate["artifacts"]
    for path in sorted(set(frozen) | set(current)):
        if path not in current:
            out.append({"code": "member-removed", "artifact": path,
                        "reason": "frozen artifact is no longer a member of the current contract"})
            continue
        if path not in frozen:
            out.append({"code": "member-added", "artifact": path,
                        "reason": "current contract has an artifact the freeze does not bind"})
            continue
        was, now = frozen[path], current[path]
        if was["content_sha256"] != now["content_sha256"]:
            out.append({"code": "content-differs", "artifact": path,
                        "reason": f"accepted content moved from {was['content_sha256'][:12]} "
                                  f"to {now['content_sha256'][:12]}"})
        if was["depends_on"] != now["depends_on"]:
            out.append({"code": "dependencies-differ", "artifact": path,
                        "reason": "the accepted dependency identities differ from the frozen set"})
        if was["review_purpose"] != now["review_purpose"]:
            out.append({"code": "purpose-differs", "artifact": path,
                        "reason": f"accepted under {now['review_purpose']!r}, "
                                  f"frozen under {was['review_purpose']!r}"})
    return out


def repository_findings(freeze: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    """Whether current files still carry the frozen content identities.

    A separate question from candidate equivalence: the ledger can still agree with a freeze
    while the working tree has drifted, and vice versa.
    """
    from _artifact_identity import ArtifactIdentityError, artifact_identity_file

    out: list[dict[str, Any]] = []
    for path in sorted(freeze["artifacts"]):
        target = Path(project_root) / path
        if not target.is_file():
            out.append({"code": "missing-artifact", "artifact": path,
                        "reason": "frozen artifact is not present in the working tree"})
            continue
        try:
            current = artifact_identity_file(target)
        except ArtifactIdentityError as exc:
            out.append({"code": "unreadable-artifact", "artifact": path, "reason": str(exc)})
            continue
        if current != freeze["artifacts"][path]["content_sha256"]:
            out.append({"code": "content-mismatch", "artifact": path,
                        "reason": f"working tree holds {current[:12]}, freeze binds "
                                  f"{freeze['artifacts'][path]['content_sha256'][:12]}"})
    return out
