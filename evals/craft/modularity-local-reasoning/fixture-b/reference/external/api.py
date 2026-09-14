"""Valid: asks the receipt which consumers refused."""
from app import catalogue, consumers, orders


def place_order(user_id: str, sku: str, quantity: int = 1):
    try:
        order_id, receipt = orders.place(user_id, sku, quantity)
    except LookupError:
        return {"status": 404}
    except orders.OrderRefused:
        return {"status": 403}
    except ValueError:
        return {"status": 409}
    if receipt.failures:
        return {"status": 202, "order_id": order_id,
                "failed": [name for name, _ in receipt.failures]}
    return {"status": 201, "order_id": order_id}


def deliveries():
    return consumers.deliveries()


def reset() -> None:
    consumers.reset()
    catalogue.restock()
