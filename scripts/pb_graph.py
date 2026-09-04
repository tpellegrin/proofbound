#!/usr/bin/env python3
"""Validate a declared change graph against the accepted artifact ledger.

One command, deliberately. M2B is not a workflow CLI: there is no `next`, no `schedule`,
no `approve`, no `plan`. Routing belongs to the parent, which reads findings and decides.

Exit codes distinguish two genuinely different situations, because automation must not
treat them alike:

    2  the graph or ledger cannot be interpreted  — malformed, unknown version, unsafe path
    1  interpreted fine, but the graph is not satisfied — incomplete or divergent topology
    0  satisfied

A malformed graph is not an incomplete engineering contract; it is a broken declaration.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _artifact_identity import ArtifactIdentityError
from _change_graph import ChangeGraphError, evaluate, load_graph
from pb_ledger import LedgerError, check_provenance, derive_states, load_ledger


def validate(args: argparse.Namespace) -> tuple[int, dict]:
    project_root = args.project_root.resolve()
    graph = load_graph(args.graph, project_root)
    ledger = load_ledger(args.ledger)
    run_root = args.run_root.resolve() if args.run_root else None

    states = derive_states(ledger, project_root)
    findings = evaluate(graph, ledger, states)
    provenance = check_provenance(ledger, run_root)

    # Artifact rows report M2A's own derived validity unchanged. The graph reports topology;
    # it never rewrites what an artifact's state means.
    artifacts = [
        {"path": path,
         "state": states[path]["state"],
         "reasons": states[path]["reasons"],
         "declared": path in graph["artifacts"],
         "provenance": provenance[path]["provenance"]}
        for path in sorted(states)
    ]
    result = {
        "graph": str(args.graph.resolve()),
        "ledger": str(args.ledger.resolve()),
        "format": graph["format"],
        "scope": graph["scope"],
        "project_root": str(project_root),
        "run_root": str(run_root) if run_root else None,
        "findings": findings,
        "artifacts": artifacts,
    }
    return (1 if findings else 0), result


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    val = sub.add_parser("validate", help="check the declared graph against accepted records")
    val.add_argument("--graph", type=Path, required=True)
    val.add_argument("--ledger", type=Path, required=True)
    val.add_argument("--project-root", type=Path, required=True)
    val.add_argument("--run-root", type=Path, default=None,
                     help="optional retained execution evidence; absence yields provenance=unavailable")
    val.set_defaults(handler=validate)
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        code, payload = args.handler(args)
    except (ChangeGraphError, LedgerError, ArtifactIdentityError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
