"""Who may see what. Nothing here touches storage."""
from dataclasses import dataclass

_ACCOUNTS = {
    "u-1": {"name": "Ada", "plan": "team", "region": "eu"},
    "u-2": {"name": "Grace", "plan": "free", "region": "us"},
    "u-3": {"name": "Alan", "plan": "team", "region": "eu"},
}


@dataclass(frozen=True)
class Account:
    user_id: str
    name: str
    plan: str
    region: str


class UnknownAccount(Exception):
    pass


def load(user_id: str) -> Account:
    try:
        raw = _ACCOUNTS[user_id]
    except KeyError:
        raise UnknownAccount(user_id) from None
    return Account(user_id, raw["name"], raw["plan"], raw["region"])


def may_export(account: Account) -> bool:
    return account.plan != "free"
