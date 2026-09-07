# Specification CH-101 — request history store

## Record
Each inbound call produces one record containing the route, the response status, the latency,
the caller's account id, and the full body exactly as it was received.

## Storage
- Records are appended to a partitioned table, partitioned by day.
- Partitions are never dropped. Support and finance have both asked for historical lookups,
  and the console offers a date picker with no lower bound.
- Compression is applied to partitions older than seven days.

## Reader API
- `GET /history?account=<id>&from=<ts>&to=<ts>` returns matching records, newest first.
- Results are capped at 500 records per response, with a continuation token.

## Operations
Dashboards report ingest rate, partition size and query latency.
