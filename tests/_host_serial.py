"""A lock for test modules that read or assert host-level state.

Some suites here construct semantic views and materialise arms in the system temp directory, and
some *assert that nothing of the kind is present* — cross-slot isolation is checked against the
host, and it cannot tell one process's scratch directory from a previous slot's residue. So two
such suites running at once fail each other: observed twice, 25 and 29 failures, every one of them
the §11 G residue stop and none of them a defect.

The fix is not to weaken the residue check — that check is the reason the isolation guarantee means
anything. It is to make the suites take turns. A module that touches host state calls `serialise()`
from `setUpModule` and `release()` from `tearDownModule`; a second process reaching the same point
waits for the first rather than racing it.

Within one `unittest discover` run this is free: modules execute one at a time, so the lock is
uncontended. It earns its keep across processes — a reviewer running a focused module while a full
run is in progress, which is exactly how the two observed failures happened.
"""
from __future__ import annotations

import errno
import fcntl
import os
import tempfile
import time
from pathlib import Path

#: One lock for every suite that touches host state, because they all contend for the same thing:
#: the contents of the system temp directory.
LOCK_PATH = Path(tempfile.gettempdir()) / "proofbound-host-tests.lock"

#: How long to wait for another run to finish. Long enough for a full suite (about eight minutes
#: here), short enough that a stale holder is reported rather than waited on forever.
WAIT_SECONDS = 900.0

_handle = None


def serialise(module_name: str, *, wait_seconds: float = WAIT_SECONDS) -> None:
    """Wait until no other process is running a host-state suite, then claim the turn."""
    global _handle
    if _handle is not None:                                  # pragma: no cover - nested call
        return
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = open(LOCK_PATH, "a+", encoding="utf-8")          # noqa: SIM115 - held until release
    deadline = time.monotonic() + max(0.0, wait_seconds)
    while True:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError as exc:
            if exc.errno not in (errno.EAGAIN, errno.EACCES):  # pragma: no cover - unexpected
                handle.close()
                raise
            if time.monotonic() >= deadline:
                holder = ""
                try:
                    handle.seek(0)
                    holder = handle.read()[:200].strip()
                except OSError:                               # pragma: no cover
                    pass
                handle.close()
                raise RuntimeError(
                    f"{module_name} needs exclusive use of host temp state and waited "
                    f"{wait_seconds:.0f}s for another run to finish"
                    + (f" (holder recorded: {holder})" if holder else "")
                    + ". Run the suite one process at a time; these tests assert that no stray "
                      "semantic view or arm materialisation exists, and a concurrent run creates "
                      "exactly that.")
            time.sleep(0.25)
    try:
        handle.seek(0)
        handle.truncate()
        handle.write(f"{module_name} pid={os.getpid()} at={time.time():.0f}\n")
        handle.flush()
    except OSError:                                           # pragma: no cover
        pass
    _handle = handle


def release() -> None:
    """Give up the turn. Safe to call when it was never claimed."""
    global _handle
    if _handle is None:
        return
    try:
        fcntl.flock(_handle.fileno(), fcntl.LOCK_UN)
    finally:
        _handle.close()
        _handle = None
