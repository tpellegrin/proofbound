#!/usr/bin/env python3
"""The mechanical refusal controls for `pb-authority-demo-1`. Unpaid, and isolated.

Each control runs on its own fresh disposable copy, built by `scaffold.py setup` and driven to the
needed state by `rehearse.py`'s fake executor. Nothing here touches the live demonstration's run
tree, ledger, candidate or acceptance state.

**These show that mechanical gates refuse malformed authority. They say nothing about whether a
semantic reviewer can detect a defect** — a refusal is derived, a judgement is not, and conflating
the two would be the whole point missed.

The design named two controls and described them in terms that turned out not to match any
mechanism: *"change a declared member so the project derives C2; acceptance must refuse"*. It does
not. Acceptance staleness is measured against later **attempts** on the task, not against arbitrary
edits, and the project-no-longer-derives-the-candidate check lives in `pb_freeze compare`. So three
controls are exercised here, each against the mechanism that actually exists.

    python3 demo/pb-authority-demo-1/controls.py --into <scratch>
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(HERE))
import rehearse  # noqa: E402
import scaffold  # noqa: E402


def sh(argv: list[str], **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, check=False, **kw)


def fresh(into: Path, name: str) -> "rehearse.Rehearsal":
    """A disposable copy, driven to a completed design phase by the fake executor."""
    work = into / name
    shutil.rmtree(work, ignore_errors=True)
    scaffold.setup(work)
    sh(["git", "add", "-A"], cwd=work / "project")
    sh(["git", "commit", "-qm", "base"], cwd=work / "project")
    return rehearse.Rehearsal(work)


def control_stale_review(into: Path) -> dict[str, Any]:
    """A review that predates a later attempt on the task cannot be accepted.

    This is the real staleness mechanism: a reviewer's gate is evidence about the project as it was
    when the reviewer saw it, so a later producing attempt invalidates it.
    """
    r = fresh(into, "control-stale")
    r.bind("design", "RG-spec", r.contract("RG-spec"))
    author = r.work("design", "RG-spec", "spec-author")
    reflector = r.work("design", "RG-spec", "spec-reflector",
                       inputs=[author.parent / "report.md"])
    # The reviewer's gate is good right now.
    good = r.accept("design", "RG-spec", reflector)
    # A second producing attempt mutates the project after that review.
    author2 = r.work("design", "RG-spec", "spec-author",
                     inputs=[reflector.parent / "report.md"])
    stale = r.accept("design", "RG-spec", reflector)
    return {
        "control": "stale review",
        "accepted_while_fresh": good.returncode == 0,
        "refused_after_later_attempt": stale.returncode != 0,
        "refusal": (stale.stderr or stale.stdout).strip()[:200],
        "for_the_intended_reason": "predates later project mutation" in (stale.stderr + stale.stdout),
        "second_attempt": author2.parent.name,
    }


def control_wrong_candidate(into: Path) -> dict[str, Any]:
    """A review of one contract cannot be accepted for a task now bound to another.

    Candidate binding lives in the contract, and the whole contract file is hashed and bound at
    launch — so rebinding the task to a contract naming a different candidate invalidates the
    review that was produced under the old one.
    """
    r = fresh(into, "control-candidate")
    r.bind("design", "RG-spec", r.contract("RG-spec"))
    author = r.work("design", "RG-spec", "spec-author")
    reflector = r.work("design", "RG-spec", "spec-reflector",
                       inputs=[author.parent / "report.md"])

    # Rebind the task to a *different contract file* naming a different candidate. The gate the
    # reviewer produced records the contract path it ran under, so a task now bound to another
    # contract has no review of itself. Rewriting the same path in place does not demonstrate
    # this: `bind-contract` restores the recorded digest and the path never changes.
    #
    # The altered contract permits no project writes, which keeps it a review contract and keeps
    # this control about acceptance. A candidate-bearing contract that *did* permit writes would be
    # candidate-bound execution and would now be refused a step earlier, at admission, because the
    # fabricated candidate below is not what the project produces — a different fact, checked in
    # `tests/test_m4_admission.py`, not here.
    altered = r.contracts / "RG-spec-c2.md"
    altered.write_text(
        (HERE / "contracts" / "RG-spec.md").read_text(encoding="utf-8")
        .replace("## Allowed source changes\n- `spec.md`", "## Allowed source changes\nNONE")
        + "\n## Proofbound candidate\n- " + "c" * 64 + "\n", encoding="utf-8")
    r.bind("design", "RG-spec", altered)

    refused = r.accept("design", "RG-spec", reflector)
    return {
        "control": "wrong-candidate binding",
        "refused": refused.returncode != 0,
        "refusal": (refused.stderr or refused.stdout).strip()[:200],
        "for_the_intended_reason":
            "not bound to task.current_contract" in (refused.stderr + refused.stdout),
    }


def control_freeze_drift(into: Path) -> dict[str, Any]:
    """Once a member changes, the project no longer derives the accepted candidate.

    `pb_freeze compare` is where that is detected — not in acceptance, which is what the design
    assumed.
    """
    r = fresh(into, "control-drift")
    r.bind("design", "RG-spec", r.contract("RG-spec"))
    author = r.work("design", "RG-spec", "spec-author")
    reflector = r.work("design", "RG-spec", "spec-reflector",
                       inputs=[author.parent / "report.md"])
    r.accept("design", "RG-spec", reflector)
    sh([sys.executable, SCRIPTS / "pb_ledger.py", "record", "--run-root", r.run,
        "--phase-id", "design", "--task-id", "RG-spec", "--artifact", r.project / "spec.md",
        "--ledger", r.ledger])
    frozen = json.loads(sh([sys.executable, SCRIPTS / "pb_freeze.py", "create",
                            "--graph", r.graph, "--ledger", r.ledger,
                            "--project-root", r.project, "--into", r.freezes]).stdout)
    candidate = frozen.get("identity") or frozen.get("candidate")
    freeze_path = r.freezes / f"{candidate}.json"

    before = sh([sys.executable, SCRIPTS / "pb_freeze.py", "compare", freeze_path,
                 "--graph", r.graph, "--ledger", r.ledger, "--project-root", r.project])
    spec = r.project / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8") + "\nmutated after freezing\n",
                    encoding="utf-8")
    after = sh([sys.executable, SCRIPTS / "pb_freeze.py", "compare", freeze_path,
                "--graph", r.graph, "--ledger", r.ledger, "--project-root", r.project])
    return {
        "control": "freeze drift after a member changes",
        "candidate": candidate,
        "matched_before_mutation": before.returncode == 0,
        "refused_after_mutation": after.returncode != 0,
        "detail": (after.stdout or after.stderr).strip()[:300],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--into", type=Path, required=True)
    args = ap.parse_args()
    into = args.into.expanduser().resolve()
    into.mkdir(parents=True, exist_ok=True)
    results = [control_stale_review(into), control_wrong_candidate(into),
               control_freeze_drift(into)]
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if all(r.get("refused") or r.get("refused_after_later_attempt")
                    or r.get("refused_after_mutation") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
