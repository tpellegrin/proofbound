#!/usr/bin/env python3
"""Materialise the two views of one working system that the modularity calibration compares.

The experiment asks whether a task whose responsibility lies outside a module can be done correctly
without reading that module's implementation. That only means something if the two arms are the same
system: the same application, the same tasks, the same public contract, and — decisively — the same
executed bytes. The only difference either arm may carry is whether the module's source is part of
the repository the agent explores.

So the module is materialised **outside** the workspace and imported from there in both arms, the
way any installed dependency is. `full` additionally carries a vendored copy of that source inside
the workspace, at a path that is not importable, so it can be read but cannot become a second
implementation that quietly drifts from the one under test.

Nothing here invokes a model. This module builds and describes the experimental object; measuring
with it is a later milestone.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

FIXTURE = Path(__file__).resolve().parent / "craft" / "modularity-local-reasoning" / "fixture"

FULL = "full"
CONTRACT = "contract"
ARMS = (FULL, CONTRACT)

# Where the vendored, readable copy sits in the `full` workspace. Deliberately not on `sys.path`:
# a readable copy that could also be imported would let the two arms execute different files.
VENDORED = Path("third_party") / "objectstore-1.4.0"

_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


class FixtureError(Exception):
    """The fixture could not be materialised as specified."""


def digest_tree(root: Path) -> str:
    """Content identity of a directory: every relative path and every byte under it."""
    h = hashlib.sha256()
    for path in sorted(p for p in Path(root).rglob("*")
                       if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"):
        h.update(path.relative_to(root).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii"))
        h.update(b"\0")
    return h.hexdigest()


def digest_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def materialise(arm: str, into: Path, *, fixture: Path = FIXTURE) -> dict[str, Any]:
    """Build one arm's workspace and the runtime the workspace imports.

    Returns the paths and identities a later milestone needs to prove the two arms were the same
    system: the workspace, the out-of-tree runtime, and hashes for each.
    """
    if arm not in ARMS:
        raise FixtureError(f"unknown arm: {arm!r}")
    into = Path(into)
    workspace = into / "workspace"
    runtime = into / "runtime"

    shutil.copytree(fixture / "base", workspace, ignore=_IGNORE)
    # Out of the workspace entirely, so exploring the repository does not reach it.
    shutil.copytree(fixture / "runtime", runtime, ignore=_IGNORE)

    if arm == FULL:
        source = fixture / "runtime" / "objectstore"
        target = workspace / VENDORED / "objectstore"
        shutil.copytree(source, target, ignore=_IGNORE)

    return {
        "arm": arm,
        "workspace": workspace,
        "runtime": runtime,
        "workspace_digest": digest_tree(workspace),
        "runtime_digest": digest_tree(runtime),
        "contract_sha256": digest_file(workspace / "docs" / "storage-contract.md"),
        "vendored_digest": (digest_tree(workspace / VENDORED / "objectstore")
                            if arm == FULL else None),
    }


def environment(built: dict[str, Any], *, data_root: Path | None = None) -> dict[str, str]:
    """The environment a workspace runs under: the module comes from outside the workspace."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(built["runtime"]).resolve())
    env["OBJECTSTORE_ROOT"] = str(Path(data_root or (Path(built["workspace"]).parent / "data")))
    env.pop("OBJECTSTORE_FLAKY_WRITES", None)
    return env


def run_tests(built: dict[str, Any], *, python: str | None = None,
              data_root: Path | None = None) -> subprocess.CompletedProcess:
    """Run the tests that ship with the workspace."""
    return subprocess.run(
        [python or sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=Path(built["workspace"]), env=environment(built, data_root=data_root),
        capture_output=True, text=True, check=False)


def run_gate(built: dict[str, Any], gate: Path, *, python: str | None = None,
             data_root: Path | None = None) -> subprocess.CompletedProcess:
    """Run one hidden gate against the workspace.

    Named and invoked explicitly rather than left to discovery: a gate whose filename does not match
    the discovery pattern is silently skipped, and a silently skipped correctness oracle reports
    success for work that was never done. It is copied in for the run and removed again, so no
    workspace an agent sees ever contains it.
    """
    workspace = Path(built["workspace"])
    target = workspace / "tests" / Path(gate).name
    target.write_bytes(Path(gate).read_bytes())
    try:
        return subprocess.run(
            [python or sys.executable, "-B", "-m", "unittest", f"tests.{target.stem}", "-v"],
            cwd=workspace, env=environment(built, data_root=data_root),
            capture_output=True, text=True, check=False)
    finally:
        target.unlink(missing_ok=True)


def arm_difference(full: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    """Every path present in one arm's workspace and not the other's.

    The experiment is only interpretable while this is exactly the vendored source. Anything else
    is a difference the agent could notice for reasons that have nothing to do with the hypothesis,
    so it is reported rather than assumed away.
    """
    def paths(built: dict[str, Any]) -> set[str]:
        root = Path(built["workspace"])
        return {p.relative_to(root).as_posix() for p in root.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}

    only_full = paths(full) - paths(contract)
    only_contract = paths(contract) - paths(full)
    vendored = VENDORED.as_posix() + "/"
    return {
        "only_full": sorted(only_full),
        "only_contract": sorted(only_contract),
        "unintended": sorted({p for p in only_full if not p.startswith(vendored)} | only_contract),
    }
