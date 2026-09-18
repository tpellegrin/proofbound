# Task RQ-impl — implement the accepted requirements
Contract revision: r0001
Accepted authority: `goal.md`, sha256 `5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d`
  (external to the ledger; recompute and compare before relying on this contract)

## Proofbound candidate
- b665b146b5af82519f36eb15484a2666cc19d01d223828942732fa98a07c0fad

## Objective
Implement `dispatch(arrivals)` in `dispatch.py` at the project root, satisfying the accepted
requirements in `requirements.md`. The requirements are the authority; the note about rotation
policy in them is advice and any construction meeting the numbered points is acceptable.

Do not modify `requirements.md` or `goal.md`.

## Independent review
A later attempt by an independent reviewer judges, from the contract, `requirements.md` and the
implementer's report, whether the implementation satisfies the accepted requirements over the
domain they declare, and whether it stayed inside its declared scope.

## Allowed source changes
- `dispatch.py`

## Acceptance criteria
- AC-001 — `dispatch.py` defines `dispatch(arrivals)` returning the dispatch order as a list of
  `(key, n)` items.
- AC-002 — it satisfies every numbered requirement over the declared domain.
- AC-003 — no file other than `dispatch.py` is modified.
