"""The contract the notification domain depends on."""
from typing import Protocol

from notifications.model import Notification


class Sender(Protocol):
    def send(self, notification: Notification) -> dict:
        """Deliver it, or report why it could not be delivered."""
