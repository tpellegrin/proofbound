#!/usr/bin/env python3
"""Export an authority-handoff run's evidence, and check it again after the run is gone.

    export   collect one condition's evidence into a relocatable package
    verify   recompute what a package supports — offline, read-only, no provider

`verify` never launches a model, never authorizes anything and never writes to a run tree. It may
re-run the bounded artifact checker over retained bytes, but only when asked: inspecting a package
must not execute code the package carries.

Examples:

    python3 evals/authority_slice/pb_evidence.py export \\
        --run-root <run> --into <package> --experiment pb-handoff-2 --condition valid \\
        --session-db <worker.db> --project <project>

    python3 evals/authority_slice/pb_evidence.py verify --package <package>
    python3 evals/authority_slice/pb_evidence.py verify --package <package> --recheck-artifact

Exit codes:

    2  the package cannot be read at all
    1  a check reported a mismatch
    0  no mismatch — which is not the same as "everything was verified"; read the kinds
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "evals"))

import _package                                                     # noqa: E402


def do_export(args: argparse.Namespace) -> int:
    config = None
    if args.config and Path(args.config).is_file():
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    result = _package.export(
        run_root=args.run_root, into=args.into, experiment=args.experiment,
        condition=args.condition, session_db=args.session_db, project=args.project,
        config=config, artifact=args.artifact, requirements=args.requirements,
        event_dirs=args.event_dir or None)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def do_adapt(args: argparse.Namespace) -> int:
    """One historical layout, read into a package. A narrow adapter, never a migration."""
    result = _package.adapt_handoff_1(args.condition_dir, args.into)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def do_qualify(args: argparse.Namespace) -> int:
    """Two predicates, reported apart. Exit 1 when either fails; a result, not an error."""
    report = _package.qualify(args.package, recheck_artifact=not args.no_recheck_artifact,
                              timeout=args.timeout)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["qualified"] else 1


def do_verify(args: argparse.Namespace) -> int:
    report = _package.verify(args.package, recheck_artifact=args.recheck_artifact,
                             timeout=args.timeout)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"package     {report['package']}")
        print(f"experiment  {report['experiment']} / {report['condition']}")
        print(f"produced by {report['produced_by'].get('adapter')} at "
              f"{str(report['produced_by'].get('harness_revision', {}).get('commit'))[:12]}")
        print()
        width = max(len(c["id"]) for c in report["checks"])
        for entry in report["checks"]:
            mark = {"ok": "  ", "mismatch": "!!", "unavailable": "··",
                    "reported": "››", "not-observed": "‑‑"}.get(entry["status"], "??")
            print(f"{mark} {entry['id']:<{width}}  {entry['kind']:<12} {entry['status']:<12} "
                  f"{entry['detail']}")
        print()
        print("  ".join(f"{k}={v}" for k, v in sorted(report["counts"].items())))
        print(report["note"])
    # Zero means "reported no mismatch". It does not mean the package established anything: a
    # package of nothing but `unavailable` exits zero too, which is why qualification reads the
    # required-observation predicate rather than this exit code.
    return 1 if report["counts"].get(_package.MISMATCH) else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    e = sub.add_parser("export", help="collect a condition's evidence into a package")
    e.add_argument("--run-root", type=Path, required=True)
    e.add_argument("--into", type=Path, required=True)
    e.add_argument("--experiment", required=True)
    e.add_argument("--condition", required=True)
    e.add_argument("--session-db", type=Path, default=None)
    e.add_argument("--project", type=Path, default=None)
    e.add_argument("--config", type=Path, default=None, help="the run-config.json this run used")
    e.add_argument("--artifact", type=Path, default=None)
    e.add_argument("--requirements", type=Path, default=None,
                   help="the accepted requirements the artifact checker consumed")
    e.add_argument("--event-dir", action="append", default=[],
                   help="restrict attribution to these attempts; repeatable")
    e.set_defaults(handler=do_export)

    a = sub.add_parser("adapt-handoff-1",
                       help="build a package from pb-handoff-1's retained evidence")
    a.add_argument("--condition-dir", type=Path, required=True,
                   help="evals/authority_slice/runs/pb-handoff-1/{valid,control}")
    a.add_argument("--into", type=Path, required=True)
    a.set_defaults(handler=do_adapt)

    q = sub.add_parser("qualify",
                       help="did this condition reach its declared outcome, with the evidence?")
    q.add_argument("--package", type=Path, required=True)
    q.add_argument("--no-recheck-artifact", action="store_true")
    q.add_argument("--timeout", type=float, default=10.0)
    q.set_defaults(handler=do_qualify)

    v = sub.add_parser("verify", help="recompute what a package supports, offline")
    v.add_argument("--package", type=Path, required=True)
    v.add_argument("--recheck-artifact", action="store_true",
                   help="run the bounded checker over the retained artifact bytes")
    v.add_argument("--timeout", type=float, default=5.0)
    v.add_argument("--json", action="store_true")
    v.set_defaults(handler=do_verify)

    args = ap.parse_args()
    try:
        return args.handler(args)
    except _package.PreservationFailure as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
