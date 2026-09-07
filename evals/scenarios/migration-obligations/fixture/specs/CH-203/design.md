# Design CH-203 — catalogue price representation

## Schema
Add `price_minor` as an integer column. Drop the existing `price` float column in the same
release, once the new column is populated, so the table does not carry two sources of truth.

## Migration
The migration follows the team's established runbook in `ops/runbooks/schema-changes.md`. No
new procedure is introduced and no new tooling is needed; operators already know this sequence
and have run it many times.

## Rollout
Deploy the new service version to all instances together. A staged rollout would mean both
representations being written at once, which is exactly the ambiguity this change removes.

## Verification
Compare a sample of rows against the finance ledger after the migration completes.

## Monitoring
Migration duration and post-migration read latency are recorded.
