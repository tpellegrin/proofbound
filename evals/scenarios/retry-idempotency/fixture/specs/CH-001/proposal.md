# Proposal — resilient charge submission

## Problem
Transient network faults cause charge submissions to fail before we learn their outcome.

## Constraints
- Once a submission has been handed to the payment network it has an externally visible effect on the
  customer's account, and that effect cannot be reversed by us.
- The system must never repeat a submission that has reached the payment network.
- Recovery after an ambiguous failure must go through the reconciliation query, which is safe to repeat.

## Non-goals
Changing the payment provider. Offline queuing.
