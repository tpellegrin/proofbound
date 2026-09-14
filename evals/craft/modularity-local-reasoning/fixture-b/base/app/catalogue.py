"""The goods this service will sell, and how many are left."""


class Account:
    def __init__(self, user_id: str, region: str, may_order: bool):
        self.user_id = user_id
        self.region = region
        self.may_order = may_order


_ACCOUNTS = {
    "u-1": Account("u-1", "eu", True),
    "u-2": Account("u-2", "us", True),
    "u-3": Account("u-3", "eu", False),
}

_STOCK = {"widget": 4, "gasket": 2, "flange": 1, "sprocket": 3, "cam": 3, "bolt": 3}


def load(user_id: str):
    return _ACCOUNTS.get(user_id)


def may_order(account) -> bool:
    return bool(account and account.may_order)


def in_stock(sku: str, quantity: int) -> bool:
    return sku in _STOCK and _STOCK[sku] >= quantity


def known(sku: str) -> bool:
    return sku in _STOCK


def take(sku: str, quantity: int) -> None:
    _STOCK[sku] -= quantity


def restock() -> None:
    _STOCK.update({"widget": 4, "gasket": 2, "flange": 1, "sprocket": 3, "cam": 3, "bolt": 3})
