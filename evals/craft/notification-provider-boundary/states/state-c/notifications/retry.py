"""Retry loop for notification delivery."""
import transport
from notifications import status

MAX_ATTEMPTS = 3


def deliver_with_retry(url, headers, payload) -> tuple:
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        attempts += 1
        code, body = transport.post(url, headers, payload)
        outcome = status.outcome_for(code)
        if outcome == "sent":
            return "sent", attempts, body.get("id")
        if outcome == "rejected":
            return "rejected", attempts, None
    return "failed", attempts, None
