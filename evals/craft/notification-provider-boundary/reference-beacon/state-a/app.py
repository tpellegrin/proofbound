"""Application entry point."""
import delivery
from notifications.model import Notification


def notify(user_id: str, channel: str, subject: str, body: str,
           provider: str = "acme") -> dict:
    return delivery.send(Notification(user_id, channel, subject, body), provider)
