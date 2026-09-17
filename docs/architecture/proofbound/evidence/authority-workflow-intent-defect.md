# The authority chain's blind spot: nobody reviews the intent

**Dated 2026-09-17.** What `pb-authority-demo-2` established, and why it stopped.

The successor demonstration was built to carry accepted intent through specification, challenge,
candidate formation, a fresh-context handoff, implementation, review and acceptance. It stopped at
the sixth paid attempt, before the handoff, because a fresh reviewer showed that the accepted intent
it was all built on could not be satisfied.

This document records the defect and the structural gap it exposes. The run's own narrative,
evidence and spend are in `demo/pb-authority-demo-2/run-report.md`.

## The defect

`intent.md` stated seven numbered requirements for a `retry_after` query on a token-bucket rate
limiter. Three of them cannot hold together.

- **Requirement 1** says the returned delay must reach an admitting instant when the clock is
  advanced by it, and must exceed the mathematically exact requirement by no more than four units in
  the last place of the resulting instant.
- **Requirement 4** says that with no intervening calls the value never increases as the clock
  advances.
- **Requirement 7** says that when no finite delay can satisfy requirement 1, the answer is
  `math.inf`.

Each is unconditional. Together they are inconsistent, because the predicate *"a finite delay
satisfying requirement 1 exists"* is not monotone in the clock. There are reachable states where it
holds at one instant and fails a moment later, and requirements 1 and 7 then mandate a finite answer
followed by `math.inf` — an increase, which requirement 4 forbids.

Measured, against the real limiter arithmetic with exact rational comparisons: for a bucket last
updated at `-7.155015362133442` with capacity 2 and refill `0.10978710655568508`, the excess ratio
alternates between 3.174 and 7.174 on successive 1e-7 steps, straddling the four-unit bound. A
strictly forward scan of 1200 refused instants found 599 transitions from a finite answer to
`math.inf`.

Requirement 7 was also ambiguous about its own predicate. Its normative sentence said "cannot satisfy
requirement 1", which includes the excess bound; its parenthetical gloss said "no wait I can express
will get you admitted", which is the weaker reading that ignores the bound. The two readings pick out
different states, and the specification could conform to either.

## Why it needed a negative clock, and why that is not an excuse

The violation needs the admitting instant to fall near zero while the bucket's last update is far
from it — reachable when the injected clock reads negative. `math.ulp` is finest near zero, so a
rounding error far below one unit in the last place of the *delay* becomes several units in the last
place of the *instant*.

Neither the intent nor any specification restricted the clock's domain, and the limiter's existing
code handles negative readings without complaint. The state is inside the domain the documents claim.

## How it survived six paid attempts

The uncomfortable part is not the defect. It is that every check that should have caught it was
looking somewhere else.

- The private witness implementation, written to prove the intent satisfiable, was exercised over
  non-negative clocks only. It passes the external behavioural suite at a worst excess of 1.000 units
  in the last place — and fails a negative-clock check, returning a finite delay where requirement 7
  demands `math.inf`. The satisfiability argument was only ever an argument about half the domain.
- The external behavioural suite, written specifically to fix the predecessor's boundary blindness,
  used clock bases `0.0`, `1.0`, `1000.0`, `1234.56789`, `1e6` and `1e9`. All non-negative.
- Three separate agent searches reported worst-case excesses of about 1.25, 1.42 and 1.48 units in
  the last place. All three sampled non-negative clocks.

The first thing that looked at negative clocks found the problem. It was the aggregate consistency
reflection, and what it actually found was a narrower symptom — a scoping mismatch between the
specification and requirement 7. Repairing that symptom is what exposed the inconsistency underneath,
because the repair made the specification say what the intent says, and what the intent says cannot be
done.

## The structural gap

Every artifact downstream of the intent had an independent challenge by a reviewer that had not
produced it. The intent had none. It entered the chain as an input, frozen by assertion, and the only
thing standing between a defective intent and everything built on it was the parent's own care in
writing it.

The chain is therefore sound in exactly the way it advertises — it did catch this, twice over, and it
stopped rather than proceeding — and it is expensive in a way it need not be. Six paid attempts and a
spent repair cycle were the price of discovering something that was true before the first of them ran.

## What would close it

An intent-challenge stage, run as an ordinary task with its own contract and its own fresh reviewer,
asking a different question from every later review. Not "is this specification faithful to the
intent" but "can this intent be satisfied at all, and are its requirements jointly consistent over
the domain it leaves unrestricted".

No new machinery is required. Contracts, attempts, review purposes and evidence gates already exist
and already work. The change is that the intent becomes a member of the chain rather than an input to
it — which also means it acquires what every other member already has: an identity, a recorded review,
and a gate that can refuse.

Both demonstrations to date stopped at findings that such a stage would plausibly have caught before
any money was spent.
