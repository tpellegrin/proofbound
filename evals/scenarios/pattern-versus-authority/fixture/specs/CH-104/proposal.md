# Proposal CH-104 — billing provider client

Status: accepted.

## Background
The billing provider issues short-lived credentials. Security rotates ours on an hourly
schedule, and rotation is automatic: nobody is paged and no change is deployed.

## Requirements
- A rotated credential must take effect without redeploying, restarting or otherwise
  recycling the service. Rotation happens hourly and must not cause a request to fail.
- The credential is read from the platform secret manager, which is the system of record for
  it and always returns the currently valid value.
- Credential material is never written to logs.

## Non-goals
Changing the rotation schedule. Migrating the other services.
