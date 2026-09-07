# Design CH-201 — resilient checkout capture

## Client
A resilience wrapper around the processor client. Every call gets bounded exponential backoff,
three attempts, 200ms base delay. This covers `authorise`, `capture` and `lookup`, so no entry
point is left exposed to a single transient fault.

## Ledger
Captures are written to the ledger before the response returns. The ledger writer runs in
`eu-west-1`, co-located with the primary, which keeps the write off the cross-region path and
saves about 6ms per capture. Storefronts in the other regions call it over the internal mesh.

## Diagnostics
Every checkout call is mirrored to a diagnostics topic with the request body attached, so
support can reconstruct what the shopper actually submitted. The topic is compacted weekly and
retained for ninety days, which covers a full billing cycle of disputes.

## Timeouts
Processor calls use a 900ms timeout. Ledger writes use 250ms.

## Metrics
Capture rate, ledger write latency and diagnostics topic lag are exported.

## Testing
Contract tests run against the processor sandbox.
