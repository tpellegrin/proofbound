# Runbook — schema changes

How the catalogue team has run schema changes for the last two years. Followed by every
migration in `db/migrations` to date.

## Standard sequence
1. Announce in `#catalogue-ops`.
2. Take the write lock.
3. Run the migration script. Scripts transform the affected column **in place**: the old value
   is overwritten with the new representation in the same statement, which is why they complete
   in a single pass and need no staging table.
4. Verify row counts.
5. Release the write lock.

## Notes
- We do not keep a copy of the previous representation. Storage was the original reason and
  nobody has revisited it.
- If a migration turns out to be wrong, the recovery path is a restore from the nightly
  snapshot, accepting the loss of anything written since.
