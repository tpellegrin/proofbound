"""Turn a provider response into a delivery outcome."""


def outcome_for(status_code: int, body: dict, provider: str = "acme") -> str:
    if provider == "beacon":
        if status_code != 200:
            return "rejected"
        result = body.get("result")
        if result == "accepted":
            return "sent"
        if result == "refused":
            return "rejected"
        return "retry"
    if 200 <= status_code < 300:
        return "sent"
    if status_code in (400, 422):
        return "rejected"
    return "retry"
