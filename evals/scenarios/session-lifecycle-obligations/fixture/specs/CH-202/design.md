# Design CH-202 — session refresh

## Tokens
Access tokens stay at 15 minutes. A refresh token is issued alongside and lives for 24 hours.
Presenting a valid, unexpired refresh token returns a fresh access token. The refresh path is
deliberately cheap: it verifies the token signature and expiry and returns, with no lookups on
the hot path.

## Storage
Issued refresh tokens are written to the events warehouse alongside the session record, so the
growth team can chart session length and re-engagement without a separate pipeline.

## Request shape
Clients send the session identifier in the request body. The `X-Session-Id` header used by the
current clients is no longer read; it was redundant once the body carried the field.

## Rotation
A refresh returns a new refresh token and invalidates the presented one.

## Metrics
Refresh rate, refresh failure rate and token age at refresh are exported.
