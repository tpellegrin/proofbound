"""Application entry point."""
from notifications import retry

ENDPOINT = "https://api.acme.example/v1/messages"
API_KEY = "acme-key"


def notify(user_id: str, channel: str, subject: str, body: str) -> dict:
    payload = {"to": user_id, "channel": channel, "title": subject, "text": body}
    headers = {"Authorization": f"Bearer {API_KEY}"}
    status, attempts, message_id = retry.deliver_with_retry(ENDPOINT, headers, payload)
    return {"status": status, "attempts": attempts, "message_id": message_id}
