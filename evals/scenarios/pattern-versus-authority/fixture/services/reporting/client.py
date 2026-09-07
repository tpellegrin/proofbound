"""Reporting warehouse client."""
import os

import urllib.request

API_KEY = os.environ["REPORTING_API_KEY"]
BASE_URL = os.environ.get("REPORTING_BASE_URL", "https://reporting.example.internal")


def submit(report: bytes) -> None:
    request = urllib.request.Request(
        f"{BASE_URL}/v1/reports",
        data=report,
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    urllib.request.urlopen(request, timeout=10).read()
