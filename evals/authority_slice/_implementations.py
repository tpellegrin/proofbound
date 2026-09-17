#!/usr/bin/env python3
"""Implementations the oracle is checked against, before it is trusted to judge anything.

A suite that only ever sees one correct implementation measures nothing. Three populations:

* the **reference**, which must conform — otherwise the requirements are not satisfiable in the way
  the case claims;
* a **sound alternative** using a different mechanism, which must *also* conform. If the oracle
  rejected it, the oracle would be testing resemblance to the reference rather than the stated
  requirements — the specificity control that calibration V2 failed
  ([evaluation.md §E24.3](../../docs/architecture/proofbound/evaluation.md#e243-controls-and-what-they-cannot-prove));
* **defective variants**, each breaking something specific, so the oracle is shown to discriminate
  rather than merely to accept.
"""
from __future__ import annotations

from _obligations import items_of


def _queues(arrivals: "list[str]") -> "tuple[list[str], dict[str, list]]":
    """Per-key FIFO queues, and the keys in order of first arrival."""
    order: "list[str]" = []
    queues: "dict[str, list]" = {}
    for item in items_of(arrivals):
        key = item[0]
        if key not in queues:
            queues[key] = []
            order.append(key)
        queues[key].append(item)
    return order, queues


def reference(arrivals: "list[str]") -> list:
    """Cyclic round-robin over the keys, FIFO within each, starting at the first arrival."""
    keys, queues = _queues(arrivals)
    out = []
    while any(queues[k] for k in keys):
        for key in keys:
            if queues[key]:
                out.append(queues[key].pop(0))
    return out


def fewest_remaining(arrivals: "list[str]") -> list:
    """Sound alternative: serve whichever eligible key has the fewest items left.

    Different mechanism, same obligations. Eligibility excludes the key just served whenever
    another key still has work, which is what keeps requirement 3; the first dispatch is pinned to
    the first arrival, which is what keeps requirement 4.
    """
    keys, queues = _queues(arrivals)
    out: list = []
    last: "str | None" = None
    while any(queues[k] for k in keys):
        waiting = [k for k in keys if queues[k]]
        if last is None:
            choice = keys[0]
        else:
            eligible = [k for k in waiting if k != last] or waiting
            choice = min(eligible, key=lambda k: (len(queues[k]), keys.index(k)))
        out.append(queues[choice].pop(0))
        last = choice
    return out


def global_fifo(arrivals: "list[str]") -> list:
    """Today's behaviour: strict arrival order. Breaks the fairness requirement."""
    return items_of(arrivals)


def lifo_per_key(arrivals: "list[str]") -> list:
    """Round-robin, but a key's own items come out backwards."""
    keys, queues = _queues(arrivals)
    out = []
    while any(queues[k] for k in keys):
        for key in keys:
            if queues[key]:
                out.append(queues[key].pop())
    return out


def drops_last(arrivals: "list[str]") -> list:
    """Loses one item."""
    return reference(arrivals)[:-1]


def duplicates_head(arrivals: "list[str]") -> list:
    """Serves the first item twice."""
    out = reference(arrivals)
    return [out[0], *out]


def key_sorted(arrivals: "list[str]") -> list:
    """Drains one key completely before starting the next."""
    _keys, queues = _queues(arrivals)
    out = []
    for key in sorted(queues):
        out.extend(queues[key])
    return out


def skips_the_head(arrivals: "list[str]") -> list:
    """Round-robin that starts on the second key whenever there is one."""
    keys, queues = _queues(arrivals)
    rotation = keys[1:] + keys[:1] if len(keys) > 1 else keys
    out = []
    while any(queues[k] for k in keys):
        for key in rotation:
            if queues[key]:
                out.append(queues[key].pop(0))
    return out


#: Name, callable, and whether the case's obligations should hold for it.
CONFORMING = {"reference": reference, "fewest-remaining": fewest_remaining}
DEFECTIVE = {"global-fifo": global_fifo, "lifo-per-key": lifo_per_key,
             "drops-last": drops_last, "duplicates-head": duplicates_head,
             "key-sorted": key_sorted, "skips-the-head": skips_the_head}
