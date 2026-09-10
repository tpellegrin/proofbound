#!/usr/bin/env python3
"""Whether the evidence a treatment withholds is reachable anyway.

An experiment that hides something has two conditions to meet, and only one of them is about the
prepared workspace. The other is about everywhere else the evaluated agent can look. A calibration
run learned this the expensive way: an arm whose workspace deliberately contained no implementation
source ran one ordinary search of the host filesystem, found a copy left behind by a materialisation
from a previous day, and read all four of the module's files. The workspace was exactly as designed.
The treatment had already failed.

So the condition is stated as what it is:

> The prepared workspace withholds the controlled evidence, **and** before execution no unintended
> alternative copy of that evidence — nor of the oracle, the reference solution, prior samples or
> earlier results — is reachable through the ordinary filesystem capabilities the agent is granted.

**This is experimental hermeticity, not system security.** It claims nothing about process
isolation, kernel boundaries, `/proc`, side channels, or an agent that is trying to escape. It
claims that ordinary engineering tools — a shell, a search, a read by absolute path — do not find a
second copy of what the experiment is controlling. An agent determined to defeat it can; that is not
the question this answers.

**Identity, not filename.** A directory whose name matches the controlled artefact is not a leak. A
file whose bytes are that artefact's bytes is. Names guide the search because reading every file on a
host would be absurd; content confirms it, because a name proves nothing either way.

**What is scanned is reported.** A scan that skips a reachable root and then reports "clean" is
worse than no scan, so the roots examined, the roots deliberately excluded and the paths that could
not be read are all part of the result. Absence is only ever claimed over what was actually looked
at.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Iterable

# What a finding is about. Evaluation-local categories, supplied with their identities by the caller.
CONTROLLED_EVIDENCE = "controlled-evidence"
ORACLE = "oracle"
REFERENCE = "reference-solution"
PRIOR_SAMPLE = "prior-sample"
RESULT_RECORD = "experiment-result"

CATEGORIES = (CONTROLLED_EVIDENCE, ORACLE, REFERENCE, PRIOR_SAMPLE, RESULT_RECORD)

# Outcomes. `declared` is not a pass: it is an exposure the experiment has written down and chosen
# to run with, and it is reported beside the findings so no reader mistakes silence for control.
CLEAN = "clean"
CONTAMINATED = "contaminated"
UNKNOWN = "unknown"

# How much of a fingerprint a file must carry before its content is taken as confirming its identity.
# One distinctive line is what the fingerprint machinery already treats as identifying; three is what
# separates a file that quotes the material from a file that is the material.
CONFIRMING_LINES = 3

# A scan reads a file only when its name invites reading. Reading every byte of every reachable root
# would be disproportionate and slow, and a name is a perfectly good index into a haystack as long as
# it is never the evidence.
MAX_CONFIRM_BYTES = 8_000_000


class Sensitive:
    """One category of evidence the experiment controls, and how to recognise a copy of it."""

    def __init__(self, category: str, *, stems: Iterable[str] = (), digests: Iterable[str] = (),
                 marks: "frozenset[str] | None" = None, path_markers: Iterable[str] = (),
                 contains: Iterable[bytes] = ()):
        self.category = category
        self.stems = frozenset(stems)
        self.digests = frozenset(digests)
        self.marks = marks or frozenset()
        self.path_markers = tuple(path_markers)
        # For artefacts that have no fixed bytes — a session database, a result record — but that
        # carry the experiment's own name inside them. Still content, still not the filename.
        self.contains = tuple(contains)

    def interesting(self, path: Path) -> bool:
        """Whether this path is worth opening. Names guide; they never decide."""
        if self.stems and path.name in self.stems:
            return True
        return any(marker in path.as_posix() for marker in self.path_markers)

    def confirms(self, path: Path) -> str | None:
        """Why this file is a copy of the controlled evidence, or nothing if it is not."""
        try:
            if path.stat().st_size > MAX_CONFIRM_BYTES:
                return None
            data = path.read_bytes()
        except OSError:
            return None
        if self.digests and hashlib.sha256(data).hexdigest() in self.digests:
            return "byte-identical to the controlled artefact"
        if self.marks:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                return None
            hit = sum(1 for line in text.splitlines() if line.strip() in self.marks)
            if hit >= CONFIRMING_LINES:
                return f"carries {hit} distinctive lines of the controlled artefact"
        for needle in self.contains:
            if needle in data:
                return f"contains the experiment marker {needle.decode('utf-8', 'replace')!r}"
        return None


def scan(roots: Iterable[Path], sensitive: Iterable[Sensitive], *,
         declared: Iterable[str] = (), excluded: Iterable[tuple[str, str]] = (),
         follow_symlinks: bool = False) -> dict[str, Any]:
    """Walk the given roots and report every reachable copy of the controlled evidence.

    `declared` paths are still found and still reported; they are separated from the findings because
    the experiment has already written them down. Declaring is not removing, and a declared exposure
    belongs in the frozen identity so it cannot be added quietly once a series is running.
    """
    sensitive = tuple(sensitive)
    declared_prefixes = []
    for entry in declared:
        try:
            declared_prefixes.append(str(Path(entry).resolve()))
        except OSError:                                     # pragma: no cover - unresolvable
            declared_prefixes.append(str(Path(entry)))
    declared_prefixes = tuple(declared_prefixes)
    findings: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    unreadable: list[str] = []
    scanned: list[str] = []
    seen_real: set[str] = set()

    def unreadable_hook(error: OSError) -> None:
        unreadable.append(str(getattr(error, "filename", error)))

    for root in roots:
        root = Path(root)
        try:
            resolved = root.resolve()
        except OSError:                                     # pragma: no cover - unresolvable root
            unreadable.append(str(root))
            continue
        if not resolved.exists():
            continue
        if str(resolved) in seen_real:
            continue
        seen_real.add(str(resolved))
        scanned.append(str(resolved))
        for parent, directories, files in os.walk(resolved, onerror=unreadable_hook,
                                                  followlinks=follow_symlinks):
            for name in files:
                path = Path(parent) / name
                for kind in sensitive:
                    if not kind.interesting(path):
                        continue
                    reason = kind.confirms(path)
                    if not reason:
                        continue
                    record = {"category": kind.category, "path": str(path), "basis": reason}
                    if str(path).startswith(declared_prefixes):
                        accepted.append(record)
                    else:
                        findings.append(record)
                    break

    status = CONTAMINATED if findings else (UNKNOWN if unreadable else CLEAN)
    return {
        "status": status,
        "findings": sorted(findings, key=lambda f: (f["category"], f["path"])),
        "declared_exposures": sorted(accepted, key=lambda f: (f["category"], f["path"])),
        "scanned_roots": sorted(scanned),
        "excluded_roots": [{"path": p, "reason": r} for p, r in excluded],
        "unreadable": sorted(set(unreadable))[:50],
        # Stated so no reader mistakes this for a claim about the whole machine. Absence is claimed
        # over the scanned roots and over nothing else.
        "claim": ("no unintended copy of the controlled evidence was found under the scanned roots; "
                  "nothing is claimed about roots that were excluded or could not be read"),
    }


def identity(sensitive: Iterable[Sensitive], roots: Iterable[Path],
             declared: Iterable[str] = ()) -> str:
    """What the hermeticity rule was, as one digest, so a series can prove which rule it ran under.

    Derived from the rule rather than from its outcome: which categories were checked, by which
    identities, over which roots, with which exposures declared. A run that widens the declared list
    or narrows the roots is running a different rule and gets a different identity.
    """
    h = hashlib.sha256()
    for kind in sorted(sensitive, key=lambda k: k.category):
        h.update(kind.category.encode("utf-8"))
        for part in (sorted(kind.stems), sorted(kind.digests), sorted(kind.marks),
                     sorted(kind.path_markers), sorted(kind.contains)):
            h.update(repr(part).encode("utf-8"))
        h.update(b"\0")
    h.update(repr(sorted(str(Path(r)) for r in roots)).encode("utf-8"))
    h.update(repr(sorted(str(Path(d)) for d in declared)).encode("utf-8"))
    return h.hexdigest()
