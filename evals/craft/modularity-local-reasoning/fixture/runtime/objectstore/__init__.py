"""objectstore — durable storage for opaque application artefacts.

Public surface: `put`, `get`, `delete`, `exists`, and the errors they raise. Everything else in
this package is an implementation detail and may change between releases.
"""
from objectstore._errors import NotFound, StorageUnavailable
from objectstore._store import delete, exists, get, put

__all__ = ["put", "get", "delete", "exists", "NotFound", "StorageUnavailable"]
__version__ = "1.4.0"
