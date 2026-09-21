"""Dispatch order for the shared work queue.

`dispatch(arrivals)` takes the sequence of enqueued tenant keys and returns the order in
which the queued items are served, as a list of ``(key, n)`` pairs where ``(key, n)`` is the
n-th item enqueued for ``key`` (n is 1-based).

Keys are served round-robin, each key draining its own items first-in-first-out, so a burst
from one tenant does not block the others while each tenant's own order is preserved.
"""


def _enumerated(arrivals):
    """Pair each arrival with its 1-based position within its own key."""
    seen = {}
    items = []
    for key in arrivals:
        seen[key] = seen.get(key, 0) + 1
        items.append((key, seen[key]))
    return items


def _queues(arrivals):
    """Per-key FIFO queues plus the keys in order of first appearance."""
    keys = []
    queues = {}
    for item in _enumerated(arrivals):
        key = item[0]
        if key not in queues:
            queues[key] = []
            keys.append(key)
        queues[key].append(item)
    return keys, queues


def dispatch(arrivals):
    """Return the dispatch order for `arrivals` as a list of (key, n) items."""
    keys, queues = _queues(arrivals)
    order = []
    while any(queues[key] for key in keys):
        for key in keys:
            if queues[key]:
                order.append(queues[key].pop(0))
    return order
