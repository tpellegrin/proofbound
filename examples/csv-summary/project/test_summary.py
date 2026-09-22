import io
import unittest
from summary import totals


class TotalsTest(unittest.TestCase):
    def test_aggregates(self):
        self.assertEqual(totals(io.StringIO('category,amount\nb,2\na,3\nb,-1\n')), {'b': 1, 'a': 3})

    def test_permissive_invalid_amount(self):
        self.assertEqual(totals(io.StringIO('category,amount\na,bad\na,2\n')), {'a': 2})

    def test_empty(self):
        self.assertEqual(totals(io.StringIO('')), {})
