"""Fair dispatch for the shared work queue.

``dispatch(arrivals)`` takes the sequence of enqueued items, each identified by
the key of the tenant that enqueued it, and returns the order in which those
items should be served as a list of ``(key, n)`` pairs.  The n-th item enqueued
for a key is that key's n-th item.

The queue rotates over the tenants that still have work, so a tenant's burst
cannot block another tenant, while each tenant's own items keep their arrival
order.
"""

from collections import deque


def dispatch(arrivals):
    queues = {}
    rotation = deque()

    for key in arrivals:
        if key not in queues:
            queues[key] = deque()
            rotation.append(key)
        queues[key].append(len(queues[key]) + 1)

    order = []
    while rotation:
        key = rotation.popleft()
        order.append((key, queues[key].popleft()))
        if queues[key]:
            rotation.append(key)
    return order
