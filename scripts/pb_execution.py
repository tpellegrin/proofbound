#!/usr/bin/env python3
"""Authorize implementation work against an engineering candidate, and see what governs a run.

Two commands, and no new state behind either. `authorize` composes facts the freeze and
consistency layers already establish; `report` derives task bindings from the immutable
contracts a run already holds.

    authorize   may implementation work begin against this candidate now?
    report      which engineering candidate governs each task in this run?

`authorize` is a launch-time question. Once a task's immutable contract names a candidate,
that contract is the task's engineering authority for the rest of its life; nothing here
rechecks it at acceptance, and later movement of engineering intent never silently rebinds
running work.

Exit codes:

    2  inputs cannot be interpreted
    1  interpreted fine, but authorization is refused (or the run's bindings diverge)
    0  authorized (or a single consistent binding)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _artifact_identity import ArtifactIdentityError
from _change_graph import ChangeGraphError
from _consistency import ConsistencyError
from _contract import declared_candidate
from _execution import authorize as authorize_candidate
from _execution import bound_candidates
from _freeze import FreezeError
from pb_ledger import LedgerError


def authorize(args: argparse.Namespace) -> tuple[int, dict]:
    """Authorize the candidate a contract declares, or one named directly.

    Passing a contract is the normal path: it asks about the exact artifact that will
    become the task's immutable authority, and it fails closed when the contract declares
    no candidate — an inherited task that never went through Proofbound authorization.
    """
    candidate = args.candidate
    contract_path = None
    if args.contract is not None:
        contract_path = args.contract.resolve()
        try:
            declared = declared_candidate(contract_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConsistencyError(f"task contract unreadable: {contract_path}: {exc}") from exc
        if declared is None:
            return 1, {"authorized": False, "contract": str(contract_path), "candidate": None,
                       "findings": [{"code": "no-candidate-declared",
                                     "reason": "the contract declares no `## Proofbound "
                                               "candidate`, so it is not bound to an "
                                               "engineering candidate"}]}
        if candidate is not None and candidate != declared:
            return 1, {"authorized": False, "contract": str(contract_path),
                       "candidate": declared,
                       "findings": [{"code": "contract-candidate-mismatch",
                                     "reason": f"contract declares {declared[:12]}, but "
                                               f"{candidate[:12]} was requested"}]}
        candidate = declared

    result = authorize_candidate(
        candidate=candidate, graph_path=args.graph, ledger_path=args.ledger,
        project_root=args.project_root, consistency_dir=args.consistency,
        run_root=args.run_root.resolve() if args.run_root else None)
    if contract_path is not None:
        result["contract"] = str(contract_path)
    return (0 if result["authorized"] else 1), result


def report(args: argparse.Namespace) -> tuple[int, dict]:
    """Which candidate governs each task. Divergence is information, never a verdict."""
    result = bound_candidates(args.run_root)
    return (1 if result["divergent"] else 0), result


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)

    a = sub.add_parser("authorize", help="may implementation work begin against this candidate?")
    a.add_argument("--graph", type=Path, required=True)
    a.add_argument("--ledger", type=Path, required=True)
    a.add_argument("--project-root", type=Path, required=True)
    a.add_argument("--consistency", type=Path, required=True,
                   help="directory of consistency acceptance records")
    a.add_argument("--contract", type=Path, default=None,
                   help="task contract whose declared candidate is being authorized")
    a.add_argument("--candidate", default=None, help="candidate identity, if no contract yet")
    a.add_argument("--run-root", type=Path, default=None,
                   help="optional retained evidence; absence yields provenance=unavailable")
    a.set_defaults(handler=authorize)

    r = sub.add_parser("report", help="which candidate governs each task in this run")
    r.add_argument("--run-root", type=Path, required=True)
    r.set_defaults(handler=report)
    return ap


def main() -> int:
    args = parser().parse_args()
    if args.command == "authorize" and args.contract is None and args.candidate is None:
        print("ERROR: authorize needs --contract or --candidate", file=sys.stderr)
        return 2
    try:
        code, payload = args.handler(args)
    except (ConsistencyError, FreezeError, ChangeGraphError, LedgerError,
            ArtifactIdentityError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
