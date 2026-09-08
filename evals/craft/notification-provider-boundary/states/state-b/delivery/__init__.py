"""Delivery boundary. The notification domain calls `deliver` and nothing else."""
from delivery import registry


def deliver(notification) -> dict:
    from delivery.providers import acme  # noqa: F401  (registers on import)
    return registry.handler_for(registry.DEFAULT)(notification)
