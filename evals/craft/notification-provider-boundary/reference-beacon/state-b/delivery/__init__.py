"""Delivery boundary. The notification domain calls `deliver` and nothing else."""
from delivery import registry


def deliver(notification, provider: str = registry.DEFAULT) -> dict:
    from delivery.providers import acme, beacon  # noqa: F401  (register on import)
    return registry.handler_for(provider)(notification)
