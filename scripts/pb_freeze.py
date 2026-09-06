#!/usr/bin/env python3
"""Derive, record and inspect durable engineering-contract identities.

Three commands, deliberately. A freeze is an *identity* primitive: it records which exact
engineering contract existed, and it authorizes nothing. There is no `approve`, `activate`,
`current`, `supersede` or `bind` here, and there is no persisted "current freeze" anywhere —
a later milestone will let a task contract name an exact freeze, which is a different thing.

    create    derive from a satisfied graph + ledger and write it, content-addressed
    validate  interpret a freeze from the file alone
    compare   ask whether the current project still produces this freeze

Exit codes separate genuinely different situations:

    2  the freeze, graph or ledger cannot be interpreted
    1  interpreted fine, but the current project has diverged from the freeze
    0  no findings
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _artifact_identity import ArtifactIdentityError
from _change_graph import ChangeGraphError
from _freeze import (FreezeError, canonical_freeze_text, compare, current_candidate,
                     freeze_identity, load_freeze, repository_findings)
from pb_ledger import LedgerError, check_provenance


def _candidate(args: argparse.Namespace) -> tuple[dict, dict, dict]:
    """Derive the current candidate from CLI arguments; the logic lives in `_freeze`."""
    return current_candidate(args.graph, args.ledger, args.project_root)


def create(args: argparse.Namespace) -> tuple[int, dict]:
    graph, ledger, candidate = _candidate(args)
    identity = freeze_identity(candidate)

    # Provenance is a creation *policy*, never an identity input: the bytes below are
    # derived from graph and ledger alone. `contradicted` means retained evidence actively
    # disagrees with durable provenance, so minting a new durable record from it would
    # launder a known inconsistency. Absent evidence is not disagreement, so `unavailable`
    # is allowed — an old repository must stay able to freeze.
    provenance = "unavailable"
    if args.run_root:
        statuses = {p["provenance"] for p in check_provenance(ledger, args.run_root.resolve()).values()
                    if p} or {"unavailable"}
        if "contradicted" in statuses:
            raise FreezeError(
                "refusing to create a freeze while retained evidence contradicts the accepted "
                "records it would bind; resolve the contradiction or drop the run tree first")
        provenance = "verified" if statuses == {"verified"} else "unavailable"

    out_dir = args.into.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{identity}.json"
    text = canonical_freeze_text(candidate)
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return 0, {"freeze": str(path), "identity": identity, "created": False,
                   "provenance": provenance}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    load_freeze(path)
    return 0, {"freeze": str(path), "identity": identity, "created": True,
               "provenance": provenance, "artifacts": sorted(candidate["artifacts"])}


def validate(args: argparse.Namespace) -> tuple[int, dict]:
    """Interpret a freeze from the file alone — no ledger, no graph, no run tree."""
    freeze = load_freeze(args.freeze)
    identity = freeze_identity(freeze)
    named = args.freeze.stem
    findings = []
    if len(named) == 64 and named != identity:
        findings.append({"code": "filename-identity-mismatch", "artifact": str(args.freeze),
                         "reason": f"file is named {named[:12]} but its content is {identity[:12]}"})
    return (1 if findings else 0), {
        "freeze": str(args.freeze.resolve()), "format": freeze["format"], "identity": identity,
        "artifacts": sorted(freeze["artifacts"]), "findings": findings}


def compare_cmd(args: argparse.Namespace) -> tuple[int, dict]:
    freeze = load_freeze(args.freeze)
    identity = freeze_identity(freeze)
    result = {"freeze": str(args.freeze.resolve()), "identity": identity,
              "repository": repository_findings(freeze, args.project_root.resolve())}

    # Candidate equivalence needs the graph and ledger; both may legitimately be gone. That
    # is reported as not-computable, never as the freeze being invalid.
    try:
        _graph, ledger, candidate = _candidate(args)
    except (ChangeGraphError, LedgerError, FreezeError) as exc:
        # Not computable is not equivalence. The freeze stays perfectly valid — its graph or
        # ledger is simply gone or diverged — but nothing here establishes that the project
        # still produces it, and reporting success would say exactly that.
        result["candidate"] = {"computable": False, "reason": str(exc)}
        result["provenance"] = "unavailable"
        findings = result["repository"] + [{
            "code": "candidate-not-computable", "artifact": str(args.freeze.resolve()),
            "reason": f"the current project cannot produce a contract candidate: {exc}"}]
        result["candidate"]["findings"] = findings[len(result["repository"]):]
    else:
        candidate_identity = freeze_identity(candidate)
        differences = compare(freeze, candidate)
        result["candidate"] = {"computable": True, "identity": candidate_identity,
                               "equivalent": candidate_identity == identity,
                               "findings": differences}
        statuses = {p["provenance"] for p in
                    check_provenance(ledger, args.run_root.resolve() if args.run_root else None).values()}
        result["provenance"] = ("contradicted" if "contradicted" in statuses
                                else "verified" if statuses == {"verified"} else "unavailable")
        findings = result["repository"] + differences
    return (1 if findings else 0), result


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    def sources(p):
        p.add_argument("--graph", type=Path, required=True)
        p.add_argument("--ledger", type=Path, required=True)
        p.add_argument("--project-root", type=Path, required=True)
        p.add_argument("--run-root", type=Path, default=None)

    c = sub.add_parser("create", help="derive and record a contract identity (parent-owned)")
    sources(c)
    c.add_argument("--into", type=Path, required=True, help="directory for content-addressed freezes")
    c.set_defaults(handler=create)

    v = sub.add_parser("validate", help="interpret a freeze from the file alone")
    v.add_argument("freeze", type=Path)
    v.set_defaults(handler=validate)

    k = sub.add_parser("compare", help="does the current project still produce this freeze?")
    k.add_argument("freeze", type=Path)
    sources(k)
    k.set_defaults(handler=compare_cmd)
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        code, payload = args.handler(args)
    except (FreezeError, ChangeGraphError, LedgerError, ArtifactIdentityError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
