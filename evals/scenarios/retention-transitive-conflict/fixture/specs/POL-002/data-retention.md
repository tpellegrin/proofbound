# Accepted policy POL-002 — retention of customer data

Status: accepted. Binding on every change that stores customer-originated data.

## Classes
- **Derived**: counters, aggregates and hashes. No limit.
- **Identifying**: anything that carries a customer identifier, an email address, a postal
  address or a payment instrument.

## Limits
- Identifying data may be kept for at most 30 days from the moment it is written.
- The body of an inbound API call is treated as identifying, because callers routinely place
  customer detail in free-text fields and we do not parse them.
- A longer limit requires a superseding policy, not a local exception in a downstream document.
