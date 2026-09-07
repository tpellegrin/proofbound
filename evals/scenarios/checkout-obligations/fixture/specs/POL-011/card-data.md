# Accepted policy POL-011 — handling of cardholder data

Status: accepted. Binding on every change that touches the checkout path.

## Scope
Any field submitted by a shopper during payment, including the whole request body of a
checkout call, because shoppers paste card detail into free-text fields and we do not parse
them.

## Rules
- Cardholder data may be held only for as long as an in-flight authorisation needs it, and in
  no case beyond 24 hours.
- Debug and diagnostic copies are in scope. There is no exemption for troubleshooting.
- A downstream document may tighten this. It may not relax it, and it may not create an
  exception for itself.
