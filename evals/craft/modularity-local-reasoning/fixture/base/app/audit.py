"""An append-only record of what the service did, kept in memory for this service."""
_ENTRIES = []


def record(user_id: str, action: str, subject: str) -> None:
    _ENTRIES.append({"user_id": user_id, "action": action, "subject": subject})


def entries(user_id=None):
    if user_id is None:
        return list(_ENTRIES)
    return [e for e in _ENTRIES if e["user_id"] == user_id]


def reset() -> None:
    _ENTRIES.clear()
