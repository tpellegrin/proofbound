# Proposal CH-202 — session refresh

Status: accepted.

## Problem
Customers are signed out mid-task because access tokens are short-lived and there is no way to
extend a session without a full sign-in.

## Requirements
- When an operator revokes a session, that revocation takes effect at once. A revoked session
  must not be able to obtain further access, and "at once" means the next request, not the
  next expiry.
- Clients on the previous major version must keep working for two releases after this change
  ships. They are widely deployed and cannot be upgraded on our schedule.
- This change persists new material, so it is bound by the accepted tiering policy in
  `specs/POL-014/data-tiers.md`. That policy governs; this proposal does not restate it.

## Non-goals
Changing the sign-in flow. Device management.
