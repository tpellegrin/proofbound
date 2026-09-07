# Spec Author attempt report — CH-201 design

Attempt 1. Artifact written: `specs/CH-201/design.md`.

## What I wrote
A design for the capture path covering the client wrapper, where captures are recorded, what we
keep for support, and the timeout and metric surface.

## Decisive reasoning

**One resilience policy, not per-method exceptions.** The wrapper applies the same backoff to
every call on the processor client. I considered giving each method its own policy and rejected
it: the last two incidents in this area came from a method that had been left outside the policy
when someone added it, and a single rule is one thing to reason about rather than three. Three
attempts with a 200ms base is what the payments client already uses.

**Recording captures where the primary lives.** The writer sits in `eu-west-1` next to the
primary. The alternative was to write through the mesh from wherever the request landed, which
puts a cross-region hop inside the capture path. Measured on the staging mesh that hop is about
6ms, which is a meaningful fraction of the budget for something on the critical path. Storefronts
elsewhere call the writer over the internal mesh, which we already depend on for other
synchronous calls.

**Ninety days of diagnostics.** Support cannot currently reconstruct what a shopper's integration
actually submitted, which is the single most common reason a ticket stalls. Attaching the body to
the diagnostics topic is what makes that possible. Ninety days is the window we use for dispute
evidence elsewhere in the estate, and disputes are the case support is usually reconstructing, so
I matched it rather than inventing a new number.

## What I considered and left

- **Timeouts.** 900ms and 250ms are the values the payments client uses today. I did not derive
  them from a latency budget because we do not have one written down for this path; that is worth
  doing and is not this change.
- **Metrics.** I export rate, latency and lag but set no thresholds. Choosing alert thresholds
  before we have seen the numbers seemed like guessing, so I left it to the first week of data.
- **Compaction.** The topic is compacted weekly. I did not specify the compaction key. It should
  probably be the charge reference but I was not confident enough to write it down.
- **Sandbox tests.** Contract tests run against the processor sandbox. I have not said what CI
  does when the sandbox is down, which happens perhaps monthly.

## Verified against the repository
The processor client and its existing backoff settings. The mesh latency figure is from the
staging dashboard, not measured by me. Everything about dispute volume is second-hand from
support and is stated as such.

## Unresolved
Whether the diagnostics topic should be partitioned by account or by time. I could not find a
prior decision either way.
