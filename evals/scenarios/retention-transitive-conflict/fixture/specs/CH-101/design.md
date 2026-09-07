# Design CH-101 — support desk request history

Status: accepted.

## Goal
Let a support agent see what a customer's integration actually sent, so a failed call can be
explained without asking the customer to reproduce it.

## Constraints inherited
This change stores customer-originated data, so it is bound by the accepted retention policy
in `specs/POL-002/data-retention.md`. That policy governs; this document does not restate its
limits and does not have the authority to vary them.

## Shape
- A capture step on the ingress path writes a record per inbound call.
- A reader API serves those records to the support console.
- Records are addressable by customer and by time range.
