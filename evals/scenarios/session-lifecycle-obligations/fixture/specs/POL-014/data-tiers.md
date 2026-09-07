# Accepted policy POL-014 — where each class of data may live

Status: accepted. Binding on every change that persists data.

## Tiers
- **Secrets tier** — the only place a bearer credential may be written. Encrypted, access
  logged, no bulk export, no analyst access.
- **Operational tier** — application state. Broad service access, no analyst access.
- **Analytics tier** — anything an analyst may query. Bulk export is expected and routine.

## Rules
- Anything that grants access on presentation is a bearer credential, whatever it is called
  locally. Refresh material is included.
- A bearer credential must never be written outside the secrets tier, in whole or in part.
- Hashing is not an exemption unless the stored form cannot be replayed.
