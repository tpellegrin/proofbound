# Proposed requirements — fair dispatch for the shared work queue

One queue serves work for several tenants. Today it dispatches strictly in arrival order, so a
tenant that enqueues a burst delays everyone behind it for as long as the burst lasts. Support has
three complaints about this in a month and they are all the same complaint.

The queue should stay fair to tenants without becoming unpredictable to any one of them.

## What must become true

`dispatch(arrivals)` decides the order in which queued items are served. `arrivals` is the sequence
of items that were enqueued, each identified by the key of the tenant that enqueued it; the n-th
item enqueued for a key is that key's n-th item.

1. **Nothing is lost and nothing is served twice.** Every enqueued item is dispatched exactly once.

2. **Arrival order is preserved.** Items are dispatched in the order they arrived, across all
   tenants. Operators reason about this queue by watching it drain, and an item that arrived
   earlier being served later is the behaviour that makes an incident hard to read.

3. **No tenant is served twice while another waits.** A key is never dispatched twice in
   succession while an item belonging to a different key is still waiting. This is the fairness
   the change exists for.

4. **The queue still starts where it used to.** The first item dispatched is the first item that
   arrived. A fair queue that reorders the head for no reason is a behaviour change nobody asked
   for.

## The domain these hold over

Up to three tenant keys and up to five queued items, which is the domain the requirements are
stated for and the domain any acceptance evidence covers. Nothing here claims a property of
unbounded queues; a later requirement may extend the domain, and would need its own evidence.

## What must not change

- An item is dispatched only after it has been enqueued.
- Keys are opaque. No key is privileged over another, and nothing infers priority from the key
  itself.

## A note on how, which is advice and not a requirement

Round-robin over the keys with a queue per key is the obvious construction, and it is one
acceptable construction rather than the required one. Serving whichever eligible key has waited
longest, or whichever has the fewest items left, would also be acceptable if it satisfies the
numbered points. Nothing will be rejected for choosing a different rotation, and the numbered
points are the whole of what is required.

## Machine-checkable model

The obligations above, in the form the deterministic checker reads. This block is part of the
document: if it disagrees with the prose above, that disagreement is a defect in this document.

```json
{
  "format": "proofbound-dispatch-order-v1",
  "keys": ["a", "b", "c"],
  "max_items": 5,
  "obligations": {
    "R1": "exactly-once",
    "R2": "fifo-global",
    "R3": "round-robin",
    "R4": "head-first"
  }
}
```
