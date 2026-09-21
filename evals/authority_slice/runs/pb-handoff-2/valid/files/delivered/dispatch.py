from collections import deque


def dispatch(arrivals):
    queues = {}
    key_order = []
    for key in arrivals:
        if key not in queues:
            queues[key] = deque()
            key_order.append(key)
        queues[key].append(key)

    served = {}
    order = []
    index = 0
    remaining = len(arrivals)
    total = len(key_order)
    while remaining:
        while not queues[key_order[index]]:
            index = (index + 1) % total
        key = key_order[index]
        queues[key].popleft()
        served[key] = served.get(key, 0) + 1
        order.append((key, served[key]))
        index = (index + 1) % total
        remaining -= 1
    return order
