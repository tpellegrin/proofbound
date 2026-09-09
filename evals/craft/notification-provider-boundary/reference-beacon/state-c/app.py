"""Application entry point."""
from notifications import retry

PROVIDERS = {
    "acme": {
        "endpoint": "https://api.acme.example/v1/messages",
        "headers": {"Authorization": "Bearer acme-key"},
        "fields": ("to", "channel", "title", "text"),
    },
    "beacon": {
        "endpoint": "https://api.beacon.example/send",
        "headers": {"X-Api-Key": "beacon-key"},
        "fields": ("recipient", "kind", "headline", "message"),
    },
}


def notify(user_id: str, channel: str, subject: str, body: str,
           provider: str = "acme") -> dict:
    spec = PROVIDERS[provider]
    names = spec["fields"]
    payload = dict(zip(names, (user_id, channel, subject, body)))
    status, attempts, message_id = retry.deliver_with_retry(
        spec["endpoint"], spec["headers"], payload, provider)
    return {"status": status, "attempts": attempts, "message_id": message_id}
