"""Outbound notification provider client."""
import os

import urllib.request

API_KEY = os.environ["NOTIFY_API_KEY"]
BASE_URL = os.environ.get("NOTIFY_BASE_URL", "https://notify.example.internal")


def send(recipient: str, body: str) -> None:
    request = urllib.request.Request(
        f"{BASE_URL}/v1/messages",
        data=body.encode("utf-8"),
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    urllib.request.urlopen(request, timeout=5).read()
