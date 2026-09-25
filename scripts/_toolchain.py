"""A run's declared project toolchain: pinned bytes the worker boundary can run and not change.

Measured on 2026-09-24 with BorrowDesk (Node 24.19.0, TypeScript 7), inside the production
boundary: its baseline check passes on the host, but a worker could not run it. The boundary
executes only system binaries, the Python interpreter, Homebrew's Cellar and the run's own runtime:
- the pinned Node and npm live under the owner's home, which the boundary does not expose;
- TypeScript 7's compiler executes a native binary from the project's `node_modules`, and
  execution from the project is refused.

A run opts in with `start --toolchain <node distribution>`:
- **`start` prepares.** It copies the distribution's `node`, `npm` and `npx` into the run's runtime
  directory as an independent copy, records versions and content digests, and records the
  project's already-installed dependencies. That means a digest of `node_modules`, the lockfile,
  and the dependency fields of `package.json`. `start` installs nothing: dependencies are prepared
  beforehand with `<toolchain>/bin/npm ci`, and a project without them is refused.
- **The boundary** puts the prepared `bin` on the worker's `PATH`, denies writes to the prepared
  copy and to `node_modules` (including renaming either), and allows execution inside
  `node_modules` only. Worker `npm` runs offline, so it cannot fetch packages.
- **Every launch** is refused, before a slot is reserved, if any recorded digest no longer matches.
  That includes a worker's change to the dependency declarations: the prepared dependencies then
  no longer describe the candidate, and nothing reinstalls them.

**Trust.** Project checks already execute project code. This makes a prepared toolchain available;
it does not make dependency code trusted or harmless. The worker's network and credential rules
are those of its profile, unchanged, and the owner's home stays outside the boundary.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

FORMAT = "proofbound-run-toolchain-v1"
KIND = "node"
PREPARED = "toolchain"
#: What is copied from a Node distribution: the runtime and npm, and nothing else it ships.
ENTRIES = ("bin/node", "bin/npm", "bin/npx", "lib/node_modules/npm")
#: The `package.json` fields that declare dependencies. A change to any of them means the prepared
#: `node_modules` no longer corresponds to the project.
DEPENDENCY_FIELDS = ("dependencies", "devDependencies", "optionalDependencies",
                     "peerDependencies", "bundleDependencies", "bundledDependencies", "overrides",
                     "allowScripts", "packageManager", "workspaces")
#: Worker npm never fetches: installation happens before the run, not during it.
WORKER_NPM_ENV = {"npm_config_offline": "true", "npm_config_update_notifier": "false",
                  "npm_config_fund": "false", "npm_config_audit": "false"}


import _package_manager as pm


class ToolchainError(ValueError):
    """A declaration or preparation that cannot be used as given; nothing was prepared."""


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def tree(root: Path, exclude: "tuple[str, ...]" = ()) -> dict[str, Any]:
    """A content digest of a directory tree, without following symlinks.

    Files contribute their bytes and executable bit, and symlinks their target text. Directories
    contribute their names, so an added, removed or renamed entry changes the digest.
    """
    root = Path(root)
    if not root.exists() and not root.is_symlink():
        return {"digest": None, "files": 0, "bytes": 0}
    h = hashlib.sha256()
    counts = {"files": 0, "bytes": 0}

    def add(rel: str, path: Path) -> None:
        if path.is_symlink():
            h.update(f"L {rel} {os.readlink(path)}\n".encode())
        elif path.is_dir():
            h.update(f"D {rel}\n".encode())
        else:
            counts["files"] += 1
            counts["bytes"] += path.stat().st_size
            h.update(f"F {rel} {oct(path.stat().st_mode & 0o111)} {_sha(path)}\n".encode())

    if root.is_symlink() or not root.is_dir():
        add(".", root)
    else:
        for base, dirs, names in os.walk(root, followlinks=False):
            if exclude and Path(base) == root:
                dirs[:] = [d for d in dirs if d not in exclude]
                names = [n for n in names if n not in exclude]
            dirs.sort()
            relative = Path(base).relative_to(root)
            for name in sorted(names + dirs):
                add(str(relative / name), Path(base) / name)
    return {"digest": h.hexdigest(), **counts}


def _manifest_dependencies(project: Path) -> dict[str, Any]:
    path = project / "package.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    fields = {k: data[k] for k in DEPENDENCY_FIELDS if k in data}
    blob = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
    return {"path": str(path), "fields": sorted(fields), "sha256": hashlib.sha256(blob).hexdigest()}


def dependencies(project: Path, manager: str = pm.NPM) -> dict[str, Any]:
    """What the project's prepared dependencies are, from the bytes on disk now.

    An npm record keeps its original shape. A pnpm record adds the configuration files that change
    what `pnpm install` does."""
    project = Path(project)
    lock = project / pm.LOCKFILES[manager]
    caches = pm.TOOL_CACHES if manager == pm.PNPM else ()
    out = {"node_modules": {"path": str(project / "node_modules"),
                            **tree(project / "node_modules", exclude=caches)},
           "lockfile": {"path": str(lock), "sha256": _sha(lock) if lock.is_file() else None},
           "manifest": _manifest_dependencies(project) if manager == pm.NPM else pm.manifest(project, manager),
           "prepare_command": ["npm", "ci"] if manager == pm.NPM else
                              ["pnpm", "install", "--frozen-lockfile", "--package-import-method", "copy"]}
    if manager != pm.NPM:
        out["config_files"] = pm.config_files(project, manager)
    return out


def declarations_match(now: dict[str, Any], was: dict[str, Any]) -> bool:
    """Whether the lockfile, the manifest's installation fields and any bound configuration files
    are the ones recorded at preparation."""
    return (now["manifest"]["sha256"] == was["manifest"]["sha256"]
            and now["lockfile"]["sha256"] == was["lockfile"]["sha256"]
            and now.get("config_files") == was.get("config_files"))


def _copy(source: Path, target: Path) -> None:
    """An independent copy: a copy-on-write clone where the file system offers one."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if subprocess.run(["/bin/cp", "-c", "-R", "-P", str(source), str(target)],
                      capture_output=True).returncode == 0:
        return
    if source.is_symlink():
        os.symlink(os.readlink(source), target)
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target)


def _version(prepared: Path, *argv: str) -> str:
    env = {"PATH": f"{prepared / 'bin'}:/usr/bin:/bin", "HOME": "/nonexistent"}
    cp = subprocess.run([str(prepared / "bin" / argv[0]), *argv[1:]], capture_output=True,
                        text=True, timeout=60, env=env)
    if cp.returncode != 0:
        raise ToolchainError(f"the prepared {argv[0]} did not run: {(cp.stderr or cp.stdout)[-300:]}")
    return cp.stdout.strip()


def _leaving_links(root: Path) -> list[str]:
    """Symlinks among the copied entries that do not name another copied entry by a relative path.

    Copied as they are, such a link in the prepared copy would name bytes outside it: an absolute
    link names the source distribution, and a relative one leaving the entries names something
    that was not copied. Either could change after preparation, unseen by the recorded digests.
    """
    root = Path(root)
    entries = [Path(os.path.normpath(root / e)) for e in ENTRIES]
    out = []
    for entry in ENTRIES:
        top = root / entry
        paths = [top]
        if top.is_dir() and not top.is_symlink():
            paths += [Path(base) / n for base, dirs, names in os.walk(top) for n in dirs + names]
        for path in paths:
            if not path.is_symlink():
                continue
            text = os.readlink(path)
            target = Path(os.path.normpath(path.parent / text))
            if os.path.isabs(text) or not any(target == e or target.is_relative_to(e)
                                              for e in entries):
                out.append(f"{path.relative_to(root)} -> {text}")
    return out


def check(declared: "str | Path", project: Path, pnpm: "str | Path | None" = None) -> list[str]:
    """Why a declaration cannot be prepared, before anything is created. Copies nothing."""
    resolved = Path(declared).expanduser().absolute().resolve()
    missing = [e for e in ENTRIES if not (resolved / e).exists()]
    if missing:
        return [f"{declared} is not a Node distribution: missing {missing}"]
    leaving = _leaving_links(resolved)
    if leaving:
        return [f"{declared} has symlinks that leave the copied toolchain ({'; '.join(leaving[:5])}), "
                "so its prepared copy would name bytes that can change after preparation"]
    project = Path(project)
    out = []
    if not (project / "package.json").is_file():
        return out + ["the project has no package.json"]
    if pnpm is not None:
        out += pm.pnpm_problems(pnpm, project)
        if not (project / "node_modules").is_dir():
            out.append("the project's dependencies are not installed; prepare them first with "
                       f"`{pm.preparation_command(pm.PNPM, str(resolved))}` in {project}")
        elif not out:
            version = json.loads((Path(pnpm).expanduser().resolve() / "package.json").read_text())["version"]
            out += pm.layout_problems(project, {"version": version})
    else:
        if (pm.pin(project) or "").startswith("pnpm@"):
            out.append(f"the project pins {pm.pin(project)}; declare the pnpm package with --pnpm")
        if not (project / "package-lock.json").is_file():
            out.append("the project has no package-lock.json, so its dependencies are not pinned")
        if not (project / "node_modules").is_dir():
            out.append("the project's dependencies are not installed; prepare them first with "
                       f"`{resolved / 'bin' / 'npm'} ci` in {project}")
    pinned = project / ".node-version"
    if pinned.is_file():
        want = pinned.read_text().strip().lstrip("v")
        try:
            have = _version(resolved, "node", "--version").lstrip("v")
        except ToolchainError as exc:
            return out + [str(exc)]
        if want and want != have:
            out.append(f"{declared} is Node {have}; the project's .node-version pins {want}")
    return out


def prepare(declared: "str | Path", runtime: Path, project: Path,
            pnpm: "str | Path | None" = None) -> dict[str, Any]:
    """Copy the toolchain into the run's runtime directory and return the record the run keeps.
    Call `check` first; this assumes it found nothing."""
    declared = Path(declared).expanduser().absolute()
    resolved = declared.resolve()
    project = Path(project)
    prepared = Path(runtime) / PREPARED
    for entry in ENTRIES:
        _copy(resolved / entry, prepared / entry)
    node_version = _version(prepared, "node", "--version")
    npm_version = _version(prepared, "npm", "--version")
    pinned = project / ".node-version"
    if pinned.is_file():
        want = pinned.read_text().strip().lstrip("v")
        if want and want != node_version.lstrip("v"):
            shutil.rmtree(prepared, ignore_errors=True)
            raise ToolchainError(f"{declared} is Node {node_version}; the project's .node-version "
                                 f"pins {want}")
    record = {"format": FORMAT, "kind": KIND, "declared": str(declared), "resolved": str(resolved),
              "prepared": str(prepared), "node_version": node_version, "npm_version": npm_version,
              "identity": identity(prepared),
              "trust": "project checks already execute project code; this makes a prepared "
                       "toolchain available and does not make dependency code trusted"}
    if pnpm is None:
        record["dependencies"] = dependencies(project)
        return record
    try:
        manager = pm.prepare_pnpm(pnpm, prepared)
    except ValueError as exc:
        shutil.rmtree(prepared, ignore_errors=True)
        raise ToolchainError(str(exc)) from exc
    manager["identity"] = tree(prepared / pm.PNPM_PACKAGE)["digest"]
    manager["writable_caches"] = [f"node_modules/{c}" for c in pm.TOOL_CACHES]
    manager["network"] = ("dependencies are prepared before the run; worker pnpm runs with "
                          "npm_config_offline and cannot fetch. Fresh-checkout verification "
                          "installs from the registry with --frozen-lockfile: a fetch pinned by "
                          "the lockfile, not an offline install")
    record["package_manager"] = manager
    record["dependencies"] = dependencies(project, pm.PNPM)
    return record


def identity(root: Path) -> dict[str, Any]:
    """The digest of each copied entry under `root`, comparable between the prepared copy and the
    distribution it came from."""
    entries = {entry: tree(Path(root) / entry)["digest"] for entry in ENTRIES}
    blob = json.dumps(entries, sort_keys=True).encode()
    return {"entries": entries, "digest": hashlib.sha256(blob).hexdigest()}


def _layout(prepared: Path, manager: str = pm.NPM) -> bool:
    """The prepared copy holds exactly the copied entries: nothing added beside them."""
    expected = {"": {"bin", "lib"}, "bin": {"node", "npm", "npx"}, "lib": {"node_modules"},
                "lib/node_modules": {"npm"}}
    if manager == pm.PNPM:
        expected["bin"] = expected["bin"] | {"pnpm"}
        expected["lib/node_modules"] = expected["lib/node_modules"] | {"pnpm"}
    try:
        return all(set(os.listdir(Path(prepared) / rel)) == names for rel, names in expected.items())
    except OSError:
        return False


def source_matches(record: dict[str, Any]) -> bool:
    """Whether the declared distributions still hold the bytes that were prepared from them."""
    if identity(Path(record["resolved"]))["digest"] != record["identity"]["digest"]:
        return False
    manager = record.get("package_manager")
    return manager is None or tree(Path(manager["resolved"]))["digest"] == manager["identity"]


def materialize(record: dict[str, Any], target: Path) -> Path:
    """A fresh prepared copy made from the recorded sources, for fresh-checkout verification.

    It must reproduce the recorded identities exactly; otherwise nothing is verified with it."""
    target = Path(target)
    for entry in ENTRIES:
        _copy(Path(record["resolved"]) / entry, target / entry)
    if identity(target)["digest"] != record["identity"]["digest"]:
        raise ToolchainError("the declared Node distribution no longer holds the prepared bytes")
    manager = record.get("package_manager")
    if manager:
        pm.prepare_pnpm(manager["resolved"], target)
        if (tree(target / pm.PNPM_PACKAGE)["digest"] != manager["identity"]
                or _sha(target / pm.PNPM_WRAPPER) != manager["wrapper_sha256"]):
            raise ToolchainError("the declared pnpm package no longer holds the prepared bytes")
    return target


def problems(config: dict[str, Any]) -> list[str]:
    """Why a launch must not start from this preparation. Empty when every digest still matches."""
    record = config.get("toolchain")
    if not record:
        return []
    out = []
    prepared = Path(record["prepared"])
    manager = pm.name_of(record)
    if identity(prepared)["digest"] != record["identity"]["digest"] or not _layout(prepared, manager):
        out.append(f"the prepared toolchain at {prepared} is missing or no longer matches the "
                   "bytes recorded at start; start a new run")
    if manager == pm.PNPM:
        pnpm = record["package_manager"]
        if (tree(prepared / pm.PNPM_PACKAGE)["digest"] != pnpm["identity"]
                or _sha(prepared / pm.PNPM_WRAPPER) != pnpm["wrapper_sha256"]):
            out.append(f"the prepared pnpm at {prepared} no longer matches the bytes recorded at "
                       "start; start a new run")
    try:
        now = dependencies(Path(config["paths"]["project"]), manager)
    except (OSError, ValueError) as exc:
        return out + [f"the project's package.json cannot be read ({type(exc).__name__}); the "
                      "prepared dependencies cannot be shown to correspond to it"]
    was = record["dependencies"]
    if not declarations_match(now, was):
        out.append(f"the project's dependency declarations (package.json installation fields, "
                   f"{pm.LOCKFILES[manager]} or the package manager's configuration files) changed "
                   "since preparation, so the prepared dependencies no "
                   "longer correspond to the candidate. Nothing was reinstalled; a dependency change "
                   "needs its own adjudication and a newly prepared run")
    if now["node_modules"]["digest"] != was["node_modules"]["digest"]:
        out.append("the project's installed node_modules no longer match the dependencies prepared "
                   "at start; nothing was reinstalled")
    return out


def boundary_rules(config: dict[str, Any]) -> dict[str, list[str]]:
    """Paths the worker boundary must deny writes to, and the one tree it may execute from."""
    record = config.get("toolchain")
    if not record:
        return {"deny_write": [], "allow_exec": [], "allow_write": [], "signal_same_sandbox": False}
    # Resolved, because the boundary matches real paths: a rule on a symlinked path protects nothing.
    prepared = str(Path(record["prepared"]).resolve())
    project = Path(config["paths"]["project"]).resolve()
    modules = str(project / "node_modules")
    # Tool caches a pnpm run's record names stay writable; every installed package stays protected.
    caches = [str(project / c) for c in (record.get("package_manager") or {}).get("writable_caches", [])]
    # A pnpm run's checks use worker pools (Vitest) that must stop their own children. Signals stay
    # confined to the same sandbox; npm runs keep the original rules.
    return {"deny_write": [prepared, modules], "allow_exec": [modules], "allow_write": caches,
            "signal_same_sandbox": bool(record.get("package_manager"))}


def env_vars(config: dict[str, Any]) -> dict[str, str]:
    """The package manager's environment for anything run with the prepared tooling."""
    record = config.get("toolchain")
    return dict(pm.WORKER_ENV[pm.name_of(record)]) if record else {}


def worker_env(config: dict[str, Any]) -> dict[str, str]:
    """What the worker's environment adds: the prepared `bin` first on `PATH`, and an offline
    package manager."""
    record = config.get("toolchain")
    if not record:
        return {}
    return {"PATH_PREFIX": str(Path(record["prepared"]) / "bin"), **env_vars(config)}
