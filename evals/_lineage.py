#!/usr/bin/env python3
"""Where a piece of delivered text came from, when the path it arrived by no longer says.

MLR-C3D found the attribution instrument losing track of information it had already classified. An
agent read the module's source; the executor echoed that read into `worker.log`; the agent read the
log; and the log's path said `harness`. The bytes were implementation source and were counted as
something else. A second run listed the repository with `git ls-files` and the module's file names
were counted as behaviour.

Both are the same defect: **the measurement asked how text arrived and treated the answer as what
the text was.** Those are two questions. This module answers the first one — origin — so the route
can go back to answering only the second.

**How, and how far.** Not by information-flow analysis, which would be disproportionate. By content:
the module's own source lines are a fingerprint, and text that contains them verbatim carries
implementation source however it got there. That covers the routes an agent actually uses — a direct
read, a `grep` hit, a copy through `/tmp`, a log echo, `git show` — because all of them move the
bytes unchanged.

**What it deliberately does not cover.** Text *derived* from the implementation without reproducing
it — disassembly, `help()`, `vars()` — is not source and is not claimed as source; it keeps its own
origin. Paraphrase, summary and translation are invisible to this method, and are recorded as
unresolved rather than as zero when they carry other signs of disclosure. That boundary is stated
rather than hidden, because an instrument that quietly guessed would be the same failure again.

**Discrimination is measured, not assumed.** Against this fixture the module's 68 fingerprint lines
share nothing with the application, the tests, the contract, the task, the reference solution, the
hidden oracle or the worker protocol. A line has to be long enough to be distinctive before it is
allowed to identify anything.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

# Where information came from. Distinct from how it arrived, and never summed across kinds: source
# bytes, disassembly characters and file names are not exchangeable quantities.
IMPLEMENTATION_SOURCE = "implementation-source"
IMPLEMENTATION_RUNTIME = "implementation-runtime"
IMPLEMENTATION_METADATA = "implementation-metadata"
PUBLIC_CONTRACT = "public-contract"
APPLICATION = "application"
BEHAVIOUR = "behaviour"
HARNESS = "harness"
UNRESOLVED = "unresolved"
OTHER = "other"

ORIGINS = (IMPLEMENTATION_SOURCE, IMPLEMENTATION_RUNTIME, IMPLEMENTATION_METADATA,
           PUBLIC_CONTRACT, APPLICATION, BEHAVIOUR, HARNESS, UNRESOLVED, OTHER)

# The three kinds that carry the module's interior. Kept together for reporting and apart for
# accounting, because the paired question is precisely whether one replaces another.
IMPLEMENTATION_ORIGINS = (IMPLEMENTATION_SOURCE, IMPLEMENTATION_RUNTIME, IMPLEMENTATION_METADATA)

# A line shorter than this is not allowed to identify anything. `import hashlib` appears in the
# module and in a hundred other files; a twenty-four character line of its logic does not.
MIN_FINGERPRINT = 24


def source_fingerprint(source: Path) -> frozenset[str]:
    """The module's own source lines, as the marks by which its text is recognised elsewhere.

    Derived from the source that was compiled into the runtime, so it tracks the fixture rather than
    a list someone maintained. Stripped of leading and trailing space, because a copy through a log
    or a shell pipeline is frequently re-indented and the bytes are otherwise unchanged.
    """
    marks: set[str] = set()
    for module in sorted(Path(source).glob("*.py")):
        try:
            text = module.read_text(encoding="utf-8")
        except OSError:                                     # pragma: no cover - unreadable fixture
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if len(stripped) >= MIN_FINGERPRINT:
                marks.add(stripped)
    return frozenset(marks)


def source_in(text: str, marks: frozenset[str]) -> dict[str, Any]:
    """How much of this delivered text is verbatim module source, and which lines.

    Counted by line so a `grep` hit that returned four lines is charged for four lines, not for the
    file they came from. The matched text is returned as well: it is what identity is taken over, so
    that the same source replayed through three routes is one unique representation and three
    deliveries.
    """
    if not text or not marks:
        return {"bytes": 0, "lines": 0, "matched": ""}
    hit: list[str] = []
    for line in text.splitlines():
        for candidate in _candidates(line):
            if candidate in marks:
                hit.append(candidate)
                break
    if not hit:
        return {"bytes": 0, "lines": 0, "matched": ""}
    matched = "\n".join(hit)
    return {"bytes": len(matched.encode("utf-8")), "lines": len(hit), "matched": matched}


# Tools decorate the lines they return. `grep` prefixes `path:lineno:`, `cat -n` and OpenCode's own
# reader prefix a line number, and a diff prefixes a marker. The bytes after the decoration are still
# the module's source, so each plausible undecoration is tried before the line is dismissed.
_DECORATIONS = (
    re.compile(r"^[A-Za-z0-9_./\-]+\.py[:\-]\d+[:\-]\s?(?P<rest>.*)$"),   # grep -n / ripgrep
    re.compile(r"^[A-Za-z0-9_./\-]+\.py[:\-]\s?(?P<rest>.*)$"),             # grep without -n
    re.compile(r"^\s*\d+[:\|\t]\s?(?P<rest>.*)$"),                          # numbered readers
    re.compile(r"^[+\-> ]\s?(?P<rest>.*)$"),                                 # diff / quote markers
)


def _candidates(line: str) -> tuple[str, ...]:
    """The line as delivered, and as it reads once a tool's decoration is removed."""
    out = [line.strip()]
    for pattern in _DECORATIONS:
        match = pattern.match(line.rstrip("\n"))
        if match:
            rest = match.group("rest").strip()
            if rest and rest not in out:
                out.append(rest)
    return tuple(out)


def source_identity(matched: str) -> str:
    """Identity of matched source text, order-independent.

    Two deliveries of the same lines in a different order are the same information, and counting
    them as two unique representations would inflate exactly the number the experiment turns on.
    """
    lines = sorted(set(matched.splitlines()))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def module_paths(source: Path) -> tuple[str, ...]:
    """File names that reveal the module's structure without revealing its contents."""
    return tuple(sorted(p.name for p in Path(source).glob("*.py")))


_PATHISH = re.compile(r"[A-Za-z0-9_./\-]+\.py\b")


def metadata_in(text: str, names: Iterable[str], marker: str) -> dict[str, Any]:
    """References to the module's files that carry no source with them.

    A listing that names a module's private file discloses that the module has one. That is
    real information and it is not source, so it is counted in its own unit — references, and the
    bytes of the lines carrying them — and never added to a source total. `git ls-files` produces
    this; so does a `find`, a `glob`, and a traceback naming a file.
    """
    if not text:
        return {"bytes": 0, "references": 0, "names": []}
    wanted = set(names)
    seen: set[str] = set()
    hit: list[str] = []
    for line in text.splitlines():
        if marker not in line and not any(n in line for n in wanted):
            continue
        found = {Path(m).name for m in _PATHISH.findall(line)} & wanted
        if found:
            seen |= found
            hit.append(line.strip())
    if not hit:
        return {"bytes": 0, "references": 0, "names": []}
    return {"bytes": len("\n".join(hit).encode("utf-8")), "references": len(hit),
            "names": sorted(seen)}
