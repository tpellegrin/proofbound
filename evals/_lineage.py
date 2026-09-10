#!/usr/bin/env python3
"""What a delivered representation encodes, decided by the text and by nothing else.

An earlier version of this evaluation attributed information by asking how it arrived. An agent read
a module's source; the executor echoed that read into a log; the agent read the log; and the log's
path said the bytes were harness output. A later version asked what the text contained instead, and
promoted a model's own sentence to a file it had never opened because the sentence reproduced two
lines of that file exactly.

Both are the same confusion. **Where information came from, what it encodes, and how it reached the
reader are three questions.** This module answers only the second, and answers it as a decomposition:
of a delivered text, how many bytes are lines of a given source, how many are a machine rendering of
compiled code, how many are a rendering of live objects, how many are only file names, and how many
are none of those.

**How, and how far.** Not by information-flow analysis, which would be disproportionate. By content:
the given source's own lines are a fingerprint, and text containing them verbatim is source-shaped
however it got there. That covers the routes a tool-using agent actually produces — a direct read, a
search hit, a copy through a scratch file, a log echo, a version-control show — because all of them
move the bytes unchanged. Tool decorations are stripped before every test, not only before the source
test: a disassembly behind a line-numbering reader is still a disassembly, and an earlier version
missed exactly that.

**What it deliberately does not cover.** Paraphrase, summary and translation are invisible to this
method. A caller that needs to fail closed on them must do so on other evidence; nothing here reports
their absence as a zero.

**What content can and cannot settle.** Content equality establishes that two representations encode
the same thing, which is a fact about form. It does not establish that they came from the same place,
which is a fact about history. Two byte-identical texts can therefore have different origins, and
deciding origin is the caller's job — the caller is expected to outrank this module whenever it knows
the history.

**Discrimination is measured, not assumed.** A line must be long enough to be distinctive before it
is allowed to identify anything, and the caller's own tests are expected to prove that the marks it
supplies collide with nothing else it will classify.
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
# Text the model itself produced. It is an origin, not an absence of one: a model that reconstructs
# a source line from bytecode has authored that line, and calling it `other` loses the only fact
# that distinguishes reconstruction from a boundary failure.
MODEL_DERIVED = "model-derived"
UNRESOLVED = "unresolved"
OTHER = "other"

ORIGINS = (IMPLEMENTATION_SOURCE, IMPLEMENTATION_RUNTIME, IMPLEMENTATION_METADATA,
           PUBLIC_CONTRACT, APPLICATION, BEHAVIOUR, HARNESS, MODEL_DERIVED, UNRESOLVED, OTHER)

# The three kinds that carry the module's interior. Kept together for reporting and apart for
# accounting, because the paired question is precisely whether one replaces another.
IMPLEMENTATION_ORIGINS = (IMPLEMENTATION_SOURCE, IMPLEMENTATION_RUNTIME, IMPLEMENTATION_METADATA)

# A line shorter than this is not allowed to identify anything. `import hashlib` appears in the
# module and in a hundred other files; a twenty-four character line of its logic does not.
MIN_FINGERPRINT = 24


# What a delivered representation *encodes*, which is a different question from where it came from.
# The same form can be produced by different histories: source text can be read from a file or typed
# out by a model that only ever saw bytecode, and both are `source-form`.
SOURCE_FORM = "source-form"
DISASSEMBLY = "disassembly"
RUNTIME_STRUCTURE = "runtime-structure"
PATH_METADATA = "path-metadata"
OTHER_FORM = "other-representation"
MIXED_FORM = "mixed"

# The four substantive forms, in the order a line is tested against them. Source first because a
# module line is the most specific thing a line can be; `other` is not a member because it is the
# absence of the others rather than a finding.
SUBSTANTIVE_FORMS = (SOURCE_FORM, DISASSEMBLY, RUNTIME_STRUCTURE, PATH_METADATA)
FORMS = SUBSTANTIVE_FORMS + (OTHER_FORM, MIXED_FORM)

# A component is material at the size of one distinctive line. Any smaller floor would be a number
# with no derivation; any larger one would discard the 122 bytes that first made the distinction
# between source text and source-form reconstruction necessary.
MATERIAL_BYTES = MIN_FINGERPRINT

# CPython's disassembler prints an optional source line number, an optional jump marker, a byte
# offset and then the opcode in capitals. That shape is the body of a disassembly; the header lines
# around it name files and objects and are counted as what they are.
_OPCODE = re.compile(r"^(?:\d+\s+)?(?:>>\s+)?\d+\s+[A-Z][A-Z0-9_]{2,}(?:\s|$)")
_DIS_HEADER = re.compile(r"^Disassembly of ")

# Renderings of a live code object or namespace, as `dis`, `inspect`, `vars` and `dir` produce them.
_STRUCTURE_MARKERS = ("<code object ", "co_names", "co_consts", "co_varnames", "co_filename",
                      "co_argcount", "co_flags", "<function ", "<module ")


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


_PATHISH = re.compile(r"[A-Za-z0-9_./\-]+\.pyc?\b")


def module_reference(token: str, stems: "frozenset[str] | set[str]", marker: str) -> str | None:
    """Whether one path token names one of the given module's files, compiled or not.

    Stems rather than names, because a listing of a compiled file discloses the same structural fact
    as a listing of the source beside it, and an earlier version saw only the second. Qualified
    rather than bare, because a package's entry-point file is called the same thing in almost every
    package: a token counts only if it carries the module's own marker in its path, or if its stem is
    private and therefore distinctive on its own.
    """
    stem = Path(token).stem
    if stem not in stems:
        return None
    if marker and marker in token:
        return stem
    if stem.startswith("_") and not stem.startswith("__"):
        return stem
    return None


def metadata_in(text: str, names: Iterable[str], marker: str) -> dict[str, Any]:
    """References to the module's files that carry no source with them.

    A listing that names a module's private file discloses that the module has one. That is
    real information and it is not source, so it is counted in its own unit — references, and the
    bytes of the lines carrying them — and never added to a source total. `git ls-files` produces
    this; so does a `find`, a `glob`, and a traceback naming a file.
    """
    if not text:
        return {"bytes": 0, "references": 0, "names": []}
    # Reported as the module's own file, whichever of its forms was named: a listing of the
    # compiled file discloses that the module has that file, which is the fact being counted.
    by_stem = {Path(n).stem: n for n in names}
    stems = set(by_stem)
    seen: set[str] = set()
    hit: list[str] = []
    for line in text.splitlines():
        found = {by_stem[ref] for ref in (module_reference(tok, stems, marker)
                                          for tok in _PATHISH.findall(line)) if ref}
        if found:
            seen |= found
            hit.append(line.strip())
    if not hit:
        return {"bytes": 0, "references": 0, "names": []}
    return {"bytes": len("\n".join(hit).encode("utf-8")), "references": len(hit),
            "names": sorted(seen)}


def components(text: str, marks: frozenset[str], module_files: Iterable[str],
               name_pattern: "re.Pattern[str] | None" = None,
               marker: str = "") -> dict[str, Any]:
    """One delivered text, split by line into disjoint representation components.

    Every line lands in exactly one component, so the parts sum to the whole and no byte is counted
    twice. The order of the tests is the order of specificity: a line that is a module source line is
    that before it is anything else; a line of opcodes is a disassembly body; a line rendering a code
    object or naming several of the module's private bindings is runtime structure; a line whose only
    module content is a file name is metadata.

    Tool decorations are stripped before each test, not only before the source test. A disassembly
    read back through a numbered reader is still a disassembly, and the previous instrument missed
    exactly that: it undecorated for source and not for anything else, so 29,499 bytes of opcodes
    behind a `  1: ` prefix looked like unclassified text.
    """
    stems = {Path(n).stem for n in module_files}
    bytes_by: dict[str, int] = {form: 0 for form in SUBSTANTIVE_FORMS}
    bytes_by[OTHER_FORM] = 0
    lines_by: dict[str, list[str]] = {form: [] for form in bytes_by}
    for line in (text or "").splitlines():
        size = len(line.encode("utf-8")) + 1
        candidates = _candidates(line)
        form = None
        keep = line.strip()
        for candidate in candidates:
            if candidate in marks:
                form, keep = SOURCE_FORM, candidate
                break
        if form is None:
            if any(_OPCODE.match(c) or _DIS_HEADER.match(c) for c in candidates):
                form = DISASSEMBLY
            elif any(any(m in c for m in _STRUCTURE_MARKERS) for c in candidates) or (
                    name_pattern is not None
                    and len(set(name_pattern.findall(line))) >= 2):
                form = RUNTIME_STRUCTURE
            elif any(module_reference(tok, stems, marker) for tok in _PATHISH.findall(line)):
                form = PATH_METADATA
            else:
                form = OTHER_FORM
        bytes_by[form] += size
        lines_by[form].append(keep)
    total = sum(bytes_by.values())
    return {"total": total, "bytes": bytes_by, "lines": lines_by,
            "matched": "\n".join(lines_by[SOURCE_FORM]),
            "source_lines": len(lines_by[SOURCE_FORM])}


def form_of(comp: dict[str, Any]) -> str:
    """The single label that best describes a decomposed text, without discarding the rest.

    A form is claimed when it is most of what arrived. When two substantive components are each
    material and neither dominates, the honest label is `mixed` and the caller reads the components:
    forcing a header-plus-body item into one bucket is how a 3 KB header once hid a 29 KB body.
    """
    substantive = {f: comp["bytes"][f] for f in SUBSTANTIVE_FORMS}
    total = comp["total"]
    if not total:
        return OTHER_FORM
    top = max(substantive, key=lambda f: substantive[f])
    if substantive[top] * 2 >= total:
        return top
    if sum(1 for f, b in substantive.items() if b >= MATERIAL_BYTES) >= 2:
        return MIXED_FORM
    if substantive[top] >= MATERIAL_BYTES:
        return MIXED_FORM
    return OTHER_FORM


def component_identity(comp: dict[str, Any], form: str) -> str | None:
    """Identity of one component's lines, order-independent.

    The same disassembly written to a file and read back is the same information arriving twice. This
    is what lets a later delivery be recognised as a replay of an earlier one and inherit its origin,
    which is how a log echo keeps the history of the thing it echoes.
    """
    lines = comp["lines"].get(form) or []
    if not lines:
        return None
    if sum(len(l.encode("utf-8")) + 1 for l in lines) < MATERIAL_BYTES:
        return None
    return hashlib.sha256("\n".join(sorted(set(lines))).encode("utf-8")).hexdigest()
