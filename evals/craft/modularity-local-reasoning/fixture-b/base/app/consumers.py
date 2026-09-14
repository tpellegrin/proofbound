"""The parts of the service that react to an order being placed.

Each registers itself with the bus under a name. What they do here is deliberately small: the point
of the fixture is what the service does with the outcome of a fan-out, not what a warehouse does.
"""
import eventbus

from app import audit

TOPIC = "order.placed"

_DELIVERIES = []
# An order whose sku is in here makes the shipping consumer refuse, which is how the service's
# partial-failure behaviour is exercised without reaching into the bus.
UNSHIPPABLE = {"gasket"}


def _warehouse(event):
    _DELIVERIES.append(("warehouse", event["order_id"]))


def _shipping(event):
    if event["sku"] in UNSHIPPABLE:
        raise RuntimeError(f"no carrier for {event['sku']}")
    _DELIVERIES.append(("shipping", event["order_id"]))


def _analytics(event):
    _DELIVERIES.append(("analytics", event["order_id"]))


def register() -> None:
    eventbus.subscribe(TOPIC, "warehouse", _warehouse)
    eventbus.subscribe(TOPIC, "shipping", _shipping)
    eventbus.subscribe(TOPIC, "analytics", _analytics)


def deliveries():
    """Every delivery this process has seen, oldest first."""
    return list(_DELIVERIES)


def reset() -> None:
    _DELIVERIES.clear()
    eventbus.reset()
    audit.reset()
    register()
