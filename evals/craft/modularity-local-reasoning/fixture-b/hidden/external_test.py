"""Hidden correctness gate for the external task. Never part of a workspace an agent sees.

**It calls the product surface and nothing else.** `app.api` for behaviour and `app.api.reset` to
return the service to its starting state — both of which the service's own shipped tests already
use. It never imports `eventbus` or `app.orders`, never names a private helper, and asserts nothing
about file layout, helper decomposition, the return shape of any internal function, or how many
times anything is called.

**Delivery is observed through the product surface.** `app.api.deliveries()` is how the service
already reports what its consumers saw, and it is the only way this gate checks that a consumer
which accepted an announcement was not made to accept it twice.

**`failed` is checked as a set of names.** The task says a collection naming the consumers that
refused; it does not say a list, a tuple or an order, and the contract for the bus states that
delivery order is unspecified. A gate that required a sequence would be requiring an implementation
detail the task never fixes.

**One clause is deliberately not asserted as written.** "Nothing is announced" for 403/404/409 is
checked as the consequence a client can observe — no consumer recorded a delivery — rather than by
reaching into the bus to count publishes, which would pin an internal call pattern.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import api  # noqa: E402


def _names(result):
    """The reported failures, however the implementation chose to collect them."""
    failed = result.get("failed")
    if failed is None:
        return None
    if isinstance(failed, (str, bytes)):
        return {failed if isinstance(failed, str) else failed.decode()}
    try:
        return {str(x) for x in failed}
    except TypeError:
        return None


class PartialAnnouncement(unittest.TestCase):
    """A consumer refusing must not turn a placed order into a failure."""

    maxDiff = None

    def setUp(self):
        api.reset()

    def test_a_fully_accepted_order_is_still_created(self):
        result = api.place_order("u-1", "widget")
        self.assertEqual(result["status"], 201)
        self.assertIn("order_id", result)
        names = {n for n, order in api.deliveries() if order == result["order_id"]}
        self.assertEqual(names, {"warehouse", "shipping", "analytics"})

    def test_a_refused_consumer_makes_the_order_accepted_not_failed(self):
        result = api.place_order("u-2", "gasket")
        self.assertEqual(result["status"], 202, "the order was placed; it is not a 500")
        self.assertIn("order_id", result)

    def test_the_refusing_consumer_is_named(self):
        result = api.place_order("u-2", "gasket")
        self.assertEqual(_names(result), {"shipping"})

    def test_the_consumers_that_accepted_are_not_told_twice(self):
        result = api.place_order("u-1", "gasket")
        deliveries = [n for n, order in api.deliveries() if order == result["order_id"]]
        self.assertEqual(sorted(deliveries), ["analytics", "warehouse"])

    def test_an_unknown_account_is_still_not_found(self):
        self.assertEqual(api.place_order("nobody", "widget")["status"], 404)
        self.assertEqual(api.deliveries(), [])

    def test_an_account_that_may_not_order_is_still_refused(self):
        self.assertEqual(api.place_order("u-3", "widget")["status"], 403)
        self.assertEqual(api.deliveries(), [])

    def test_too_much_stock_is_still_a_conflict(self):
        self.assertEqual(api.place_order("u-1", "flange", 5)["status"], 409)
        self.assertEqual(api.deliveries(), [])


if __name__ == "__main__":
    unittest.main()
