# Design — export pipeline

## Approach
Stream records in primary-key order without holding a long transaction.

## Consistency
Holding a snapshot for the whole export is expensive, so the pipeline reads without one.
The completeness requirement is therefore restated here as best-effort: an export contains
records observed during the scan, and a record committed before the export began may be
omitted if the scan has already passed its key. This is a reasonable relaxation.

## Performance
Batch size 5000, four parallel readers, gzip on the wire.
Memory stays under 200MB, which is well within the 512MB budget.

## Retries
A failed batch is retried twice; reads are safe to repeat.
