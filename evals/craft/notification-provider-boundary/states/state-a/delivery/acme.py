"""Everything specific to the Acme provider lives here and nowhere else."""
import transport
from notifications.model import Notification

ENDPOINT = "https://api.acme.example/v1/messages"
API_KEY = "acme-key"
MAX_ATTEMPTS = 3


class AcmeSender:
    def send(self, notification: Notification) -> dict:
        payload = {
            "to": notification.user_id,
            "channel": notification.channel,
            "title": notification.subject,
            "text": notification.body,
        }
        headers = {"Authorization": f"Bearer {API_KEY}"}
        attempts = 0
        while attempts < MAX_ATTEMPTS:
            attempts += 1
            status, body = transport.post(ENDPOINT, headers, payload)
            if 200 <= status < 300:
                return {"status": "sent", "attempts": attempts,
                        "message_id": body.get("id")}
            if status in (400, 422):
                return {"status": "rejected", "attempts": attempts, "message_id": None}
        return {"status": "failed", "attempts": attempts, "message_id": None}
