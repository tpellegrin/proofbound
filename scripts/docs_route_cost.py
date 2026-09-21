#!/usr/bin/env python3
"""What each architecture reading route actually costs, computed from the files.

The entry point's "Read this if…" table tells a reader which documents a bounded task must ingest.
Those figures were hand-maintained and drifted badly: route A was displayed as ~28 KB while its
documents totalled 46,937 bytes, and route B2 as ~64 KB against an actual 100,963. A stale budget
is worse than no budget, because it is quoted in decisions about what to read.

So the figures are derived here and checked by the suite. `--check` fails when the table disagrees
with the filesystem; `--update` rewrites the column. Either way the number in the document is a
measurement, not a recollection.

    python3 scripts/docs_route_cost.py            # report every route and the corpus budget
    python3 scripts/docs_route_cost.py --check    # exit 1 if the entry point's figures are stale
    python3 scripts/docs_route_cost.py --update   # rewrite the figures in place

**What the figure is.** The unique bytes of the documents the route names, the entry point
included. Unique, because routes share documents and counting one twice would overstate a real
reader's cost. It is a byte count of required reading and nothing more: it does not predict an
agent's token usage, its context pressure, or how well it will do the task.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "docs" / "architecture" / "proofbound"
ENTRY = CORPUS / "README.md"

ROW = re.compile(r"^\|\s*\*\*([A-Z]\d?)\.\*\*\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")
LINK = re.compile(r"\[[^\]]*\]\(([^)#]+)[^)]*\)")

#: The cap the suite enforces on the entry point, mirrored here so one command reports the whole
#: budget picture. `tests/test_docs_architecture_refs.py` remains the authority.
ENTRY_CAP = 16_000
NORMATIVE_CAP = 40_000


def route_rows() -> list[dict]:
    """Every row of the entry point's routing table, with its documents resolved."""
    rows = []
    for line_no, line in enumerate(ENTRY.read_text(encoding="utf-8").splitlines(), 1):
        m = ROW.match(line)
        if not m:
            continue
        label, task, read, skip, shown = m.groups()
        docs: list[Path] = []
        if re.search(r"\bREADME\b", read):
            docs.append(ENTRY)
        for target in LINK.findall(read):
            dest = (ENTRY.parent / target).resolve()
            if dest.is_file() and dest not in docs:
                docs.append(dest)
        rows.append({"label": label, "task": task, "line": line_no, "read": read,
                     "skip": skip, "shown": shown, "docs": docs})
    return rows


def figure(docs: list[Path]) -> tuple[int, str]:
    """Unique bytes, and how the table should display them."""
    total = sum(len(d.read_bytes()) for d in dict.fromkeys(docs))
    return total, f"{total / 1000:.0f} KB"


def corpus_budget() -> dict:
    entry = len(ENTRY.read_bytes())
    normative = {d.name: len(d.read_bytes()) for d in sorted(CORPUS.glob("*.md"))
                 if d != ENTRY}
    evidence = {d.name: len(d.read_bytes())
                for d in sorted((CORPUS / "evidence").glob("*.md"))}
    return {
        "entry_point_bytes": entry,
        "entry_point_headroom": ENTRY_CAP - entry,
        "normative": normative,
        "tightest_normative": min((NORMATIVE_CAP - n, name) for name, n in normative.items()),
        "evidence_documents": len(evidence),
        "evidence_bytes": sum(evidence.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the displayed figures are stale")
    ap.add_argument("--update", action="store_true", help="rewrite the figures in the entry point")
    args = ap.parse_args()

    rows = route_rows()
    if not rows:
        print("no routing table found in the entry point", file=sys.stderr)
        return 2

    stale = []
    for row in rows:
        total, shown = figure(row["docs"])
        row["bytes"], row["computed"] = total, shown
        if shown not in row["shown"]:
            stale.append(row)

    if args.update:
        text = ENTRY.read_text(encoding="utf-8")
        for row in rows:
            old = f"| {row['shown']} |"
            new = f"| {row['computed']}{' + plan' if '+ plan' in row['shown'] else ''} |"
            # The cost cell is the row's last, so replace only that occurrence on that line.
            line = ENTRY.read_text(encoding="utf-8").splitlines()[row["line"] - 1]
            if old in line:
                text = text.replace(line, line[: line.rindex(old)] + new, 1)
        ENTRY.write_text(text, encoding="utf-8")
        print(f"updated {len(rows)} route figures in {ENTRY.relative_to(ROOT)}")
        return 0

    budget = corpus_budget()
    print(f"{'route':6} {'bytes':>8}  {'shown':>10}  documents")
    for row in rows:
        mark = "  " if row not in stale else "!!"
        names = ", ".join(d.name for d in row["docs"]) or "(none resolved)"
        print(f"{mark}{row['label']:4} {row['bytes']:8,}  {row['computed']:>10}  {names}")
    print(f"\nentry point: {budget['entry_point_bytes']:,} bytes, "
          f"{budget['entry_point_headroom']:,} of headroom under {ENTRY_CAP:,}")
    slack, tightest = budget["tightest_normative"]
    print(f"tightest normative document: {tightest} with {slack:,} of headroom under {NORMATIVE_CAP:,}")
    print(f"evidence: {budget['evidence_documents']} documents, "
          f"{budget['evidence_bytes']:,} bytes, read on demand and uncapped")

    if args.check and stale:
        print(f"\n{len(stale)} STALE ROUTE FIGURE(S):", file=sys.stderr)
        for row in stale:
            print(f"  route {row['label']}: shows {row['shown']!r}, computes to "
                  f"{row['computed']!r} ({row['bytes']:,} bytes)", file=sys.stderr)
        print("  run: python3 scripts/docs_route_cost.py --update", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
