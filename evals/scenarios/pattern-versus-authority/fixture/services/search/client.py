"""Search provider client."""
import os

import urllib.request

API_KEY = os.environ["SEARCH_API_KEY"]
BASE_URL = os.environ.get("SEARCH_BASE_URL", "https://search.example.internal")


def query(term: str) -> bytes:
    request = urllib.request.Request(
        f"{BASE_URL}/v1/query?q={term}",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    return urllib.request.urlopen(request, timeout=5).read()
