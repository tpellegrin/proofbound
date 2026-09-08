"""Turn a provider response code into a delivery outcome."""


def outcome_for(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "sent"
    if status_code in (400, 422):
        return "rejected"
    return "retry"
