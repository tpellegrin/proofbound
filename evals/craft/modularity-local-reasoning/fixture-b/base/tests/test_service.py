"""The service's own suite. It must keep passing."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import api  # noqa: E402


class PlacingAnOrder(unittest.TestCase):
    def setUp(self):
        api.reset()

    def test_a_placed_order_is_announced_to_every_consumer(self):
        result = api.place_order("u-1", "widget")
        self.assertEqual(result["status"], 201)
        names = {name for name, order in api.deliveries() if order == result["order_id"]}
        self.assertEqual(names, {"warehouse", "shipping", "analytics"})

    def test_an_unknown_account_is_not_found(self):
        self.assertEqual(api.place_order("nobody", "widget")["status"], 404)

    def test_an_unknown_sku_is_not_found(self):
        self.assertEqual(api.place_order("u-1", "nonesuch")["status"], 404)

    def test_an_account_that_may_not_order_is_refused(self):
        self.assertEqual(api.place_order("u-3", "widget")["status"], 403)

    def test_more_than_the_stock_is_a_conflict(self):
        self.assertEqual(api.place_order("u-1", "flange", 5)["status"], 409)

    def test_nothing_is_delivered_when_the_order_is_refused(self):
        api.place_order("u-3", "widget")
        self.assertEqual(api.deliveries(), [])


if __name__ == "__main__":
    unittest.main()
