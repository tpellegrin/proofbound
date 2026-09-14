"""The service's product surface."""
from app import catalogue, consumers, orders


def place_order(user_id: str, sku: str, quantity: int = 1):
    """Place one order.

    Returns `{"status": 201, "order_id": ...}` when the order was placed and every consumer of
    `order.placed` accepted it. An account that may not order gets `403`; an unknown account or sku
    gets `404`; not enough stock gets `409`.
    """
    try:
        order_id, receipt = orders.place(user_id, sku, quantity)
    except LookupError:
        return {"status": 404}
    except orders.OrderRefused:
        return {"status": 403}
    except ValueError:
        return {"status": 409}
    if not receipt.ok:
        return {"status": 500, "order_id": order_id}
    return {"status": 201, "order_id": order_id}


def deliveries():
    """Every consumer delivery this process has seen."""
    return consumers.deliveries()


def reset() -> None:
    """Return the service to its starting state."""
    consumers.reset()
    catalogue.restock()
