# Spec Author attempt report — CH-203 design

Attempt 1. Artifact written: `specs/CH-203/design.md`.

## What I wrote
A design for moving catalogue prices to integer minor units: the schema change, how the migration
runs, how it is deployed, and how it is checked afterwards.

## Decisive reasoning

**Not carrying two representations.** The thing I most wanted to avoid is a period where both a
float column and an integer column exist and something has to keep them agreeing. That means every
writer has to be correct twice, and it means every reader has to know which one is authoritative
today. The drift we are fixing came from exactly that kind of ambiguity, and I did not want to fix
it by introducing more of it, so the old column goes when the new one is populated.

**One coordinated deploy.** Same reasoning, applied to the service rather than the schema. Rolling
the new version out gradually means some instances writing one representation while others write
the other, for as long as the rollout takes. Doing it in one step keeps the window where behaviour
is ambiguous as small as the deploy itself.

**Using the procedure we already have.** Migrations here follow the runbook in `ops/runbooks/`.
Every migration in this service to date has gone through it, the operators who will run this one
have run it many times, and inventing a bespoke procedure for a single column change seemed like
the riskier choice. Introducing new tooling on a change that touches money felt like two changes
at once.

## What I considered and left

- **Verification sample.** I compare a sample of rows against the finance ledger and have not said
  how large the sample is or how rows are chosen. I also have not said what result would make us
  stop. That should be decided before this runs.
- **Duration.** I record how long the migration takes but state no expectation, so an operator
  watching it has nothing to compare against. I did not have a row-count estimate to build one
  from.
- **Nullability.** I have not said whether the new column is nullable while it is being populated,
  which decides whether writers need to handle a missing value in that window.
- **Reader coverage.** Six services read the catalogue. I have not said which of them are exercised
  before this ships, and I do not have a current list of who reads which fields.

## Verified against the repository
The runbook and the existing migrations under `db/migrations` that follow it. The float column and
its current usage in the catalogue service. The six-reader figure is from the proposal and I did
not independently confirm it.

## Unresolved
Whether finance wants the reconciliation re-run after the change or only spot-checked.
