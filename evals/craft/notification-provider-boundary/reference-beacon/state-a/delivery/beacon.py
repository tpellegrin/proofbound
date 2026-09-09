"""Everything specific to the Beacon provider lives here and nowhere else."""
import transport
from notifications.model import Notification

ENDPOINT = "https://api.beacon.example/send"
API_KEY = "beacon-key"
MAX_ATTEMPTS = 3


class BeaconSender:
    def send(self, notification: Notification) -> dict:
        payload = {
            "recipient": notification.user_id,
            "kind": notification.channel,
            "headline": notification.subject,
            "message": notification.body,
        }
        headers = {"X-Api-Key": API_KEY}
        attempts = 0
        while attempts < MAX_ATTEMPTS:
            attempts += 1
            status, body = transport.post(ENDPOINT, headers, payload)
            if status != 200:
                return {"status": "rejected", "attempts": attempts, "message_id": None}
            # Beacon answers 200 whenever it accepted the request for processing; what it did
            # with the message is in the body.
            result = body.get("result")
            if result == "accepted":
                return {"status": "sent", "attempts": attempts,
                        "message_id": body.get("id")}
            if result == "refused":
                return {"status": "rejected", "attempts": attempts, "message_id": None}
        return {"status": "failed", "attempts": attempts, "message_id": None}
