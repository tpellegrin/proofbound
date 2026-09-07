# Proposal CH-203 — catalogue price representation

Status: accepted.

## Problem
Prices are stored as floating point and rounding drift has reached the point where finance
reconciliation fails.

## Requirements
- Move price storage to integer minor units.
- Readers on the current release must keep working while the change rolls out. The catalogue is
  read by six services and they do not deploy together.
- The rollout must not take the catalogue offline. Reads and writes continue throughout.
- Any migration must be reversible on its own, without restoring a backup. We must be able to
  put the data back the way it was if reconciliation still fails afterwards.

## Non-goals
Changing the price API shape. Currency support.
