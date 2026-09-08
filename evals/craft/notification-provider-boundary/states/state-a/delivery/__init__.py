"""Delivery boundary. The notification domain calls `send` and nothing else."""
from delivery.acme import AcmeSender
from notifications.model import Notification

_sender = AcmeSender()


def send(notification: Notification) -> dict:
    return _sender.send(notification)
