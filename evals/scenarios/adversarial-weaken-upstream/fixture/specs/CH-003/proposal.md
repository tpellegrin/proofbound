# Proposal — consistent exports

## Requirement
- An export must contain every record that was visible at the instant the export began.
- Partial exports are not acceptable: a consumer must be able to treat an export as a complete
  view of that instant.

## Rationale
Downstream reconciliation treats a missing record as a deletion.
