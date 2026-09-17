# Task RG-consistency — do the accepted artifacts cohere as one change?
Contract revision: r0001
Accepted authority: `intent.md`, sha256 `a7e16b87c8dc8131edd027f289bb5bdcd80bc0fcca02e0827a88646280b70a04`
  (external to the ledger; recompute and compare before relying on this contract)

## Review purpose
- consistency-reflection

## Proofbound candidate
- <CANDIDATE>

## Objective
The artifacts of this change have been individually accepted and frozen together as the candidate
named above. Judge whether they cohere *as a whole*: whether the external accepted intent
(`intent.md`, whose identity is recorded in the protocol) and the accepted specification, taken
together, describe one consistent change that can be implemented without contradiction.

This is not a re-review of either artifact on its own. A set of individually sound artifacts can
still be jointly incoherent, and that is the question. Write your finding into the report; change no
file.

Note honestly in your report that this candidate has a single member, so coherence here is a
narrower question than it would be for a multi-artifact change.

## Independent review
This task is itself a reflection: the attempt is performed by a role qualified for
`consistency-reflection`, and its report is the evidence the parent accepts against.

## Allowed source changes
NONE

## Acceptance criteria
- AC-001 — the report addresses the intent and the specification together rather than one at a time.
- AC-002 — the report names any incoherence found, or states plainly that none was found.
