# Proposal CH-103 — posting latency

Status: accepted.

## Problem
Customers open the ledger immediately after paying and do not see the charge. Support tickets
follow, and agents cannot tell a slow posting from a failed one.

## Requirement
- Once a charge is posted, it appears in the customer-visible ledger no more than two seconds
  later. This is a product commitment, quoted in the support runbook.
- The two seconds are measured from posting to the charge being returned by a ledger read,
  not to any internal checkpoint.

## Non-goals
Changing the charge posting path itself. Historical backfill.
