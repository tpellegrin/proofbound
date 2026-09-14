"""Placing an order and telling the rest of the service about it."""
import eventbus

from app import audit, catalogue, consumers


class OrderRefused(Exception):
    pass


_SEQUENCE = {"n": 0}


def _next_id() -> str:
    _SEQUENCE["n"] += 1
    return f"o-{_SEQUENCE['n']}"


def place(user_id: str, sku: str, quantity: int):
    """Record the order and announce it. Returns the order id and the fan-out receipt."""
    account = catalogue.load(user_id)
    if account is None or not catalogue.known(sku):
        raise LookupError(f"unknown account or sku: {user_id} {sku}")
    if not catalogue.may_order(account):
        raise OrderRefused(user_id)
    if not catalogue.in_stock(sku, quantity):
        raise ValueError(f"insufficient stock for {sku}")
    catalogue.take(sku, quantity)
    order_id = _next_id()
    audit.record(user_id, "order.place", order_id)
    receipt = eventbus.publish(consumers.TOPIC,
                               {"order_id": order_id, "user_id": user_id, "sku": sku,
                                "quantity": quantity, "region": account.region})
    return order_id, receipt
