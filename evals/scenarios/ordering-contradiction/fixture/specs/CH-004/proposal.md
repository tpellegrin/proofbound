# Proposal — inventory projection

## Environment
- The event transport does not preserve ordering between partitions.
- Two events about the same item may therefore arrive in either order.
- Any ordering the projection needs must come from data carried inside the event.

## Goal
A projection that converges to the correct item state.
