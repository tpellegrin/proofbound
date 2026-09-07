# Proposal CH-102 — session service resilience

Status: accepted.

## Requirements
- The service continues to issue and validate sessions when any single availability zone
  becomes unreachable. Losing one zone is an expected event, not an incident.
- Validation stays correct under partition: an expired session is never accepted.
- Session issuance is not a read-only path; it must keep working, not merely degrade to reads.

## Out of scope
Multi-region. Session content changes. Client SDK work.
