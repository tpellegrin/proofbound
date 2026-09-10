#!/usr/bin/env python3
"""Is the provider actually answering, before a semantic slot is spent on finding out.

The Nemotron paired run lost five of eight pairs to an endpoint that had begun returning upstream
404s. The frozen retry policy behaved correctly — each slot took its bounded attempts and no more —
but twenty-five paid launches were spent discovering, one at a time, that the provider was down.

So a cheap check runs first. It asks the configured model a trivial question outside the fixture and
reports whether an answer came back. It is not a semantic sample, it never touches the experiment's
task, and its cost is accounted separately from the experiment's.

**What it cannot do.** It cannot promise the provider will still be there for the next slot; an
outage that begins mid-series still costs the slot it interrupts. It shortens the window, it does not
close it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

AVAILABLE = "available"
UNAVAILABLE = "unavailable"
NO_EXECUTABLE = "no-executable"

# Long enough for a small model call, short enough that a dead endpoint is not discovered slowly.
PROBE_TIMEOUT_SECONDS = 120
PROBE_PROMPT = "Reply with exactly one word: ready"


def health(model: str, *, variant: str | None = None,
           timeout: int = PROBE_TIMEOUT_SECONDS,
           executable: str = "opencode") -> dict[str, Any]:
    """One trivial call to the configured model, in a throwaway directory and database.

    The probe runs against its own `OPENCODE_DB` in a temporary directory so it cannot appear in any
    experiment's session record, and in a temporary working directory so it has no repository to
    explore. What comes back is retained: the provider's own model identity, its usage if reported,
    and the error text if it failed — the last being what turned an opaque series of failures into a
    diagnosis last time.
    """
    found = shutil.which(executable)
    if not found:
        return {"status": NO_EXECUTABLE, "model": model, "variant": variant,
                "detail": f"{executable!r} is not on PATH"}

    holder = Path(tempfile.mkdtemp(prefix="pb-health-"))
    started = time.time()
    try:
        env = dict(os.environ)
        env["OPENCODE_DB"] = str(holder / "probe.db")
        cmd = [found, "run", "--model", model]
        if variant:
            cmd += ["--variant", variant]
        cmd += ["--dir", str(holder), PROBE_PROMPT]
        try:
            done = subprocess.run(cmd, cwd=holder, env=env, capture_output=True, text=True,
                                  timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return {"status": UNAVAILABLE, "model": model, "variant": variant,
                    "detail": f"no answer within {timeout}s",
                    "elapsed_seconds": round(time.time() - started, 3)}

        blob = (done.stdout or "") + (done.stderr or "")
        # OpenCode reports provider trouble on the stream rather than through the exit code, so the
        # text is what has to be read. Truncated hard: an error body is diagnostic, not evidence, and
        # nothing from a provider response should be able to grow without bound in a record.
        failed = done.returncode != 0 or "Error from provider" in blob or "Error:" in blob
        result: dict[str, Any] = {
            "status": UNAVAILABLE if failed else AVAILABLE,
            "model": model,
            "variant": variant,
            "exit_code": done.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "detail": _first_error(blob) if failed else None,
        }
        result.update(_probe_evidence(holder / "probe.db"))
        return result
    finally:
        shutil.rmtree(holder, ignore_errors=True)


def _first_error(blob: str) -> str:
    for line in (blob or "").splitlines():
        stripped = line.strip()
        if "Error" in stripped:
            return stripped[:300]
    return (blob or "").strip()[-300:]


def _probe_evidence(db: Path) -> dict[str, Any]:
    """What the provider said it was, and what it charged, from the probe's own session."""
    try:
        import _profile
    except ImportError:                                    # pragma: no cover - import-path guard
        return {}
    events = _profile.read_parts(Path(db))
    if not events:
        return {"observed": {}, "usage": {}}
    return {"observed": _profile.observed_identity(events), "usage": _profile.usage(events)}


def require(model: str, *, variant: str | None = None, **kw: Any) -> dict[str, Any]:
    """Health, raised into a refusal.

    Callers about to spend a semantic slot use this so an unavailable provider stops the series
    rather than consuming it. It returns the evidence either way; deciding what to do with a refusal
    belongs to the caller, not here.
    """
    got = health(model, variant=variant, **kw)
    got["may_spend"] = got["status"] == AVAILABLE
    return got
