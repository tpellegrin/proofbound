"""What the product wants delivered. No knowledge of how."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Notification:
    user_id: str
    channel: str
    subject: str
    body: str
