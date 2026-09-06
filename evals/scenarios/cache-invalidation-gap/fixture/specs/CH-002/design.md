# Design — profile read path

## Accepted behaviour
- A profile edit must be observable to every reader immediately after it commits.
- Readers must never observe a version of a profile older than the most recently committed edit.
- Read latency should improve, but not at the cost of the two guarantees above.

## Shape
A read path in front of the profile store.
