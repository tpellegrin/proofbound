#!/usr/bin/env python3
"""Single registry for DSD worker roles and objective project-write capabilities."""
from __future__ import annotations

ROLE_SKILLS = {
    "implementer": "roles/dsd-implementer/SKILL.md",
    "fixer": "roles/dsd-fixer/SKILL.md",
    "reviewer": "roles/dsd-reviewer/SKILL.md",
    "verification": "roles/dsd-verification/SKILL.md",
    "discovery": "roles/dsd-discovery/SKILL.md",
    "phase-surveyor": "roles/dsd-phase-surveyor/SKILL.md",
    "recovery": "roles/dsd-recovery/SKILL.md",
    "phase-auditor": "roles/dsd-phase-auditor/SKILL.md",
    "evidence-clerk": "roles/dsd-evidence-clerk/SKILL.md",
    # Append new roles only. Worker-rules manifests written before v3 recorded protocol
    # membership without its order, and their historical order is reconstructed from this
    # tuple restricted to what they recorded (see _rules_snapshot.recorded_protocol_order).
    "spec-author": "roles/dsd-spec-author/SKILL.md",
    "spec-reflector": "roles/dsd-spec-reflector/SKILL.md",
}

ROLE_NAMES = tuple(ROLE_SKILLS)
ALWAYS_PROJECT_WRITER_ROLES = frozenset({"implementer", "fixer", "spec-author"})
CONDITIONALLY_WRITING_ROLES = frozenset({"verification"})
ALWAYS_READ_ONLY_ROLES = frozenset(set(ROLE_NAMES) - set(ALWAYS_PROJECT_WRITER_ROLES) - set(CONDITIONALLY_WRITING_ROLES))

# Roles whose fresh, non-mutating attempt can satisfy the independent-review requirement for a
# recorded project mutation. This is a *capability*, not a purpose: implementation review and
# specification reflection share the same acceptance mechanics while keeping separate doctrine,
# and which of them a task warrants remains the parent's role choice, as it already is
# everywhere else. Membership here must stay narrow.
INDEPENDENT_REVIEW_ROLES = frozenset({"reviewer", "spec-reflector"})
