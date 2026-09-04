#!/usr/bin/env python3
"""The closed Proofbound review-purpose vocabulary and its relation to worker roles.

Three concepts stay separate, and conflating any two of them is an architecture bug:

    purpose     why a review existed              declared by authority in the contract
    capability  whether a role can review at all  `_roles.INDEPENDENT_REVIEW_ROLES`
    role        which worker doctrine ran         recorded on the integrity gate

Several purposes map to a single qualifying role today. They are still separate names.
Collapsing them because the mechanics currently coincide would discard durable engineering
provenance and force historical retro-classification the first time a role is added — the
recorded reason for a review is not recoverable from the role that performed it.

What this table lets Python guarantee:

    the declared purpose was reviewed by a role authorized for that declared purpose

and nothing more. Whether the reflection was any good stays semantic.
"""
from __future__ import annotations

from _roles import INDEPENDENT_REVIEW_ROLES, ROLE_NAMES

# Closed vocabulary. An unknown declared purpose fails; it is never treated as a new
# purpose with no constraints. Additions are deliberate architecture decisions, and each
# new purpose must name at least one role that can already review independently.
REVIEW_PURPOSE_ROLES: dict[str, frozenset[str]] = {
    "proposal-reflection": frozenset({"spec-reflector"}),
    "design-reflection": frozenset({"spec-reflector"}),
    "specification-reflection": frozenset({"spec-reflector"}),
    "consistency-reflection": frozenset({"spec-reflector"}),
    "implementation-review": frozenset({"reviewer"}),
}

REVIEW_PURPOSES = tuple(REVIEW_PURPOSE_ROLES)


class ReviewPurposeError(ValueError):
    """A declared review purpose is unknown, or was satisfied by an unauthorized role."""


def _validate_table() -> None:
    """Fail at import if the table could ever authorize something meaningless.

    A purpose naming a role that does not exist, or one that cannot mechanically serve as
    an independent review, would let acceptance authorize the wrong thing on the strength
    of a typo.
    """
    for purpose, roles in REVIEW_PURPOSE_ROLES.items():
        if not roles:
            raise ValueError(f"review purpose has no qualifying role: {purpose}")
        for role in roles:
            if role not in ROLE_NAMES:
                raise ValueError(f"review purpose {purpose} names unknown role: {role}")
            if role not in INDEPENDENT_REVIEW_ROLES:
                raise ValueError(f"review purpose {purpose} names non-reviewing role: {role}")


_validate_table()


def normalize_purpose(raw: str) -> str:
    return str(raw or "").strip().lower()


def qualifying_roles(purpose: str) -> frozenset[str]:
    """Roles authorized to satisfy `purpose`; unknown purposes fail closed."""
    known = REVIEW_PURPOSE_ROLES.get(normalize_purpose(purpose))
    if known is None:
        raise ReviewPurposeError(
            f"unknown declared review purpose: {purpose!r}; "
            f"known purposes are {', '.join(REVIEW_PURPOSES)}"
        )
    return known


def assert_role_qualifies(purpose: str, role: str) -> None:
    """Objective check: did a role authorized for this declared purpose perform the review?"""
    allowed = qualifying_roles(purpose)
    actual = str(role or "").strip().lower()
    if actual not in allowed:
        raise ReviewPurposeError(
            f"declared review purpose {normalize_purpose(purpose)!r} requires role "
            f"{' or '.join(sorted(allowed))}, but the accepted integrity gate records role {actual!r}"
        )
