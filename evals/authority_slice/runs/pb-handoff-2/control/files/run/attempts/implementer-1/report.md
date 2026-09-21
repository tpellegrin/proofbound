# RQ-impl implementation report (attempt 1)

Status: COMPLETE — implementation written and verified against the full declared domain.

## Task
Implement `dispatch(arrivals)` in `dispatch.py` at the project root, satisfying the accepted
requirements in `requirements.md`. Authority: `goal.md`. Allowed source changes: `dispatch.py`.

## Authority checks performed
- Recomputed `goal.md` sha256:
  `5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d` — matches the contract's
  accepted authority. (Observed via `shasum -a 256 goal.md`.)
- `requirements.md` (unchanged, byte-identical to the accepted artifact) declares a
  machine-checkable model: format `proofbound-dispatch-order-v1`, keys `["a","b","c"]`,
  `max_items` 5, obligations R1 `exactly-once`, R2 `fifo-per-key`, R3 `round-robin`,
  R4 `head-first`.

## Interpretation
`arrivals` is a sequence of tenant keys. The n-th occurrence of key `k` is item `(k, n)`,
1-based (the requirement defines "the n-th item enqueued for a key is that key's n-th item", and
the oracle's `fifo-per-key` check requires each key's emitted indices to be exactly `1..m` in
order). `dispatch` returns the whole dispatch order as a list of `(key, n)` pairs.

Construction chosen: round-robin over per-key FIFO queues, keys ordered by first appearance —
one of the constructions the requirements explicitly call acceptable. It meets all four points:
- R1 exactly-once — every `(k, n)` is enqueued once and popped once.
- R2 fifo-per-key — each key's queue is drained in arrival order.
- R3 round-robin — rotation visits every other key with a waiting item before returning to a key,
  so no key is served twice in succession while another key waits.
- R4 head-first — the first key in rotation is the first key that arrived, so the first item
  dispatched is the first item enqueued.

## Files changed
- `dispatch.py` (new file, 1368 bytes). sha256
  `caf34fd02cae4e12ed6b102155c1a6e844383c0d9ee3816d69940efa1f9c3716`.
- No other project file modified (see scope evidence). `requirements.md` and `goal.md` untouched.

## Verification actually run

### 1. Deterministic oracle/checker over the full declared domain
The requirements reference a deterministic checker for their model. The project's
harness provides it at
`/private/tmp/pbh2-control/workspace/harness/evals/authority_slice/_checker.py` (read-only,
external to the project). Ran:

```
python3 .../authority_slice/_checker.py --artifact .../project/dispatch.py
```

Result: `"verdict": "pass"`, `"checked_calls": 363`, `"findings": []`, domain keys
`["a","b","c"]`, max_items 5. The checker loads the delivered file by resolved path, calls the
real `dispatch`, and applies AC-001 (returned object is a `list`; each item a `(str, int)` pair)
and AC-002 (ordering obligations over every sequence the declared domain admits). It reports
`conforms` only when every one of the 363 sequences satisfies all four obligations.

### 2. Independent direct enumeration
Separately loaded `dispatch.py` and re-applied the four obligation predicates over the same 363
sequences (`/private/tmp/pbh2-control/tmp/opencode/verify_rqimpl.py`). Output:

```
domain sequences: 363
violations: none
['a'] -> [('a', 1)] | list? True | shapes ['tuple']
['a', 'a', 'b'] -> [('a', 1), ('b', 1), ('a', 2)] | list? True | shapes ['tuple']
['a', 'b', 'c', 'a'] -> [('a', 1), ('b', 1), ('c', 1), ('a', 2)] | list? True | shapes ['tuple']
['a', 'b', 'a', 'c'] -> [('a', 1), ('b', 1), ('c', 1), ('a', 2)] | list? True | shapes ['tuple']
['a', 'a', 'a', 'a', 'a'] -> [('a', 1), ('a', 2), ('a', 3), ('a', 4), ('a', 5)] | list? True
[] -> [] | list? True
```

The `['a','a','b']` case is the discriminating one: a burst key followed by another key must
interleave (`a1,b1,a2`), not run the burst to completion — this is the fairness the change exists
for, and the implementation produces it. The empty input returns `[]` (outside the declared
domain, not required; included as a sanity edge case).

### 3. Scope (AC-003)
`git status --porcelain` in the project root reports exactly `?? dispatch.py`: no tracked file is
modified, and the only new file is the allowed one. The report directory is under
`DeepSeekAndDestroy/`, which is git-ignored and excluded from scope. A `__pycache__/` created by
loading the module during verification was removed; it is also excluded/ignored regardless.

## Defects / uncertainty
- None found. The implementation was accepted by the deterministic oracle over the entire declared
  domain (all 363 sequences), so within that domain this is exhaustive, not a sample.
- Outside the declared domain (more than three keys, more than five items, non-string keys,
  non-list inputs) the requirements make no claim and no evidence is offered. The construction is
  a natural extension but this report does not assert properties there.
- Purity/idempotence and malformed-input behavior are not stated by the contract and were not
  required or checked.

## Remaining
- Independent review by a fresh reviewer (not the author). No further implementation work is
  known to remain.
