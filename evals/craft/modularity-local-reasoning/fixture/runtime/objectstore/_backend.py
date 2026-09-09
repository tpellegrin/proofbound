"""The filesystem backend. Nothing outside this package may depend on this layout."""
import os
import tempfile
from pathlib import Path

_ROOT_ENV = "OBJECTSTORE_ROOT"
_FLAKE_ENV = "OBJECTSTORE_FLAKY_WRITES"


def root() -> Path:
    path = Path(os.environ.get(_ROOT_ENV, tempfile.gettempdir())) / "objectstore-data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _flakes_remaining() -> int:
    try:
        return int(os.environ.get(_FLAKE_ENV, "0"))
    except ValueError:
        return 0


def _consume_flake() -> bool:
    """Simulated transient backend failure, used by the package's own tests."""
    remaining = _flakes_remaining()
    if remaining <= 0:
        return False
    os.environ[_FLAKE_ENV] = str(remaining - 1)
    return True


def write_segment(path: Path, payload: bytes) -> None:
    if _consume_flake():
        raise OSError("backend refused the write")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Written beside the target and renamed, so a reader never observes a partial object.
    handle, staging = tempfile.mkstemp(dir=str(path.parent))
    with os.fdopen(handle, "wb") as out:
        out.write(payload)
    os.replace(staging, path)


def read_segment(path: Path) -> bytes:
    if _consume_flake():
        raise OSError("backend refused the read")
    return path.read_bytes()
