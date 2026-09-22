"""Summarize a category,amount CSV; permissive parsing is the historical API."""
import csv
from collections import defaultdict


def totals(stream):
    result = defaultdict(int)
    for row in csv.DictReader(stream):
        try:
            result[row['category']] += int(row['amount'])
        except (KeyError, ValueError, TypeError):
            continue
    return dict(result)
