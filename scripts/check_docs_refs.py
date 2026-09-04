#!/usr/bin/env python3
"""Validate the Proofbound architecture corpus.

The architecture is one corpus spread over several files so that a bounded task can read
only what applies to it. That split is only safe if two things stay true mechanically:

* every cross-document reference resolves — a link to a heading that no longer exists is
  worse than no link, because it reads as authority;
* every canonical identifier is defined exactly once, in its declared home — a principle
  silently dropped or duplicated during a file move is a real architectural regression,
  and prose review does not reliably catch it.

Stdlib only, no documentation toolchain. Exits non-zero and prints every failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs" / "architecture"
CORPUS = DOCS / "proofbound"

# Canonical homes. An identifier range is defined in exactly one file, and completely.
# Other documents may cite these identifiers freely; they may not redefine them.
CANONICAL = {
    "P": (CORPUS / "core-model.md", 13),
    "I": (CORPUS / "execution-and-review.md", 15),
    "T": (CORPUS / "long-running-autonomy.md", 10),
}

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*)$")
SECTION = re.compile(r"^#{2,3}\s+(\d+(?:\.\d+)?)\.?\s")
BARE_SECTION = re.compile(r"(?<!\[)§(\d+(?:\.\d+)?)(?!\]\()")


def slug(text: str) -> str:
    """GitHub's heading-anchor rule, reduced to what this corpus actually uses."""
    s = text.lower()
    s = "".join(c if (c.isalnum() or c in " -") else "" for c in s)
    return s.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = HEADING.match(line)
        if m:
            out.add(slug(m.group(1).strip()))
    return out


def markdown_files() -> list[Path]:
    return sorted(DOCS.rglob("*.md"))


def check_links(failures: list[str]) -> int:
    checked = 0
    cache: dict[Path, set[str]] = {}
    for f in markdown_files():
        for line_no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for target in LINK.findall(line):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                checked += 1
                rel, _, anchor = target.partition("#")
                dest = (f.parent / rel).resolve() if rel else f
                if not dest.is_file():
                    failures.append(f"{f.name}:{line_no}: link target missing: {target}")
                    continue
                if anchor:
                    if dest not in cache:
                        cache[dest] = anchors(dest)
                    if anchor not in cache[dest]:
                        failures.append(f"{f.name}:{line_no}: anchor not found: {target}")
    return checked


def check_canonical_identifiers(failures: list[str]) -> int:
    """Each range complete in its home, and defined nowhere else in the corpus."""
    checked = 0
    for prefix, (home, count) in CANONICAL.items():
        expected = {f"{prefix}{i}" for i in range(1, count + 1)}
        row = re.compile(rf"^\|\s*\**({prefix}\d+)\**\s*\|")
        found = [m.group(1) for line in home.read_text(encoding="utf-8").splitlines()
                 if (m := row.match(line))]
        checked += len(expected)
        missing = expected - set(found)
        if missing:
            failures.append(f"{home.name}: canonical {prefix} definitions missing: {sorted(missing)}")
        dupes = {x for x in found if found.count(x) > 1}
        if dupes:
            failures.append(f"{home.name}: canonical {prefix} defined more than once: {sorted(dupes)}")
        extra = set(found) - expected
        if extra:
            failures.append(f"{home.name}: unexpected {prefix} identifier: {sorted(extra)}")
        for other in CORPUS.rglob("*.md"):
            if other == home:
                continue
            here = [m.group(1) for line in other.read_text(encoding="utf-8").splitlines()
                    if (m := row.match(line))]
            if here:
                failures.append(
                    f"{other.relative_to(CORPUS)}: redefines canonical {prefix} identifiers "
                    f"{sorted(set(here))}; the only home is {home.name}"
                )
    return checked


def check_section_uniqueness(failures: list[str]) -> int:
    """Inherited §N identifiers must resolve to exactly one document."""
    seen: dict[str, Path] = {}
    for f in sorted(CORPUS.rglob("*.md")):
        for line in f.read_text(encoding="utf-8").splitlines():
            m = SECTION.match(line)
            if m:
                num = m.group(1)
                if num in seen:
                    failures.append(
                        f"section §{num} is defined in both {seen[num].name} and {f.name}")
                seen[num] = f
    return len(seen)


def check_link_syntax(failures: list[str]) -> int:
    """Reject malformed link syntax, not just unresolvable targets.

    A link whose text contains another link renders as literal brackets and reads as
    corruption. This check exists because an earlier automated reference rewrite emitted
    exactly that — and a checker that validated only link *targets* passed it, because the
    targets were fine. Validating that a reference resolves is not the same as validating
    that it is well formed.
    """
    checked = 0
    for f in markdown_files():
        for line_no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            stripped = re.sub(r"`[^`]*`", "", line)          # code spans may contain brackets
            for m in re.finditer(r"\[([^\]]*)\]\(", stripped):
                checked += 1
                if "[" in m.group(1):
                    failures.append(f"{f.name}:{line_no}: nested brackets in link text: {m.group(0)[:60]}")
            if "None[" in stripped:
                failures.append(f"{f.name}:{line_no}: literal 'None[' — a broken generated reference")
    return checked


def check_no_bare_cross_references(failures: list[str]) -> int:
    """A bare §N inside the corpus must belong to the document it appears in.

    A §N inside link text is not bare — `[core-model.md §33](...)` is a correct citation —
    so links are removed before scanning.
    """
    owner: dict[str, Path] = {}
    for f in sorted(CORPUS.rglob("*.md")):
        for line in f.read_text(encoding="utf-8").splitlines():
            m = SECTION.match(line)
            if m:
                owner[m.group(1)] = f
    checked = 0
    for f in sorted(CORPUS.rglob("*.md")):
        for line_no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("#"):
                continue
            line = LINK.sub("", line)
            for num in BARE_SECTION.findall(line):
                checked += 1
                home = owner.get(num) or owner.get(num.split(".")[0])
                if home is None:
                    # A reference to a section that no longer exists reads as authority and
                    # leads nowhere. Silently skipping it is how a split loses a rule.
                    failures.append(
                        f"{f.name}:{line_no}: §{num} refers to no section in the corpus")
                elif home != f:
                    failures.append(
                        f"{f.name}:{line_no}: bare §{num} refers to {home.name}; use a link")
    return checked


def main() -> int:
    failures: list[str] = []
    links = check_links(failures)
    ids = check_canonical_identifiers(failures)
    sections = check_section_uniqueness(failures)
    bare = check_no_bare_cross_references(failures)
    syntax = check_link_syntax(failures)

    print(f"links checked:              {links}")
    print(f"link syntax checked:        {syntax}")
    print(f"canonical identifiers:      {ids}")
    print(f"inherited sections indexed: {sections}")
    print(f"bare section references:    {bare}")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("\nOK: architecture corpus references are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
