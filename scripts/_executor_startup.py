"""How the pinned executor starts, for runs whose worker settings carry `executor.startup`.

OpenCode 1.18.29 does three things at start-up that nothing in a run's record controlled:

* **It replaces its model catalogue from the network.** The binary bundles a catalogue; unless
  `OPENCODE_DISABLE_MODELS_FETCH` is set it also fetches models.dev, caches it in the home as
  `.cache/opencode/models.json`, and prefers that cache from then on. As fetched on 2026-09-24,
  models.dev lists `deepseek-v4-flash` as `deprecated`, and the executor deletes deprecated models
  from the catalogue it builds providers from. A launch that reads the fetched catalogue therefore
  fails at its first model step, before any request, with a server error whose detail is only
  logged: reproduced from the failed qualification run's own cached catalogue, and through the
  front door on a fresh run. With the fetch off, no cache is written and the bundled catalogue —
  part of the pinned bytes — is the one used; a cache already present still wins, so none may
  exist.
* **It installs `@opencode-ai/plugin` from npm into every configuration directory**, in a detached
  background fiber, whenever that directory is writable. Its version is the executor's own, its
  dependencies are resolved at install time, and an exit mid-install leaves the install lock behind
  (whose heartbeat the executor never advances), for the next executor process to break. Nothing
  on the `run` path waits for it. The configuration directory is therefore staged here with the
  two files the executor would write itself, and the boundary denies writes to it: the executor's
  own writability check then skips the install. No npm dependency is used, so there is none to pin.
* **It logs to a file it buffers.** A process that fails within a second leaves that file empty, so
  the error reference it prints (`err_…`) names a detail nobody kept. `OPENCODE_PRINT_LOGS` sends
  the same log to stderr, which the launcher already writes to the attempt's private `worker.log`.

`observe` and `problems` let the launcher refuse, before a slot is reserved, a home that would
start differently. What they record is names, sizes, modes, times and digests, never contents.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

#: The policy recorded in worker settings. Each value names what the launcher enforces.
POLICY = {
    "catalogue": "bundled: OPENCODE_DISABLE_MODELS_FETCH, and no cached models.json in the home",
    "config_dir": "staged with the executor's own defaults and write-denied by the boundary, so "
                  "the executor skips its npm install of @opencode-ai/plugin",
    "logs": "OPENCODE_PRINT_LOGS: the executor's log goes to stderr, i.e. the attempt's worker.log",
    "refuse_before_launch": "a changed configuration directory, a cached catalogue, a lock or "
                            "breaker left by an earlier executor process, or a .opencode directory",
}

ENV = {"OPENCODE_DISABLE_MODELS_FETCH": "1", "OPENCODE_PRINT_LOGS": "1"}

#: Exactly the bytes OpenCode 1.18.29 writes into its global configuration directory on first
#: start (`Config.ensureGitignore` and the default global config), so staging them changes nothing
#: the executor reads and leaves it nothing it wants to write.
CONFIG_FILES = {
    "opencode.jsonc": b'{\n  "$schema": "https://opencode.ai/config.json"\n}',
    ".gitignore": b"node_modules\npackage.json\npackage-lock.json\nbun.lock\n.gitignore",
}


def config_dir(home: "str | Path") -> Path:
    return Path(home) / ".config" / "opencode"


def catalogue(home: "str | Path") -> Path:
    return Path(home) / ".cache" / "opencode" / "models.json"


def locks(home: "str | Path") -> Path:
    return Path(home) / ".local" / "state" / "opencode" / "locks"


def stage(home: "str | Path") -> dict[str, Any]:
    """Write the configuration directory a new run's executor starts from."""
    directory = config_dir(home)
    directory.mkdir(parents=True, exist_ok=False)
    for name, data in CONFIG_FILES.items():
        (directory / name).write_bytes(data)
    return {"config_dir": str(directory),
            "files": {name: hashlib.sha256(data).hexdigest()
                      for name, data in CONFIG_FILES.items()}}


def boundary_rules(home: "str | Path") -> list[tuple[str, str]]:
    """The writes the boundary denies the worker: `(kind, path)` for `subpath` or `literal`."""
    return [("subpath", str(config_dir(home))), ("literal", str(catalogue(home)))]


def _entry(path: Path) -> dict[str, Any]:
    st = path.lstat()
    out: dict[str, Any] = {"mode": oct(st.st_mode & 0o7777), "mtime": st.st_mtime,
                           "kind": "dir" if path.is_dir() else "file"}
    if path.is_file() and not path.is_symlink():
        out["size"] = st.st_size
        out["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _lock(path: Path) -> dict[str, Any]:
    out = _entry(path)
    meta = path / "meta.json"
    if meta.is_file():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            # The token proves ownership to the executor; it identifies nothing to a reader.
            out["meta"] = {k: data.get(k) for k in ("pid", "createdAt")}
        except (OSError, ValueError):
            out["meta"] = "unreadable"
    heartbeat = path / "heartbeat"
    if heartbeat.exists():
        out["heartbeat_mtime"] = heartbeat.stat().st_mtime
    return out


def observe(home: "str | Path", project: "str | Path") -> dict[str, Any]:
    """What an executor starting now would find. Names, sizes, modes, times and digests only."""
    home, project = Path(home), Path(project)
    directory, cached, held = config_dir(home), catalogue(home), locks(home)
    return {
        "config_dir": ({name: _entry(directory / name) for name in sorted(p.name for p in
                                                                            directory.iterdir())}
                       if directory.is_dir() else None),
        "catalogue_cache": _entry(cached) if cached.exists() else None,
        "locks": ({p.name: _lock(p) for p in sorted(held.iterdir())} if held.is_dir() else {}),
        "opencode_dirs": [str(p) for p in (project / ".opencode", home / ".opencode")
                          if p.exists()],
    }


def problems(observed: dict[str, Any], *, boundary_text: "str | None",
             home: "str | Path", bounded: bool = True) -> list[str]:
    """Why an executor must not start from this state; each names what to inspect.

    `bounded` says whether the launch runs inside a boundary at all. Authorization always builds
    one; only the suite's offline injection launches a scripted stand-in without it, and there is
    then no boundary whose rules could be checked. Every state check still applies.
    """
    out: list[str] = []
    found = observed.get("config_dir")
    expected = {name: hashlib.sha256(data).hexdigest() for name, data in CONFIG_FILES.items()}
    if found is None:
        out.append(f"the staged executor configuration directory {config_dir(home)} is missing")
    elif {n: e.get("sha256") for n, e in found.items()} != expected:
        out.append(f"the executor configuration directory {config_dir(home)} no longer holds "
                   f"exactly the staged files {sorted(expected)} (found {sorted(found)}); an "
                   "install or edit happened there")
    if observed.get("catalogue_cache"):
        out.append(f"a cached model catalogue exists at {catalogue(home)}; the executor would "
                   "prefer it to the catalogue bundled in the pinned build")
    if observed.get("locks"):
        out.append(f"an earlier executor process left {sorted(observed['locks'])} in "
                   f"{locks(home)}; its work did not finish")
    if observed.get("opencode_dirs"):
        out.append(f"{observed['opencode_dirs']} would be loaded as executor configuration and "
                   "given an npm install; remove it or start a new run")
    rules = [f'(deny file-write* ({kind} "{path}"))' for kind, path in boundary_rules(home)]
    if bounded and (boundary_text is None or any(rule not in boundary_text for rule in rules)):
        out.append("the worker boundary does not deny writes to the staged executor "
                   "configuration and catalogue cache; re-run authorization")
    return out
