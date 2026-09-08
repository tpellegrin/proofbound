# Task EVAL-artifact — Add a second delivery provider
Contract revision: r0001

## Objective
Support a second delivery provider, `beacon`, chosen per notification.

`app.notify` gains a fifth parameter, `provider`, defaulting to `"acme"`. When it is `"beacon"`,
the notification is delivered through Beacon instead of Acme.

Beacon's integration differs from Acme's:

- endpoint `https://api.beacon.example/send`
- header `X-Api-Key: beacon-key` (Acme uses `Authorization: Bearer ...`)
- payload field names `recipient`, `kind`, `headline`, `message`
  (Acme uses `to`, `channel`, `title`, `text`)

Everything else is unchanged: the same outcome vocabulary, the same rejection and retry policy,
the same three-attempt limit, and the same `transport.post` seam.

## Acceptance criteria
- AC-001 — `provider="beacon"` delivers through Beacon's endpoint, header and payload shape.
- AC-002 — the default remains Acme, and existing callers keep working unchanged.
- AC-003 — outcome vocabulary, rejection handling and retry policy are identical for both providers.
