"""Where a project keeps Proofbound's generated workflow state.

New runs, receipts and adapter shims are created under `.proofbound/` at the project root. Runs
created before that name was chosen live under `DeepSeekAndDestroy/` and stay usable where they
were recorded: nothing here moves, copies or rewrites them. Both names are therefore recognised
wherever a path is *read* — deriving a project from a run, confining a worker, excluding generated
state from scope and deliveries — and only `.proofbound/` is ever *created*.

Deliberate, reviewable specifications are not workflow state; they live in the project's own
locations (`specs/<change>/`) and are not governed by this module. Retained private evidence lives
outside the project altogether.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath

#: The root every new run, receipt and adapter shim is created under.
WORKSPACE = ".proofbound"
#: The root runs were created under before `.proofbound/`. Recognised, never created.
LEGACY_WORKSPACE = "DeepSeekAndDestroy"
#: Every name a project-local workspace root may have, newest first.
ROOTS = (WORKSPACE, LEGACY_WORKSPACE)


def root_of(path: Path) -> Path | None:
    """The nearest ancestor of `path`, itself included, that is a workspace root."""
    for ancestor in [path, *path.parents]:
        if ancestor.name in ROOTS:
            return ancestor
    return None


def project_of(path: Path) -> Path:
    """The project whose workspace contains `path`."""
    root = root_of(path)
    if root is None:
        raise ValueError(f"{path} does not live below a {' or '.join(r + '/' for r in ROOTS)} "
                         "workspace root")
    return root.parent.resolve()


def containing(project: Path, run: Path) -> Path:
    """The workspace root below `project` that contains `run`, refusing a run anywhere else."""
    for name in ROOTS:
        root = project / name
        try:
            run.relative_to(root)
        except ValueError:
            continue
        return root
    raise ValueError(f"run root must live under {project / WORKSPACE} "
                     f"(or, for a run created before it, {project / LEGACY_WORKSPACE}): {run}")


def is_generated(relative: str) -> bool:
    """Whether a project-relative POSIX path is inside any workspace root."""
    text = PurePosixPath(relative.replace("\\", "/").strip("/")).as_posix()
    return any(text == name or text.startswith(name + "/") for name in ROOTS)


def run_for(project: Path, change: str, name: str = "first") -> Path:
    """Where the run `name` of `change` is, or would be created.

    An existing run is found where it was recorded. A run present under both roots is ambiguous and
    refused rather than resolved by preference, because either copy could be the one a coordinator
    has been continuing. A run present under neither is placed under `.proofbound/`.
    """
    candidates = [project / root / "plans" / change / "runs" / name for root in ROOTS]
    present = [c for c in candidates if c.exists()]
    if len(present) > 1:
        raise ValueError("run " + f"{change}/{name} exists under more than one workspace root ("
                         + ", ".join(str(p) for p in present) + "); nothing was chosen or "
                         "changed. Continue the intended run by its --run path, and preserve or "
                         "move the other deliberately")
    return present[0] if present else candidates[0]


def plans(project: Path) -> list[Path]:
    """Each workspace root's `plans/` directory that exists in `project`."""
    return [project / root / "plans" for root in ROOTS if (project / root / "plans").is_dir()]
