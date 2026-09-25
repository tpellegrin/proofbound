"""What a declared Node toolchain's package manager contributes: npm (the original) or pnpm.

`_toolchain` owns the prepared Node copy, the dependency record and the checks around launches. This
module owns what differs between package managers, so the coordinator CLI stays free of branches
on them.

- **Binding files.** A preparation is bound to the lockfile, the manifest fields that decide
  installation, and, for pnpm, the configuration files that change what `pnpm install` does. Any of
  them changing means the prepared dependencies no longer describe the project.
- **pnpm is prepared like Node.** The declared pnpm package (the unpacked `pnpm` npm package) is
  copied into the run's runtime and recorded by content. A generated `bin/pnpm` runs it with the
  prepared Node. The project's `packageManager` pin must name exactly that version, and pnpm's own
  version management is switched off, so nothing is downloaded behind the pin.
- **pnpm's layout.** Packages must be *copied* into `node_modules`, not hard-linked from a store: a
  store file changed later would change the installed bytes. Symlinks may not leave the project.
  Files may share an inode only with other files inside `node_modules` (esbuild links its own
  binary).
- **Verification** installs with `--frozen-lockfile` from the registry, into a store inside the
  verification directory. That is a network fetch pinned by the lockfile. It is not offline, and it
  is never reported as offline.

Unsupported, and refused rather than approximated: pnpm workspaces with more than one importer,
`patchedDependencies`, and `file:`/`link:` dependencies.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

NPM, PNPM = "npm", "pnpm"
LOCKFILES = {NPM: "package-lock.json", PNPM: "pnpm-lock.yaml"}
#: The `package.json` fields that decide what gets installed.
MANIFEST_FIELDS = {
    NPM: ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies",
          "bundleDependencies", "bundledDependencies", "overrides", "allowScripts",
          "packageManager", "workspaces"),
    PNPM: ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies",
           "bundleDependencies", "bundledDependencies", "overrides", "packageManager",
           "workspaces", "pnpm", "resolutions"),
}
#: Project files that change what `pnpm install` does. Absent is recorded as absent.
PNPM_CONFIG_FILES = (".npmrc", "pnpm-workspace.yaml", ".pnpmfile.cjs")
#: The prepared pnpm, relative to the prepared toolchain root.
PNPM_PACKAGE = "lib/node_modules/pnpm"
PNPM_WRAPPER = "bin/pnpm"
WRAPPER_TEXT = ('#!/bin/sh\n# Proofbound: the declared pnpm, run by the prepared Node.\n'
                'here=$(cd "$(dirname "$0")" && pwd)\n'
                'exec "$here/node" "$here/../lib/node_modules/pnpm/bin/pnpm.cjs" "$@"\n')
#: Environment for anything running with the prepared tooling: no registry access, no update
#: check, no package-manager self-management, and no Git hook installation by `husky`.
WORKER_ENV = {
    NPM: {"npm_config_offline": "true", "npm_config_update_notifier": "false",
          "npm_config_fund": "false", "npm_config_audit": "false"},
    PNPM: {"npm_config_offline": "true", "npm_config_update_notifier": "false",
           "npm_config_manage_package_manager_versions": "false",
           "npm_config_package_manager_strict": "true", "HUSKY": "0"},
}
#: Preparation outside the boundary: lifecycle scripts run as the project's CI runs them, except
#: that `HUSKY=0` keeps a `prepare: husky install` from changing Git configuration.
PREPARE_ENV = {NPM: {}, PNPM: {"HUSKY": "0", "npm_config_update_notifier": "false",
                               "npm_config_manage_package_manager_versions": "false"}}
#: Tool caches that project checks write inside `node_modules`. They are not installed packages, so
#: a pnpm run's boundary lets checks write them and the dependency digest leaves them out:
#: `.vite-temp` (Vite bundles its config there), `.vite` (Vite's and Vitest's cache directory),
#: `.tmp` (where a Vite-template tsconfig puts TypeScript's build info). Observed with
#: wellbeing-platform inside the boundary on 2026-09-25. Fresh-checkout verification starts
#: without any of them.
TOOL_CACHES = (".vite", ".vite-temp", ".tmp")
AUTH_KEYS = re.compile(r"(?im)^\s*[^#;\s]*(_authToken|_auth|_password|//[^=]*:username)\s*=")


def _sha(path: Path) -> "str | None":
    if not Path(path).is_file():
        return None
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def name_of(record: "dict[str, Any] | None") -> str:
    """A toolchain record's package manager. Records from before pnpm support are npm."""
    return ((record or {}).get("package_manager") or {}).get("name", NPM)


def manifest(project: Path, manager: str) -> dict[str, Any]:
    path = Path(project) / "package.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    fields = {k: data[k] for k in MANIFEST_FIELDS[manager] if k in data}
    blob = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
    return {"path": str(path), "fields": sorted(fields), "sha256": hashlib.sha256(blob).hexdigest()}


def config_files(project: Path, manager: str) -> dict[str, "str | None"]:
    return ({name: _sha(Path(project) / name) for name in PNPM_CONFIG_FILES}
            if manager == PNPM else {})


# ---------------------------------------------------------------- declaring pnpm

def pin(project: Path) -> "str | None":
    try:
        return json.loads((Path(project) / "package.json").read_text()).get("packageManager")
    except (OSError, ValueError):
        return None


def pnpm_problems(declared: "str | Path", project: Path) -> list[str]:
    """Why a declared pnpm package cannot serve this project. Copies nothing."""
    root = Path(declared).expanduser().absolute().resolve()
    meta = root / "package.json"
    if not (root / "bin/pnpm.cjs").is_file() or not meta.is_file():
        return [f"{declared} is not an unpacked pnpm package (bin/pnpm.cjs and package.json)"]
    info = json.loads(meta.read_text())
    if info.get("name") != "pnpm":
        return [f"{declared} is the package {info.get('name')!r}, not pnpm"]
    out = []
    wanted = pin(project)
    if not (wanted or "").startswith("pnpm@"):
        out.append(f"the project's packageManager is {wanted!r}; a pnpm run needs a pnpm@<version> pin")
    elif wanted.split("+", 1)[0] != f"pnpm@{info.get('version')}":
        out.append(f"the project pins {wanted}, but {declared} is pnpm {info.get('version')}")
    project = Path(project)
    if not (project / LOCKFILES[PNPM]).is_file():
        out.append("the project has no pnpm-lock.yaml, so its dependencies are not pinned")
    if (project / LOCKFILES[NPM]).is_file():
        out.append("the project has both package-lock.json and pnpm-lock.yaml; declare one package manager")
    out += unsupported(project)
    npmrc = project / ".npmrc"
    if npmrc.is_file() and AUTH_KEYS.search(npmrc.read_text(errors="replace")):
        out.append("the project's .npmrc holds registry credentials, which the worker boundary could "
                   "read; keep them outside the project")
    return out


def unsupported(project: Path) -> list[str]:
    """pnpm features this preparation does not model yet, refused rather than half-bound."""
    out = []
    lock = Path(project) / LOCKFILES[PNPM]
    text = lock.read_text(errors="replace") if lock.is_file() else ""
    importers = re.findall(r"(?m)^  (\S[^:]*):\s*$", text.split("\nimporters:", 1)[1].split("\npackages:", 1)[0]) \
        if "\nimporters:" in text else []
    if len(importers) > 1:
        out.append(f"the lockfile has {len(importers)} importers (a workspace); pnpm workspaces are not supported yet")
    if re.search(r"(?m)^patchedDependencies:", text):
        out.append("the lockfile has patchedDependencies; patched pnpm dependencies are not supported yet")
    if re.search(r"(?m)^\s+(specifier|version):\s*'?(file|link):", text):
        out.append("the lockfile has file: or link: dependencies; local dependencies are not supported yet")
    return out


def prepare_pnpm(declared: "str | Path", prepared: Path) -> dict[str, Any]:
    """Copy the declared pnpm package beside the prepared Node and write its wrapper."""
    import shutil
    source = Path(declared).expanduser().absolute().resolve()
    target = Path(prepared) / PNPM_PACKAGE
    shutil.copytree(source, target, symlinks=True)
    wrapper = Path(prepared) / PNPM_WRAPPER
    wrapper.write_text(WRAPPER_TEXT)
    wrapper.chmod(0o755)
    env = {"PATH": f"{Path(prepared) / 'bin'}:/usr/bin:/bin", "HOME": "/nonexistent",
           **WORKER_ENV[PNPM]}
    cp = subprocess.run([str(wrapper), "--version"], capture_output=True, text=True, env=env, timeout=60)
    if cp.returncode != 0:
        raise ValueError(f"the prepared pnpm did not run: {(cp.stderr or cp.stdout)[-300:]}")
    return {"name": PNPM, "version": cp.stdout.strip(), "declared": str(Path(declared).expanduser().absolute()),
            "resolved": str(source), "wrapper_sha256": _sha(wrapper)}


# ---------------------------------------------------------------- installed layout

def layout_problems(project: Path, record: dict[str, Any]) -> list[str]:
    """Why an installed pnpm `node_modules` is not a self-contained copy made by the declared pnpm."""
    project = Path(project).resolve()
    modules = project / "node_modules"
    meta = modules / ".modules.yaml"
    if not meta.is_file():
        return ["node_modules was not installed by pnpm (no node_modules/.modules.yaml)"]
    text = meta.read_text(errors="replace")
    out = []
    want = f"pnpm@{record['version']}"
    if not re.search(rf"(?m)^packageManager: {re.escape(want)}$", text):
        out.append(f"node_modules was not installed by {want}")
    if not re.search(r"(?m)^nodeLinker: isolated$", text):
        out.append("node_modules does not use pnpm's isolated layout")
    links: dict[tuple[int, int], list[int]] = {}   # inode -> [paths seen inside node_modules, nlink]
    leaving = []
    for base, dirs, names in os.walk(modules, followlinks=False):
        if Path(base) == modules:
            dirs[:] = [d for d in dirs if d not in TOOL_CACHES]
        for name in dirs + names:
            path = Path(base) / name
            if path.is_symlink():
                target = Path(os.path.realpath(path))
                if project not in target.parents:
                    leaving.append(f"{path.relative_to(project)} -> {target}")
            elif name in names:
                st = path.lstat()
                if st.st_nlink > 1:
                    links.setdefault((st.st_dev, st.st_ino), [0, st.st_nlink])[0] += 1
    if leaving:
        out.append(f"{len(leaving)} symlinks in node_modules leave the project, e.g. {leaving[:3]}")
    out += cache_problems(project)
    shared = sum(1 for seen, nlink in links.values() if seen < nlink)
    if shared:
        out.append(f"{shared} installed files are hard-linked to files outside node_modules (a package "
                   "store), so a later change there would change them; install with "
                   "--package-import-method copy")
    return out


def cache_problems(project: Path) -> list[str]:
    """Why the writable tool caches are not ordinary directories inside the project.

    They are writable inside the boundary and left out of the dependency digest, so each must be
    absent or a real directory, and no symlink inside it may leave the project. Otherwise a check
    would read cache state from outside the recorded preparation. Writes through such a link are
    refused by the boundary; this closes the read side."""
    project = Path(project).resolve()
    out = []
    for name in TOOL_CACHES:
        cache = project / "node_modules" / name
        if cache.is_symlink():
            out.append(f"node_modules/{name} is a symlink (to {os.readlink(cache)}), not a cache directory")
            continue
        if not cache.is_dir():
            continue
        for base, dirs, names in os.walk(cache, followlinks=False):
            for entry in dirs + names:
                path = Path(base) / entry
                if path.is_symlink() and project not in Path(os.path.realpath(path)).parents:
                    out.append(f"{path.relative_to(project)} links outside the project")
    return out


def install_argv(record: dict[str, Any], prepared_bin: Path, workdir: Path) -> list[str]:
    """How verification installs the recorded dependencies in a fresh checkout."""
    manager = name_of(record)
    if manager == NPM:
        return list(record["dependencies"].get("prepare_command") or ["npm", "ci"])
    return [str(Path(prepared_bin) / "pnpm"), "install", "--frozen-lockfile",
            "--package-import-method", "copy", "--store-dir", str(Path(workdir) / "pnpm-store")]


def preparation_command(manager: str, prepared_hint: str) -> str:
    """The command an owner runs, before `start`, to prepare dependencies."""
    if manager == NPM:
        return f"{prepared_hint}/bin/npm ci"
    # The declared Node goes first on PATH: dependency install scripts run `node` from PATH.
    return (f"PATH={prepared_hint}/bin:$PATH HUSKY=0 node <pnpm>/bin/pnpm.cjs install "
            "--frozen-lockfile --package-import-method copy --store-dir <a store outside the "
            "project> --config.manage-package-manager-versions=false")
