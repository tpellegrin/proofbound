"""The accepted behaviour of the notification service.

One expected behaviour, asserted through the public entry point. Everything here is part of the
product contract described in the intent: the outcome vocabulary, the request the provider
receives, and the rejection and retry policy.
"""
import sys
import unittest

import app
import transport


class Recorder:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, payload):
        self.calls.append({"url": url, "headers": headers, "payload": payload})
        return self.responses.pop(0)


class NotificationBehaviour(unittest.TestCase):
    def drive(self, responses):
        recorder = Recorder(responses)
        original = transport.post
        transport.post = recorder
        try:
            result = app.notify("u-1", "email", "Welcome", "Hello there")
        finally:
            transport.post = original
        return result, recorder

    def test_a_delivered_notification_reports_the_provider_message_id(self):
        result, rec = self.drive([(200, {"id": "m-42"})])
        self.assertEqual(result, {"status": "sent", "attempts": 1, "message_id": "m-42"})
        self.assertEqual(len(rec.calls), 1)

    def test_the_request_carries_the_expected_endpoint_headers_and_payload(self):
        _, rec = self.drive([(200, {"id": "m-1"})])
        call = rec.calls[0]
        self.assertEqual(call["url"], "https://api.acme.example/v1/messages")
        self.assertEqual(call["headers"], {"Authorization": "Bearer acme-key"})
        self.assertEqual(call["payload"], {"to": "u-1", "channel": "email",
                                           "title": "Welcome", "text": "Hello there"})

    def test_a_rejected_notification_is_not_retried(self):
        result, rec = self.drive([(422, {})])
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["attempts"], 1)
        self.assertIsNone(result["message_id"])
        self.assertEqual(len(rec.calls), 1)

    def test_a_server_error_is_retried_and_can_still_succeed(self):
        result, rec = self.drive([(503, {}), (200, {"id": "m-7"})])
        self.assertEqual(result, {"status": "sent", "attempts": 2, "message_id": "m-7"})
        self.assertEqual(len(rec.calls), 2)

    def test_repeated_server_errors_fail_after_three_attempts(self):
        result, rec = self.drive([(500, {}), (502, {}), (503, {})])
        self.assertEqual(result, {"status": "failed", "attempts": 3, "message_id": None})
        self.assertEqual(len(rec.calls), 3)


if __name__ == "__main__":
    unittest.main()
