# Proposal CH-201 — resilient checkout capture

Status: accepted.

## Problem
Shoppers abandon checkout when a capture stalls, and support cannot tell a slow capture from a
failed one.

## Constraints
- A capture request that has reached the card processor has moved money. It must not be sent a
  second time; recovery goes through the processor's status lookup, which is safe to repeat.
- The checkout path must keep serving when any one region becomes unavailable. Losing a region
  is a planned event and must not stop shoppers paying.
- This change touches the checkout path, so it is bound by the accepted policy in
  `specs/POL-011/card-data.md`. That policy governs and this proposal does not restate it.

## Non-goals
Changing processors. New payment methods.
