#!/usr/bin/env python3
"""Parse only task-contract fields needed for objective DSD mechanics.

No helper here interprets acceptance quality or worker prose. The deterministic layer
may read explicit control fields such as write boundaries, protected ignored roots,
and optional proof-pattern loading hints.
"""
from __future__ import annotations

import re
from pathlib import PurePosixPath

from _roles import ALWAYS_PROJECT_WRITER_ROLES


def markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.I | re.M)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    nxt = re.search(r"^##\s+", text[start:], re.M)
    end = start + nxt.start() if nxt else len(text)
    return re.sub(r"<!--.*?-->", "", text[start:end], flags=re.S).strip()


def _safe_prefixes(text: str, heading: str, *, forbid_dsd: bool = False) -> list[str]:
    section = markdown_section(text, heading)
    if not section or section.strip().upper() == "NONE":
        return []
    result: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        value = stripped[1:].strip().strip("`").replace("\\", "/").rstrip("/")
        if not value or value.upper() == "NONE":
            continue
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {".", "./"}:
            raise ValueError(f"unsafe {heading} entry: {value}")
        normalized = path.as_posix()
        if forbid_dsd and (normalized == "DeepSeekAndDestroy" or normalized.startswith("DeepSeekAndDestroy/")):
            raise ValueError(f"{heading} cannot target DeepSeekAndDestroy/**")
        result.append(normalized)
    return list(dict.fromkeys(result))


def path_allowed(path: str, prefixes: list[str]) -> bool:
    """Whether one project-relative path falls inside a declared write boundary.

    Lives here because the prefixes it tests are produced by `_safe_prefixes` above; the
    two halves of the boundary rule belong in one module.
    """
    normalized = PurePosixPath(path.replace("\\", "/")).as_posix()
    return any(normalized == p or normalized.startswith(p.rstrip("/") + "/") for p in prefixes)


def _bullet_values(text: str, heading: str) -> list[str]:
    section = markdown_section(text, heading)
    if not section or section.strip().upper() == "NONE":
        return []
    out: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            value = stripped[1:].strip().strip("`")
            if value:
                out.append(value)
    return list(dict.fromkeys(out))


def has_explicit_write_restriction(text: str) -> bool:
    """Whether authority supplied an explicit project-write boundary.

    Implementer/Fixer contracts do not need to predict their implementation surface.
    When this section is present, however, it is a real hard restriction; `NONE`
    therefore means no project writes for that task.
    """
    return re.search(r"^##\s+Allowed source changes\s*$", text, re.I | re.M) is not None


def allowed_source_changes(text: str) -> list[str]:
    """Return an optional authority-supplied hard write restriction.

    An absent section means no predeclared restriction for inherent writer roles.
    A present `NONE` section is an explicit no-write restriction. Prose elsewhere
    never creates or widens this boundary.
    """
    return _safe_prefixes(text, "Allowed source changes")


def extra_scope_inventory(text: str) -> list[str]:
    return _safe_prefixes(text, "Extra scope inventory", forbid_dsd=True)


REVIEW_PURPOSE_HEADING = "Review purpose"


def declares_review_purpose(text: str) -> bool:
    """Whether authority declared a review purpose for this task.

    Absence is absence: inherited DSD contracts predate the field and keep their exact
    acceptance semantics. It is deliberately not a default, because a default purpose
    would be Python inventing the reason a review existed.
    """
    return re.search(rf"^##\s+{REVIEW_PURPOSE_HEADING}\s*$", text, re.I | re.M) is not None


def declared_review_purpose(text: str) -> str | None:
    """Return the single declared review purpose, or None when none was declared.

    Reuses the same bullet parser as every other explicit control field, so no second
    contract grammar enters the codebase. The purpose is read only from this exact
    section: prose, filenames and artifact paths never declare one. A present but
    unreadable section fails rather than degrading to "no purpose declared" — silently
    dropping the declaration is exactly how the guarantee would be lost.
    """
    if not declares_review_purpose(text):
        return None
    values = _bullet_values(text, REVIEW_PURPOSE_HEADING)
    if len(values) != 1:
        raise ValueError(
            f"## {REVIEW_PURPOSE_HEADING} must declare exactly one purpose as a single "
            f"list item; found {len(values)}"
        )
    purpose = values[0].strip().lower()
    if purpose == "none":
        # `NONE` means "explicitly nothing" elsewhere in the contract grammar. There is no
        # such thing as a review with explicitly no purpose: omit the section instead.
        raise ValueError(f"## {REVIEW_PURPOSE_HEADING} cannot be NONE; omit the section instead")
    return purpose


def proof_pattern_tags(text: str) -> list[str]:
    """Explicit loading hints only; tags are not acceptance semantics."""
    return _bullet_values(text, "Proof patterns")


def role_writes_project(role: str, text: str) -> bool:
    """Whether this exact role+contract may mutate accepted project state."""
    role = role.lower().replace("_", "-")
    if role in ALWAYS_PROJECT_WRITER_ROLES:
        return True
    if role == "verification":
        return bool(allowed_source_changes(text))
    # Evidence Clerk is always project-read-only. It may write DSD attempt artifacts,
    # never project state. Project documentation updates are ordinary writer tasks.
    return False


def validate_role_contract(role: str, text: str) -> list[str]:
    """Reserved for objective role/contract contradictions; currently none."""
    return []
