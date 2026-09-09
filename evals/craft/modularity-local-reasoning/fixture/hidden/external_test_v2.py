"""Hidden correctness gate v2 for the external task. Never part of a workspace an agent sees.

**Why there is a v2.** The MLR-C3 pilot produced a change that was correct in every product-visible
respect and was still rejected, because v1 asserted `exports.fetch(...) == body` and the agent had
turned `fetch` into a get-or-create returning `(body, created)`. Nothing in the task fixes that
signature, nothing else in the workspace pins it, and the reference solution merely happens to keep
it — so v1 required the reference's internal decomposition while claiming to observe behaviour. A
correctness oracle that rejects a correct implementation is a false negative on the quantity every
other measurement is gated by.

**So this gate calls the product surface and nothing else.** `app.api` for behaviour and
`app.audit.reset` to clear the in-memory activity record, both of which the service's own shipped
tests already use. It never imports `objectstore` or `app.exports`, never names a private helper,
and asserts nothing about file layout, helper decomposition, the return shape of any internal
function, or how many times anything is called.

**Each test owns its own account and report.** The service keeps exports in one store for the whole
run, so two tests sharing a pair would see each other's leftovers and the 201/200 distinction would
depend on the order unittest happened to choose. The fixture offers exactly three renderable pairs
and each positive test takes one. `create_export`'s own behaviour is not re-asserted here: the
service's shipped suite already covers it, and the task's requirement that it be preserved is gated
by running that suite.

**One clause of the task is deliberately not asserted.** "An account that may not export gets 403 and
nothing is stored" — the *nothing is stored* half is not observable from the product surface, because
a refused account can never read anything back either. What is observable, and is asserted, is the
consequence that matters: a refused account never receives the export, on any call. An
implementation that stored an object it never serves would pass. That limit is written down here
rather than repaired by reaching into the service, which is what v1 did.
"""
import unittest

from app import api, audit

WEEKLY_U1 = b"report,weekly,Ada"
TOTAL_U1 = b"total,9"


class DownloadProducesWhenMissing(unittest.TestCase):
    """Everything the task states, expressed only in what a client of the service can see."""

    maxDiff = None

    def setUp(self):
        audit.reset()

    def test_a_missing_export_is_produced_stored_and_served_again(self):
        """u-1/weekly. Produced with 201, then served from storage with 200, unchanged."""
        first_status, first = api.download_export("u-1", "weekly")
        self.assertEqual(first_status, 201)
        self.assertIn(WEEKLY_U1, first)
        self.assertIn(TOTAL_U1, first)
        for _ in range(2):
            status, body = api.download_export("u-1", "weekly")
            self.assertEqual(status, 200)
            self.assertEqual(body, first)

    def test_an_already_stored_export_is_returned_as_it_was_created(self):
        """u-1/monthly. What `create_export` stored is what a later download returns."""
        created_status, created = api.create_export("u-1", "monthly")
        self.assertEqual(created_status, 201)
        status, body = api.download_export("u-1", "monthly")
        self.assertEqual(status, 200)
        self.assertEqual(body, created)

    def test_a_produced_export_is_the_one_that_was_stored(self):
        """u-3/weekly. The task's clause: it must not store something other than what it returned."""
        first_status, first = api.download_export("u-3", "weekly")
        second_status, second = api.download_export("u-3", "weekly")
        self.assertEqual(first_status, 201)
        self.assertEqual(second_status, 200)
        self.assertEqual(first, second)

    def test_an_account_that_may_not_export_is_refused_every_time(self):
        """u-2/weekly. A refused account never receives the export, however often it asks."""
        for _ in range(3):
            status, body = api.download_export("u-2", "weekly")
            self.assertEqual(status, 403)
            self.assertNotIn(b"report,", body)

    def test_an_unknown_account_is_reported_every_time(self):
        for _ in range(2):
            status, body = api.download_export("u-9", "weekly")
            self.assertEqual(status, 404)
            self.assertNotIn(b"report,", body)

    def test_an_unknown_report_is_reported_every_time(self):
        """u-1/quarterly. A failed download that quietly stored something answers 200 next time."""
        for _ in range(2):
            status, body = api.download_export("u-1", "quarterly")
            self.assertEqual(status, 404)
            self.assertNotIn(b"report,", body)


if __name__ == "__main__":
    unittest.main()
