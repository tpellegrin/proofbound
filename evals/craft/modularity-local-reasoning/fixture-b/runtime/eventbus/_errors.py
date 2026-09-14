"""The errors callers are allowed to see. Anything else raised in here is a defect."""


class DuplicateConsumer(Exception):
    """Raised when a consumer name is registered twice for the same topic."""


class UnknownConsumer(Exception):
    """Raised when a name that was never registered for the topic is used."""


class _HandlerRefused(Exception):
    """Internal: a handler's exception, normalised before it reaches a receipt."""
