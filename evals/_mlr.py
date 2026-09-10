#!/usr/bin/env python3
"""Materialise the two views of one working system that the modularity calibration compares.

The experiment asks whether a task whose responsibility lies outside a module can be done correctly
without reading that module's implementation. That only means something if the two arms are the same
system: the same application, the same tasks, the same public contract, and — decisively — the same
executed bytes. The only difference either arm may carry is whether the module's source is part of
the repository the agent explores.

So the module is materialised **outside** the workspace, compiled, and imported from there in both
arms, the way an installed closed-source dependency is. `full` additionally carries a readable copy
of the source inside the workspace, at a path that is not importable, so it can be read but cannot
become a second implementation that quietly drifts from the one under test.

Compiling it is what makes the treatment real. MLR-C1 shipped the runtime as source and measurement
validation then found that `contract` recovered the whole implementation with one call to
`inspect.getsource`: repository absence is friction, not an information boundary. The runtime is now
bytecode, compiled at materialisation by the interpreter that will execute it — which is also why
the version incompatibility that ruled this out earlier does not arise, since nothing compiled is
ever committed or shared between interpreters. Hash-based invalidation keeps the output byte-identical
across arms and runs, so "both arms execute the same module" stays checkable rather than asserted.

The boundary this draws is an **experimental information policy, not a security boundary**. It stops
ordinary development tooling — reading a file, `inspect.getsource`, following `__file__` — from
returning the implementation. It does not resist disassembly, and is not meant to.

Nothing here invokes a model. This module builds and describes the experimental object; measuring
with it is a later milestone.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import marshal
import os
import platform
import py_compile
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
    """Content identity of a directory: every relative path and every byte under it.

    Interpreter caches are skipped, but a `.pyc` that *is* the runtime is not a cache and must be
    covered — the compiled module is the thing whose identity the two arms have to share.
    """
    h = hashlib.sha256()
    for path in sorted(p for p in Path(root).rglob("*")
                       if p.is_file() and "__pycache__" not in p.parts):
        h.update(path.relative_to(root).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(path.read_bytes()).hexdigest().encode("ascii"))
        h.update(b"\0")
    return h.hexdigest()


def digest_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _normalise_const(value: Any) -> Any:
    """One constant, rendered so that equal constants render equally.

    Sets are rendered sorted because their iteration order is not part of what they mean, and nested
    code objects are recursed rather than repr'd because a repr carries a memory address.
    """
    if hasattr(value, "co_code"):
        return ("code", _normalise_code(value))
    if isinstance(value, (frozenset, set)):
        return ("set", tuple(sorted(repr(v) for v in value)))
    if isinstance(value, tuple):
        return ("tuple", tuple(_normalise_const(v) for v in value))
    return (type(value).__name__, repr(value))


def _normalise_code(code: Any) -> tuple:
    """One code object as its structure: what it does, over what names, with what constants."""
    return (
        code.co_name, code.co_argcount, getattr(code, "co_posonlyargcount", 0),
        code.co_kwonlyargcount, code.co_nlocals, code.co_stacksize, code.co_flags,
        code.co_code.hex(), tuple(code.co_names), tuple(code.co_varnames),
        tuple(code.co_freevars), tuple(code.co_cellvars), code.co_filename,
        code.co_firstlineno, tuple(_normalise_const(c) for c in code.co_consts),
    )


def runtime_structure(runtime: Path) -> str:
    """Structural identity of the compiled runtime, invariant under serialisation noise.

    `digest_tree` hashes the bytes, and MLR-C3D-R2 found that those bytes are not reproducible: one
    slot of a twelve-slot paired run produced a different runtime digest from the other eleven, and
    the cause was `marshal`'s interned-string flag for a single name and the reference indices that
    shift behind it. The compiled objects were structurally identical — the same opcodes, names,
    constants and nested code — and the experiment had nonetheless recorded two runtimes.

    Two arms must be able to prove they executed the same implementation, so the identity has to be
    of the implementation and not of one serialisation of it. This walks each compiled object and
    every code object nested inside it, and hashes what the interpreter will actually execute.

    **What it claims.** That the compiled objects have the same structure, for the normalisation
    written above, under one interpreter. **What it does not claim.** Semantic equivalence in any
    wider sense, or identity across interpreters — bytecode is version-specific, so the magic number
    is part of the identity and a digest from one Python is not comparable with another's.
    """
    h = hashlib.sha256()
    h.update(importlib.util.MAGIC_NUMBER)
    h.update(b"\0")
    for pyc in sorted(Path(runtime).rglob("*.pyc")):
        if "__pycache__" in pyc.parts:
            continue
        h.update(pyc.relative_to(runtime).as_posix().encode("utf-8"))
        h.update(b"\0")
        code = marshal.loads(pyc.read_bytes()[16:])
        h.update(json.dumps(_normalise_code(code), default=str).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def interpreter_identity() -> dict[str, str]:
    """The interpreter the runtime was compiled by, and therefore the one it is valid under."""
    return {"version": platform.python_version(),
            "implementation": sys.implementation.name,
            "cache_tag": sys.implementation.cache_tag,
            "bytecode_magic": importlib.util.MAGIC_NUMBER.hex()}


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
    source = fixture / "runtime" / "objectstore"
    compile_runtime(source, runtime)

    if arm == FULL:
        shutil.copytree(source, workspace / VENDORED / "objectstore", ignore=_IGNORE)

    return {
        "arm": arm,
        "workspace": workspace,
        "runtime": runtime,
        "workspace_digest": digest_tree(workspace),
        "runtime_digest": digest_tree(runtime),
        "runtime_structure": runtime_structure(runtime),
        "interpreter": interpreter_identity(),
        "source_digest": digest_tree(source),
        "contract_sha256": digest_file(workspace / "docs" / "storage-contract.md"),
        "vendored_digest": (digest_tree(workspace / VENDORED / "objectstore")
                            if arm == FULL else None),
    }


def compile_runtime(source: Path, runtime: Path) -> Path:
    """Compile the module to bytecode beside no source, with the running interpreter.

    `dfile` normalises the path recorded inside each object so the output does not carry the
    temporary directory it was built in, and unchecked-hash invalidation removes the source
    timestamp — together they make two materialisations of the same source produce the same bytes,
    which is what lets the arms be compared at all.
    """
    package = Path(runtime) / "objectstore"
    package.mkdir(parents=True, exist_ok=True)
    for module in sorted(Path(source).glob("*.py")):
        py_compile.compile(
            str(module), cfile=str(package / f"{module.stem}.pyc"),
            dfile=f"objectstore/{module.name}", doraise=True,
            invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
    return Path(runtime)


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


# Where a path an agent touched belongs. The experiment's accounting depends on telling
# implementation reads apart from everything else, and a path is the only provenance available
# without asking a model what it was doing.
WORKSPACE = "workspace"
VENDORED_IMPLEMENTATION = "vendored-implementation"
RUNTIME = "runtime"
OUTSIDE = "outside"


def classify_path(path: str | Path, built: dict[str, Any]) -> str:
    """Attribute one touched path to the arm's structure.

    `ce1_facts` drops anything absolute as "not part of the system being measured", which is right
    for a scenario whose whole system is the repository and wrong here: the implementation lives
    outside the workspace on purpose, so a read of it is the single most interesting event the run
    can produce. Classification is by resolved path, so a relative read and the absolute read of the
    same file land in the same category.
    """
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = Path(built["workspace"]) / resolved
    try:
        resolved = resolved.resolve()
    except OSError:
        return OUTSIDE
    workspace = Path(built["workspace"]).resolve()
    runtime = Path(built["runtime"]).resolve()
    vendored = (workspace / VENDORED).resolve()
    if resolved == vendored or vendored in resolved.parents:
        return VENDORED_IMPLEMENTATION
    if resolved == workspace or workspace in resolved.parents:
        return WORKSPACE
    if resolved == runtime or runtime in resolved.parents:
        return RUNTIME
    return OUTSIDE


def implementation_bytes(built: dict[str, Any], paths) -> int:
    """How much implementation text a run actually took in.

    Availability is not consumption: `full` carries the whole implementation whether or not the
    agent opens any of it, so only paths that were touched count. In `contract` there is no
    implementation text to touch, which is what makes the two arms comparable rather than merely
    different.
    """
    total = 0
    for path in paths:
        if classify_path(path, built) != VENDORED_IMPLEMENTATION:
            continue
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = Path(built["workspace"]) / resolved
        if resolved.is_file():
            total += resolved.stat().st_size
    return total


def executed_module_is_not_the_readable_copy(built: dict[str, Any], *,
                                             python: str | None = None) -> dict[str, Any]:
    """Guard against the mistake that killed the approved internal control.

    An agent editing a file that the running system does not load produces work that appears done
    and changes nothing. Any fixture offering a readable copy of code it also executes has to be
    able to say which one runs, so the confusion is detected mechanically instead of being
    discovered from a failed experiment.
    """
    probe = subprocess.run(
        [python or sys.executable, "-B", "-c", "import objectstore; print(objectstore.__file__)"],
        cwd=Path(built["workspace"]), env=environment(built), capture_output=True, text=True,
        check=False)
    loaded = Path(probe.stdout.strip()) if probe.returncode == 0 else None
    return {
        "loaded": str(loaded) if loaded else None,
        "from_runtime": bool(loaded) and classify_path(loaded, built) == RUNTIME,
        "readable_copy_is_editable": arm_has_readable_copy(built),
        "editing_the_copy_changes_execution": False,
    }


def arm_has_readable_copy(built: dict[str, Any]) -> bool:
    return (Path(built["workspace"]) / VENDORED / "objectstore").is_dir()
