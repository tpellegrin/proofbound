"""Key derivation, retry policy and checksum verification.

These are the decisions the package exists to own. Callers see `put`, `get`, `delete` and `exists`,
and are not expected to know how a key becomes a path, how many times a failed write is retried, or
that anything is checksummed at all.
"""
import hashlib
import time

from objectstore import _backend
from objectstore._errors import NotFound, StorageUnavailable, _ChecksumMismatch

_ATTEMPTS = 3
_BACKOFF_SECONDS = 0.0
_FANOUT = 2


def _path_for(key: str):
    """Two levels of fan-out keeps any one directory small as the store grows."""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    root = _backend.root()
    return root / digest[:_FANOUT] / digest[_FANOUT:_FANOUT * 2] / f"{digest}.blob"


def _checksum(payload: bytes) -> bytes:
    return hashlib.sha256(payload).digest()


def _with_retries(operation):
    last = None
    for attempt in range(_ATTEMPTS):
        try:
            return operation()
        except OSError as exc:
            last = exc
            if attempt + 1 < _ATTEMPTS and _BACKOFF_SECONDS:
                time.sleep(_BACKOFF_SECONDS * (2 ** attempt))
    raise StorageUnavailable(str(last))


def put(key: str, payload: bytes) -> None:
    """Store `payload` under `key`, replacing whatever was there before."""
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    body = bytes(payload)
    framed = _checksum(body) + body
    path = _path_for(key)
    _with_retries(lambda: _backend.write_segment(path, framed))


def get(key: str) -> bytes:
    """Return what was last stored under `key`, or raise `NotFound`."""
    path = _path_for(key)
    if not path.exists():
        raise NotFound(key)
    framed = _with_retries(lambda: _backend.read_segment(path))
    digest, body = framed[:32], framed[32:]
    if _checksum(body) != digest:
        raise _ChecksumMismatch(key)
    return body


def exists(key: str) -> bool:
    return _path_for(key).exists()


def delete(key: str) -> None:
    """Remove `key` if present. Removing an absent key is not an error."""
    path = _path_for(key)
    if path.exists():
        path.unlink()
