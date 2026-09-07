# Design CH-103 — ledger projection

## Write path
A posted charge is appended to a durable queue and acknowledged to the caller straight away.
The posting path therefore stays fast and is unaffected by ledger load.

## Projector
A projector consumes the queue and applies charges to the ledger tables. It runs on a fixed
schedule and drains whatever has accumulated since the previous pass. The schedule is set to
every 30 seconds, which amortises the write cost across a batch and keeps the write rate on
the ledger tables well inside the provisioned throughput.

## Read path
Ledger reads are served from the ledger tables through a small read cache. Cache entries live
for 5 seconds, which is short enough that a customer refreshing the page sees current data.

## Ordering
Charges carry a sequence number assigned at posting time; the projector applies them in that
order.

## Monitoring
Queue depth, projector pass duration and cache hit rate are exported.
