"""What the service did, kept in memory for the lifetime of the process."""
_ENTRIES = []


def record(user_id: str, action: str, detail: str) -> None:
    _ENTRIES.append({"user_id": user_id, "action": action, "detail": detail})


def entries():
    return list(_ENTRIES)


def reset() -> None:
    _ENTRIES.clear()
