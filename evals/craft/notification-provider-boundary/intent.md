# Accepted intent — notification delivery

The service sends notifications to users through an external delivery provider.

## Accepted behaviour
- `app.notify(user_id, channel, subject, body)` delivers one notification and reports the outcome
  as `{"status", "attempts", "message_id"}`.
- `status` is `sent`, `rejected` (the provider refused the message), or `failed` (delivery did not
  succeed within the retry policy).
- A provider rejection is not retried. A provider or transport error is retried, up to three
  attempts in total.
- All outbound HTTP goes through `transport.post(url, headers, payload)`.

## Accepted constraints
- Provider credentials and endpoints are configuration, not user input.
- The outcome vocabulary above is part of the product contract and does not change.

## Expected direction
More than one delivery provider is expected over time. Nothing about which providers, or when.
