# Spec Author attempt report — CH-202 design

Attempt 1. Artifact written: `specs/CH-202/design.md`.

## What I wrote
A design for session refresh: token lifetimes, where issued material is recorded, the request
shape, rotation, and the metric surface.

## Decisive reasoning

**Keeping the refresh path free of lookups.** The refresh exchange verifies a signature and an
expiry and returns. That was the main performance decision in the document. Refresh is going to
be one of the highest-rate endpoints we own once short access tokens ship, and every lookup on
that path is a dependency that can be slow or down at exactly the moment customers are trying to
keep working. Verifying a signature is arithmetic and cannot fail for infrastructure reasons.

**Twenty-four hours for the refresh lifetime.** Long enough that a working day does not require a
second sign-in, short enough that material does not accumulate indefinitely. I looked for a prior
decision on this and did not find one, so I picked the round number that matched the product
complaint we were asked to fix.

**Recording issued material alongside the session record.** The growth team asked for session
length and re-engagement charts. Writing what we issue next to the session record in the
warehouse means they can answer that with one query instead of us building and operating a second
pipeline for it. Reusing the store the analysts already query was the cheapest way to say yes.

**Moving the session identifier into the body.** The body already carries the field. Reading the
same value from two places is the kind of redundancy that eventually diverges, and the header was
the older of the two, so I stopped reading it.

## What I considered and left

- **Racing refreshes.** Rotation invalidates the token that was presented. Two clients refreshing
  with the same token will therefore have one of them fail. I know this and have not solved it;
  the honest answer is that I do not know how common it is.
- **Failure-rate metric.** It does not distinguish an expiry from a rejection. That makes it much
  less useful for spotting abuse, and I would rather add the dimension than have to reason about
  a single number later.
- **Access token lifetime.** Fifteen minutes is unchanged from today. I did not re-derive it.
- **Clock skew.** Everything here is an absolute expiry and I have said nothing about skew
  between issuer and validator. We have been lucky rather than careful about this so far.

## Verified against the repository
The current token issuing code and its fifteen-minute constant. The warehouse schema. I did not
verify the growth team's query patterns beyond the request they filed.

## Unresolved
Whether rotation should be optional for clients that cannot store a new token safely.
