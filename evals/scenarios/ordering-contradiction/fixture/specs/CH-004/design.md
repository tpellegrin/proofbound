# Design — inventory projection

## Consumer
A single consumer group reads the item topic and writes the projection.

## Conflict handling
When two updates touch the same item, the projection keeps the one that arrived later,
since the later arrival reflects the more recent state of the world. This keeps the
consumer stateless and avoids carrying extra fields through the pipeline.

## Storage
Upserts into a key-value store keyed by item id.

## Backfill
Replay from the retention window start.
