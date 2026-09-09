"""Delivery boundary. The notification domain calls `send` and nothing else."""
from delivery.acme import AcmeSender
from delivery.beacon import BeaconSender
from notifications.model import Notification

_senders = {"acme": AcmeSender(), "beacon": BeaconSender()}
DEFAULT = "acme"


def send(notification: Notification, provider: str = DEFAULT) -> dict:
    return _senders[provider].send(notification)
