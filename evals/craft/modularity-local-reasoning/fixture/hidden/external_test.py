"""Hidden correctness gate for the external task. Never part of a workspace an agent sees.

Asserts product-visible behaviour only: statuses, bodies, and what a later read observes. It does
not import the storage package, does not reach into any private helper, and asserts nothing about
how the service is arranged — an agent must be free to restructure `app/` as it sees fit.

Each test uses its own account and report, so no test depends on another's cleanup and none needs
to know how or where anything is stored.
"""
import unittest

from app import api, audit, exports


class DownloadProducesWhenMissing(unittest.TestCase):
    def setUp(self):
        audit.reset()

    def test_a_missing_export_is_produced_and_returned(self):
        status, body = api.download_export("u-1", "weekly")
        self.assertEqual(status, 201)
        self.assertIn(b"report,weekly,Ada", body)
        self.assertIn(b"total,9", body)

    def test_an_existing_export_is_returned_as_it_was_created(self):
        created = api.create_export("u-1", "monthly")[1]
        status, body = api.download_export("u-1", "monthly")
        self.assertEqual(status, 200)
        self.assertEqual(body, created)

    def test_two_downloads_agree_and_the_second_finds_the_first(self):
        first_status, first = api.download_export("u-3", "weekly")
        second_status, second = api.download_export("u-3", "weekly")
        self.assertEqual(first_status, 201)
        self.assertEqual(second_status, 200)
        self.assertEqual(first, second)
        self.assertEqual(exports.fetch("u-3", "weekly"), first)

    def test_an_account_that_may_not_export_is_refused_and_keeps_nothing(self):
        self.assertEqual(api.download_export("u-2", "weekly")[0], 403)
        self.assertEqual(api.download_export("u-2", "weekly")[0], 403)
        with self.assertRaises(Exception):
            exports.fetch("u-2", "weekly")

    def test_unknown_account_and_unknown_report_are_still_reported(self):
        self.assertEqual(api.download_export("u-9", "weekly")[0], 404)
        self.assertEqual(api.download_export("u-1", "quarterly")[0], 404)


if __name__ == "__main__":
    unittest.main()
