"""Providers register a delivery capability; the domain asks for delivery by name.

No protocol class and no injection: a provider is a module that registers a function.
Adding one means adding a module and registering it.
"""
_handlers: dict = {}
DEFAULT = "acme"


def register(name: str, handler) -> None:
    _handlers[name] = handler


def handler_for(name: str):
    try:
        return _handlers[name]
    except KeyError:
        raise LookupError(f"no delivery handler registered for {name!r}") from None
