"""Who is listening to what.

Kept apart from delivery so that the order consumers happen to be stored in is one module's
business. Callers are told the order is unspecified, and this is where that freedom lives.
"""
from eventbus._errors import DuplicateConsumer

_TOPICS = {}


def add(topic, name, handler):
    consumers = _TOPICS.setdefault(topic, [])
    if any(existing == name for existing, _ in consumers):
        raise DuplicateConsumer(f"{name!r} is already registered for {topic!r}")
    consumers.append((name, handler))


def names(topic):
    return tuple(name for name, _ in _TOPICS.get(topic, ()))


def listeners(topic):
    """A snapshot, so a handler that subscribes during delivery does not change this fan-out."""
    return tuple(_TOPICS.get(topic, ()))


def clear():
    _TOPICS.clear()
