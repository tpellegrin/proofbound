"""Application entry point."""
import delivery
from notifications.model import Notification


def notify(user_id: str, channel: str, subject: str, body: str) -> dict:
    return delivery.deliver(Notification(user_id, channel, subject, body))
