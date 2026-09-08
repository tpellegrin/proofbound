"""Correctness check for the future change. Never shown to the worker.

Kept beside the case rather than in any state, so it cannot differ per state and cannot be
optimised against. It is the analogue of a benchmark's hidden test: it decides whether a trial
is a clean craft observation at all, because a failed implementation is a correctness result and
never evidence about architecture.
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
        with Recorder([(200, {"id": "b-1"})]) as rec:
            result = app.notify("u-9", "sms", "Hi", "There", provider="beacon")
        self.assertEqual(result["status"], "sent")
        call = rec.calls[0]
        self.assertEqual(call["url"], "https://api.beacon.example/send")
        self.assertEqual(call["headers"], {"X-Api-Key": "beacon-key"})
        self.assertEqual(call["payload"], {"recipient": "u-9", "kind": "sms",
                                           "headline": "Hi", "message": "There"})

    def test_beacon_keeps_the_same_outcome_and_retry_policy(self):
        with Recorder([(422, {})]) as rec:
            rejected = app.notify("u-9", "sms", "Hi", "There", provider="beacon")
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(len(rec.calls), 1)
        with Recorder([(500, {}), (500, {}), (500, {})]) as rec:
            failed = app.notify("u-9", "sms", "Hi", "There", provider="beacon")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["attempts"], 3)

    def test_the_default_provider_is_unchanged(self):
        with Recorder([(200, {"id": "a-1"})]) as rec:
            result = app.notify("u-1", "email", "Welcome", "Hello there")
        self.assertEqual(result["status"], "sent")
        self.assertEqual(rec.calls[0]["url"], "https://api.acme.example/v1/messages")
        self.assertEqual(rec.calls[0]["headers"], {"Authorization": "Bearer acme-key"})


if __name__ == "__main__":
    unittest.main()
