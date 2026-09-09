"""Errors that cross the package boundary, and one that does not."""


class NotFound(Exception):
    """No object is stored under the requested key."""


class StorageUnavailable(Exception):
    """The backend could not be reached, after the package exhausted its own attempts."""


class _ChecksumMismatch(Exception):
    """Internal: a segment read back differently from what was written."""
