#!/usr/bin/env python3
"""Shared verification for immutable DSD worker-rules revisions."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Sequence

from _roles import ROLE_SKILLS

PROTOCOL_NAMES = (
    "COMMON.md",
    "PROOF-PATTERNS.md",
    *tuple(ROLE_SKILLS.values()),
)
MANIFEST_FORMAT = "dsd-worker-rules-manifest-v3"
# v2 recorded protocol membership but not its order; v3 records the order explicitly.
SUPPORTED_MANIFEST_FORMATS = ("dsd-worker-rules-manifest-v2", MANIFEST_FORMAT)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def protocol_fingerprint(protocol_dir: Path, names: Sequence[str] = PROTOCOL_NAMES) -> str:
    """Ordered fingerprint over an exact protocol sequence.

    The sequence matters: the same files in a different order produce a different
    fingerprint. Creation uses the current canonical order; verification uses the order
    the snapshot itself recorded (see `recorded_protocol_order`).
    """
    h = hashlib.sha256()
    for name in names:
        path = protocol_dir / name
        if not path.is_file():
            raise ValueError(f"worker protocol snapshot is incomplete: {path}")
        h.update(name.encode("utf-8")); h.update(b"\0")
        h.update(path.read_bytes()); h.update(b"\0")
    return h.hexdigest()


def recorded_protocol_order(recorded: dict[str, Any]) -> list[str]:
    """Return the protocol sequence a snapshot actually recorded.

    A snapshot is judged by its own recorded protocol identity, never by whatever the
    current registry contains, so adding roles cannot invalidate historical revisions.

    v3 manifests record the order explicitly. v2 manifests recorded only the membership
    map, which is serialized with `sort_keys=True` and therefore does **not** preserve the
    order the fingerprint was built from; for those, the order is reconstructed from the
    canonical registry order restricted to the recorded membership. That reconstruction is
    a hypothesis, not an assumption: `verify_snapshot` proves it by recomputing the
    recorded fingerprint and fails closed when it does not reproduce.
    """
    protocol = recorded.get("protocol")
    if not isinstance(protocol, dict) or not protocol:
        raise ValueError("worker-rules manifest lacks a recorded protocol map")
    if any(not isinstance(name, str) for name in protocol):
        raise ValueError("worker-rules manifest protocol map has a non-string entry")
    membership = set(protocol)
    explicit = recorded.get("protocol_names")
    if explicit is not None:
        if (
            not isinstance(explicit, list)
            or any(not isinstance(name, str) for name in explicit)
            or len(set(explicit)) != len(explicit)
            or set(explicit) != membership
        ):
            raise ValueError("worker-rules manifest protocol_names disagrees with its recorded protocol map")
        return list(explicit)
    return [n for n in PROTOCOL_NAMES if n in membership] + sorted(membership.difference(PROTOCOL_NAMES))


def revision_number(rules_path: Path) -> int:
    m = re.fullmatch(r"r(\d{4})", rules_path.parent.name)
    if not m or rules_path.name != "WORKER_RULES.md":
        raise ValueError(f"worker rules must identify worker-rules/rNNNN/WORKER_RULES.md: {rules_path}")
    return int(m.group(1))


def snapshot_payload(rules_path: Path, names: Sequence[str]) -> dict[str, Any]:
    """Observed snapshot facts, measured over exactly `names`."""
    rules_path = rules_path.resolve()
    revision = revision_number(rules_path)
    protocol_dir = rules_path.parent / "protocol"
    return {
        "revision": revision,
        "path": str(rules_path),
        "sha256": sha256_file(rules_path),
        "protocol_dir": str(protocol_dir.resolve()),
        "protocol_names": list(names),
        "protocol_fingerprint": protocol_fingerprint(protocol_dir, names),
        "protocol": {name: sha256_file(protocol_dir / name) for name in names},
    }


def current_payload(rules_path: Path) -> dict[str, Any]:
    """Facts for a snapshot being created now, under the current canonical registry."""
    return {"format": MANIFEST_FORMAT, **snapshot_payload(rules_path, PROTOCOL_NAMES)}


def verify_snapshot(rules_path: Path) -> dict[str, Any]:
    rules_path = rules_path.resolve()
    manifest_path = rules_path.parent / "MANIFEST.json"
    if not rules_path.is_file():
        raise ValueError(f"worker rules missing: {rules_path}")
    if not manifest_path.is_file():
        raise ValueError(f"worker-rules manifest missing: {manifest_path}")
    try:
        recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"worker-rules manifest unreadable: {exc}") from exc
    recorded_format = recorded.get("format")
    if recorded_format not in SUPPORTED_MANIFEST_FORMATS:
        raise ValueError(f"unsupported worker-rules manifest format: {recorded_format!r}")
    # Judge the snapshot by the protocol identity it recorded, then prove that identity by
    # reproducing its fingerprint. Membership, content, and order all remain adversarially
    # checked; only the assumption that the current registry equals the historical one is gone.
    names = recorded_protocol_order(recorded)
    actual = snapshot_payload(rules_path, names)
    for key in ("revision", "path", "sha256", "protocol_dir", "protocol_fingerprint", "protocol"):
        if recorded.get(key) != actual[key]:
            raise ValueError(f"immutable worker-rules revision changed after creation: {key} differs from manifest")
    return {
        "format": recorded_format,
        **actual,
        "manifest": str(manifest_path.resolve()),
        "manifest_sha256": sha256_file(manifest_path),
    }
