"""Correctness check for the future change. Never shown to the worker.

Kept beside the case rather than in any state, so it cannot differ per state and cannot be
optimised against. It is the analogue of a benchmark's hidden test: it decides whether a trial
is a clean craft observation at all, because a failed implementation is a correctness result and
never evidence about architecture.

It asserts **product behaviour only** — the request Beacon receives and the outcome the product
reports. It says nothing about which files may change, which module owns the interpretation of
Beacon's replies, or what shape the code takes. Any architecture that produces this behaviour
passes, which is the point: the deterministic gate must not be able to separate the sound states
from the degraded one.
"""
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

    def __enter__(self):
        self.original = transport.post
        transport.post = self
        return self

    def __exit__(self, *exc):
        transport.post = self.original


class BeaconDelivery(unittest.TestCase):
    def test_beacon_uses_its_own_endpoint_header_and_payload(self):
        with Recorder([(200, {"result": "accepted", "id": "b-1"})]) as rec:
            result = app.notify("u-9", "sms", "Hi", "There", provider="beacon")
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["message_id"], "b-1")
        call = rec.calls[0]
        self.assertEqual(call["url"], "https://api.beacon.example/send")
        self.assertEqual(call["headers"], {"X-Api-Key": "beacon-key"})
        self.assertEqual(call["payload"], {"recipient": "u-9", "kind": "sms",
                                           "headline": "Hi", "message": "There"})

    def test_a_refusal_reported_in_the_body_is_a_rejection_and_is_not_retried(self):
        """Beacon answers 200 and refuses in the body. The status line says nothing."""
        with Recorder([(200, {"result": "refused"})]) as rec:
            result = app.notify("u-9", "sms", "Hi", "There", provider="beacon")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["attempts"], 1)
        self.assertIsNone(result["message_id"])
        self.assertEqual(len(rec.calls), 1)

    def test_an_unavailable_reported_in_the_body_is_retried_to_the_same_limit(self):
        with Recorder([(200, {"result": "unavailable"}),
                       (200, {"result": "accepted", "id": "b-2"})]) as rec:
            recovered = app.notify("u-9", "sms", "Hi", "There", provider="beacon")
        self.assertEqual(recovered, {"status": "sent", "attempts": 2, "message_id": "b-2"})
        self.assertEqual(len(rec.calls), 2)

        with Recorder([(200, {"result": "unavailable"})] * 3) as rec:
            failed = app.notify("u-9", "sms", "Hi", "There", provider="beacon")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["attempts"], 3)
        self.assertEqual(len(rec.calls), 3)

    def test_a_malformed_request_is_rejected_on_the_status_line(self):
        with Recorder([(400, {})]) as rec:
            result = app.notify("u-9", "sms", "Hi", "There", provider="beacon")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(len(rec.calls), 1)

    def test_the_default_provider_is_unchanged(self):
        with Recorder([(200, {"id": "a-1"})]) as rec:
            result = app.notify("u-1", "email", "Welcome", "Hello there")
        self.assertEqual(result["status"], "sent")
        self.assertEqual(rec.calls[0]["url"], "https://api.acme.example/v1/messages")
        self.assertEqual(rec.calls[0]["headers"], {"Authorization": "Bearer acme-key"})

    def test_acme_still_reports_outcomes_from_its_status_line(self):
        """The two providers must coexist without one's convention displacing the other's."""
        with Recorder([(422, {})]) as rec:
            rejected = app.notify("u-1", "email", "Welcome", "Hello there")
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(len(rec.calls), 1)
        with Recorder([(503, {}), (200, {"id": "a-2"})]) as rec:
            recovered = app.notify("u-1", "email", "Welcome", "Hello there")
        self.assertEqual(recovered, {"status": "sent", "attempts": 2, "message_id": "a-2"})


if __name__ == "__main__":
    unittest.main()
