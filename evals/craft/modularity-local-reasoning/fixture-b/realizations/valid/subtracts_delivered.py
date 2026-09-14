"""Valid, and structurally different: never touches `failures`.

Works from `receipt.ok` and the set of consumers the service itself registered, taking the ones the
receipt did not list as delivered. The contract says `delivered` and `failures` together name every
consumer registered when the publish began, which is what makes this sound.
"""
from app import catalogue, consumers, orders

_STATUS = {True: 201, False: 202}


def _refused(receipt):
    registered = {"warehouse", "shipping", "analytics"}
    return sorted(registered - set(receipt.delivered))


def place_order(user_id: str, sku: str, quantity: int = 1):
    try:
        order_id, receipt = orders.place(user_id, sku, quantity)
    except LookupError:
        return {"status": 404}
    except orders.OrderRefused:
        return {"status": 403}
    except ValueError:
        return {"status": 409}
    response = {"status": _STATUS[receipt.ok], "order_id": order_id}
    if not receipt.ok:
        response["failed"] = tuple(_refused(receipt))
    return response


def deliveries():
    return consumers.deliveries()


def reset() -> None:
    consumers.reset()
    catalogue.restock()
