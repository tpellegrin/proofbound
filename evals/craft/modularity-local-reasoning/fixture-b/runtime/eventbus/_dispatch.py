"""Isolation, copying and re-entrancy — the decisions this package exists to own.

Callers see `subscribe`, `publish` and a receipt. They are not expected to know that each consumer
is handed its own copy of the event, that a handler which raises is caught one consumer at a time,
how an arbitrary exception becomes a receipt entry, or that publishing from inside a handler is
queued rather than interleaved.
"""
import copy

from eventbus import _registry
from eventbus._errors import UnknownConsumer
from eventbus._receipt import Receipt

_MAX_REASON = 200

_state = {"delivering": False, "pending": []}


def subscribe(topic: str, name: str, handler) -> None:
    """Register `handler` under `name` for `topic`."""
    if not topic or not isinstance(topic, str):
        raise ValueError("topic must be a non-empty string")
    if not name or not isinstance(name, str):
        raise ValueError("name must be a non-empty string")
    if not callable(handler):
        raise TypeError("handler must be callable")
    _registry.add(topic, name, handler)


def _reason(exc: BaseException) -> str:
    """One consumer's failure, as text a caller can report without catching anything."""
    text = str(exc).strip() or exc.__class__.__name__
    return text[:_MAX_REASON]


def _deliver_one(handler, event):
    """Each consumer gets its own copy, so one that mutates what it received is alone in it."""
    handler(copy.deepcopy(event))


def _fan_out(topic, event):
    delivered, failures = [], []
    for name, handler in _registry.listeners(topic):
        try:
            _deliver_one(handler, event)
        except Exception as exc:                            # noqa: BLE001 - isolation is the point
            failures.append((name, _reason(exc)))
        else:
            delivered.append(name)
    return Receipt(topic, delivered, failures)


def _drain():
    """Events raised during delivery, after the fan-out that raised them has finished."""
    while _state["pending"]:
        topic, event = _state["pending"].pop(0)
        _fan_out(topic, event)


def publish(topic: str, event) -> Receipt:
    """Deliver `event` to every consumer of `topic` and report what happened."""
    if not topic or not isinstance(topic, str):
        raise ValueError("topic must be a non-empty string")
    if _state["delivering"]:
        _state["pending"].append((topic, copy.deepcopy(event)))
        return Receipt(topic, queued=True)
    _state["delivering"] = True
    try:
        receipt = _fan_out(topic, event)
        _drain()
    finally:
        _state["delivering"] = False
        _state["pending"].clear()
    return receipt


def consumers(topic: str) -> tuple:
    """The names registered for `topic`, in no particular order."""
    return _registry.names(topic)


def confirm(topic: str, name: str) -> bool:
    """Whether `name` is registered for `topic`. Raises `UnknownConsumer` for an empty topic."""
    known = _registry.names(topic)
    if not known:
        raise UnknownConsumer(f"no consumer is registered for {topic!r}")
    return name in known


def reset() -> None:
    """Forget every registration. Intended for tests and process teardown."""
    _registry.clear()
    _state["delivering"] = False
    _state["pending"].clear()
