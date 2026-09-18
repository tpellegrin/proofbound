#!/usr/bin/env python3
"""Authorize implementation work against an engineering candidate, and see what governs a run.

Two commands, and no new state behind either. `authorize` composes facts the freeze and
consistency layers already establish; `report` derives task bindings from the immutable
contracts a run already holds.

    authorize   may implementation work begin against this candidate now?
    admit       authorize a candidate-bound implementation contract and bind it, in one act
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
from _contract import declared_candidate, requires_admission
from _execution import ADMISSION_FORMAT, authorize as authorize_candidate
from _execution import bound_candidates, build_admission
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


def admit(args: argparse.Namespace) -> tuple[int, dict]:
    """Authorize a candidate-bound implementation contract and bind it, in one atomic act.

    This is the supported transition at which an implementation task becomes admitted. Before it,
    nothing may launch against the contract; after it, the task carries an admission record naming
    exactly what was checked, and later attempts — review, repair, re-review — continue under that
    same authority without rechecking currentness (`freeze-and-binding.md` §A6.4).

    Authorization and binding are deliberately not two commands. A printed `authorized: true` is
    not evidence that a task was admitted, and a coordinator that had to carry one command's output
    into another's input would be the thing enforcing the rule.

    `--run-root` is always supplied here, so retained evidence is actually consulted: omitting it
    would silently downgrade provenance to `unavailable` and skip the contradiction check.
    """
    import dsd_state

    contract = args.contract.resolve()
    try:
        text = contract.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConsistencyError(f"task contract unreadable: {contract}: {exc}") from exc

    declared = declared_candidate(text)
    if declared is None:
        # An implementation request that names no candidate is refused, never quietly treated as
        # an inherited task. Downgrading here is exactly how the guarded path would be bypassed.
        return 1, {"admitted": False, "contract": str(contract), "candidate": None,
                   "findings": [{"code": "no-candidate-declared",
                                 "reason": "this contract declares no `## Proofbound candidate`, "
                                           "so there is nothing to admit. An inherited task with "
                                           "no candidate binds with `dsd_state.py bind-contract` "
                                           "and keeps its documented semantics."}]}
    if not requires_admission(text):
        return 1, {"admitted": False, "contract": str(contract), "candidate": declared,
                   "findings": [{"code": "not-candidate-bound-execution",
                                 "reason": "this contract names a candidate but declares no "
                                           "project writes, so it is upstream review work and is "
                                           "bound with `dsd_state.py bind-contract`."}]}

    # Authorizing against one project while the run mutates another would produce a record that is
    # internally consistent and about the wrong thing. The launch would catch it — as
    # `admission-project-mismatch`, at a point where the cause is no longer visible — so it is
    # caught here, where the wrong argument was given.
    run_project = dsd_state.project_root_from_run(
        args.run_root.resolve(), dsd_state.load_json(args.run_root.resolve() / "state.json"))
    if run_project != args.project_root.resolve():
        return 1, {"admitted": False, "contract": str(contract), "candidate": declared,
                   "findings": [{"code": "project-not-this-run",
                                 "reason": f"--project-root is {str(args.project_root)!r}, but this "
                                           f"run mutates {str(run_project)!r}"}]}

    verdict = authorize_candidate(
        candidate=declared, graph_path=args.graph, ledger_path=args.ledger,
        project_root=args.project_root, consistency_dir=args.consistency,
        run_root=args.run_root)
    if not verdict["authorized"]:
        # Nothing is bound and nothing is recorded. A refused admission must not leave state that
        # a later resume could read as permission.
        return 1, {"admitted": False, "contract": str(contract), **verdict}

    admission = build_admission(
        candidate=declared, contract_path=contract, contract_sha256=dsd_state.sha256(contract),
        project_root=args.project_root.resolve(), authorization=verdict,
        graph_path=args.graph, ledger_path=args.ledger, consistency_dir=args.consistency)
    bound = dsd_state.bind_contract_core(
        run_root=args.run_root, phase_id=args.phase_id, task_id=args.task_id, contract=contract,
        status=args.status, next_action=args.next_action,
        supersede_incomplete=args.supersede_incomplete, admission=admission)
    return 0, {"admitted": True, "format": ADMISSION_FORMAT, **verdict, **bound}


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

    m = sub.add_parser("admit", help="authorize a candidate-bound contract and bind it to its task")
    m.add_argument("--run-root", type=Path, required=True)
    m.add_argument("--phase-id", required=True)
    m.add_argument("--task-id", required=True)
    m.add_argument("--contract", type=Path, required=True)
    m.add_argument("--graph", type=Path, required=True)
    m.add_argument("--ledger", type=Path, required=True)
    m.add_argument("--project-root", type=Path, required=True)
    m.add_argument("--consistency", type=Path, required=True,
                   help="directory of consistency acceptance records")
    m.add_argument("--status", default="prepared")
    m.add_argument("--next-action", default=None)
    m.add_argument("--supersede-incomplete", action="store_true")
    m.set_defaults(handler=admit)

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
