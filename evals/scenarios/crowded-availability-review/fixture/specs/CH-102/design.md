# Design CH-102 — session service resilience

## Topology
Three zones, `az-a`, `az-b` and `az-c`, each running a stateless validator fleet behind the
regional load balancer. Session records live in a replicated store with a copy in every zone.

## Issuance
Issuance needs a monotonic counter so that a reissued session always sorts after the one it
replaces. A single counter service owns it. That service is deployed in `az-a`, where the
store's primary also lives, which keeps the counter write off the cross-zone path and saves
roughly 4ms per issuance. Validators in the other zones call it over the internal network.

## Health checking
Instances are removed from the load balancer when they fail a health check. The check hits
`/healthz` and expects a 200.

## Timeouts
Validator calls to the store use a 250ms timeout. Issuance calls to the counter service use
750ms. Retries are bounded at two.

## Errors
The service returns a 4xx for a bad session and a 5xx for anything else. Clients are expected
to treat 5xx as retryable.

## Rollout
Canary in one zone, then the rest.
