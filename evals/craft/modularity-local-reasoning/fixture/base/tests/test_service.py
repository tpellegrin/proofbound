"""The service's own tests. These ship with the repository."""
import unittest

from app import api, audit


class ExportService(unittest.TestCase):
    def setUp(self):
        audit.reset()

    def test_creating_an_export_returns_the_rendered_report(self):
        status, body = api.create_export("u-1", "weekly")
        self.assertEqual(status, 201)
        self.assertIn(b"report,weekly,Ada", body)
        self.assertIn(b"total,9", body)

    def test_a_created_export_can_be_downloaded(self):
        api.create_export("u-1", "monthly")
        status, body = api.download_export("u-1", "monthly")
        self.assertEqual(status, 200)
        self.assertIn(b"total,20", body)

    def test_a_free_plan_may_not_export(self):
        self.assertEqual(api.create_export("u-2", "weekly")[0], 403)

    def test_an_unknown_report_is_reported(self):
        self.assertEqual(api.create_export("u-1", "quarterly")[0], 404)

    def test_creating_an_export_is_audited(self):
        api.create_export("u-3", "weekly")
        self.assertEqual([e["action"] for e in audit.entries("u-3")], ["export.create"])


if __name__ == "__main__":
    unittest.main()
