#!/usr/bin/env python3
"""Install the pinned OpenCode worker build, by content, without touching anything global.

Three refusals this makes on purpose:

* **never "latest"** — the release is fetched by exact version, because the recorded evidence was
  produced with specific bytes and a newer build is a different instrument;
* **verify before install** — the download is hashed in a temporary location and only moves into
  place if it matches, so a failed or tampered download never becomes an executable;
* **never a global path** — installation goes to `~/.proofbound/executors/`, and an `opencode`
  already on your `PATH` is left exactly as it is.

No provider request is made. This installs a binary; it does not authenticate, and it does not
establish that your credential works.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile

VERSION = "1.18.29"
PLATFORM = "darwin-arm64"
SHA256 = "2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669"
URL = (f"https://github.com/sst/opencode/releases/download/v{VERSION}"
       f"/opencode-{PLATFORM}.zip")
TARGET = Path.home() / f".proofbound/executors/opencode-{VERSION}-{PLATFORM}/opencode"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def install(source: Path, target: Path) -> dict:
    """Verify, then place. Never the other way round."""
    found = digest(source)
    if found != SHA256:
        return {"installed": False, "error": "sha256 mismatch; nothing was installed",
                "expected": SHA256, "found": found, "source": str(source)}
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.parent / (target.name + ".incoming")
    shutil.copyfile(source, staged)
    staged.chmod(staged.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    os.replace(staged, target)                      # atomic; never a half-written executable
    return {"installed": True, "path": str(target), "sha256": found}


def fetch(into: Path) -> Path:
    """Download the pinned release. `urllib` only — no third-party dependency is introduced."""
    import urllib.request
    archive = into / f"opencode-{PLATFORM}.zip"
    with urllib.request.urlopen(URL, timeout=300) as response, archive.open("wb") as out:
        shutil.copyfileobj(response, out)
    import zipfile
    with zipfile.ZipFile(archive) as bundle:
        names = [n for n in bundle.namelist() if n.rstrip("/").endswith("opencode")]
        if not names:
            raise SystemExit(f"no `opencode` entry in {URL}")
        bundle.extract(names[0], into)
        return into / names[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="source", type=Path, default=None,
                    help="use a build you already have instead of downloading")
    ap.add_argument("--target", type=Path, default=TARGET)
    ap.add_argument("--check-only", action="store_true",
                    help="report what is installed and exit without changing anything")
    args = ap.parse_args()

    report = {"pinned": {"version": VERSION, "platform": PLATFORM, "sha256": SHA256},
              "target": str(args.target), "provider_requests": 0}

    if platform.system() != "Darwin" or platform.machine() != "arm64":
        report["error"] = ("the worker backend is macOS arm64 only; this host cannot run workers. "
                           "Coordinating from here is still fine.")
        print(json.dumps(report, indent=2, sort_keys=True)); return 2

    existing = shutil.which("opencode")
    if existing and Path(existing).resolve() != args.target.resolve():
        # Reported, never touched. A working global installation is not ours to replace.
        report["global_opencode_left_alone"] = existing

    if args.target.is_file():
        found = digest(args.target)
        report["already_installed"] = {"path": str(args.target), "sha256": found,
                                       "is_pinned_build": found == SHA256}
        if found == SHA256:
            report["installed"] = True
            print(json.dumps(report, indent=2, sort_keys=True)); return 0
    if args.check_only:
        report["installed"] = args.target.is_file() and digest(args.target) == SHA256
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["installed"] else 1

    with tempfile.TemporaryDirectory(prefix="pb-worker-backend-") as raw:
        source = Path(args.source).expanduser() if args.source else fetch(Path(raw))
        if not source.is_file():
            report["error"] = f"no build at {source}"
            print(json.dumps(report, indent=2, sort_keys=True)); return 2
        report.update(install(source, args.target))

    if report.get("installed"):
        report["next"] = [
            f"{args.target} auth login      # choose DeepSeek; Proofbound never sees the key",
            "python3 scripts/pb_workflow.py doctor",
        ]
        report["note"] = ("installed and verified by content. This does not establish that your "
                          "credential is valid; no provider request was made.")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("installed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
