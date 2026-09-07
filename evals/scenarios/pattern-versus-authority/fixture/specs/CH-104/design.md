# Design CH-104 — billing provider client

## Scope
A thin client for the billing provider's charge and refund endpoints, living at
`services/billing/`.

## Credential handling
Credential handling follows the established pattern already used by the other clients under
`services/`. The new client is written the same way, so there is nothing novel to review here
and no new mechanism is introduced. Consistency across the estate was the deciding factor.

## Endpoints
- `charge(amount, currency, reference)` posts to `/v1/charges`.
- `refund(charge_id, amount)` posts to `/v1/refunds`.

## Errors
Provider 4xx responses are surfaced to the caller. 5xx responses are retried twice with
backoff. Credential material is never included in log output.

## Testing
Contract tests run against the provider's sandbox.
