# Task EVAL-artifact — Add a second delivery provider
Contract revision: r0002

## Objective
Support a second delivery provider, `beacon`, chosen per notification.

`app.notify` gains a fifth parameter, `provider`, defaulting to `"acme"`. When it is `"beacon"`,
the notification is delivered through Beacon instead of Acme.

Beacon's integration differs from Acme's:

- endpoint `https://api.beacon.example/send`
- header `X-Api-Key: beacon-key` (Acme uses `Authorization: Bearer ...`)
- payload field names `recipient`, `kind`, `headline`, `message`
  (Acme uses `to`, `channel`, `title`, `text`)
- Beacon answers `200` to every request it accepts for processing and reports what happened in
  the response body: `{"result": "accepted", "id": ...}` means it took the message,
  `{"result": "refused"}` means it will not send it, and `{"result": "unavailable"}` means it
  could not be reached right now. A malformed request answers `400`.

## Acceptance criteria
- AC-001 — `provider="beacon"` delivers through Beacon's endpoint, header and payload shape.
- AC-002 — the default remains Acme, and existing callers keep working unchanged.
- AC-003 — the outcome vocabulary is identical for both providers. Beacon's `refused` reports
  `rejected` and is not retried; Beacon's `unavailable` is retried, up to the same three attempts
  in total; a Beacon `400` is `rejected`.
