# DSD Implementer report — RQ-impl (attempt implementer-1)

Status: COMPLETE.

## Task identity
- Task: RQ-impl — implement the accepted requirements.
- Contract: `DeepSeekAndDestroy/plans/slice/runs/r1/contracts/RQ-impl.md` (revision r0001).
- Accepted authority: `goal.md` sha256
  `5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d`.
  Recomputed with `shasum -a 256 goal.md`; matches the contract exactly.
- Allowed source changes (hard boundary): `dispatch.py` only.
- Proofbound candidate: b665b146b5af82519f36eb15484a2666cc19d01d223828942732fa98a07c0fad

## Objective
Implement `dispatch(arrivals)` in `dispatch.py` at the project root satisfying the accepted
requirements in `requirements.md`. `requirements.md` and `goal.md` are authority and were not
modified.

## What changed
- Created `/private/tmp/pbh1-valid/workspace/work/project/dispatch.py` (new file; sha256
  `d998c0eaff9fbc2be8a601d809ae43102afebbe2fc60f4f92a2f67c527a890af`).
- No other project file was added or modified (see scope check).

Implementation: build one FIFO queue per key in first-arrival order, then rotate over the keys that
still have work, popping one item per turn. Each item is emitted as `(key, n)` with `n` 1-indexed.

```python
from collections import deque


def dispatch(arrivals):
    queues = {}
    rotation = deque()

    for key in arrivals:
        if key not in queues:
            queues[key] = deque()
            rotation.append(key)
        queues[key].append(len(queues[key]) + 1)

    order = []
    while rotation:
        key = rotation.popleft()
        order.append((key, queues[key].popleft()))
        if queues[key]:
            rotation.append(key)
    return order
```

### How the code maps to the numbered requirements
- R1 exactly-once: every arrival increments exactly one key's counter and is appended exactly once;
  the loop pops each queued item exactly once, so every `(key, n)` is emitted once and only once.
- R2 fifo-per-key: each key has its own FIFO `deque`, popped head-first, so a key's items leave in
  arrival order.
- R3 round-robin fairness: a key is re-appended to the rotation only after every other key that
  still has work has had a turn, so the same key is never served twice in succession while another
  key is waiting.
- R4 head-first: the first arrival's key is the first element of `rotation`, and its first item is
  the first item dispatched.
- Domain: up to 3 keys and up to 5 items. The implementation does not depend on the domain size
  (it is a general round-robin), but acceptance evidence below covers exactly the declared domain.

## Verification actually performed
Method: exhaustive enumeration of the entire declared domain — all arrival sequences over 3 keys of
length 0..5 (3^0 + 3^1 + ... + 3^5 = 364 sequences) — with each returned order checked against all
four requirements plus return-shape, by an independent checker that recomputes expected per-key
counts from `arrivals` (it does not reuse the implementation's internal state).

Verifier (durable): `DeepSeekAndDestroy/plans/slice/runs/r1/attempts/implementer-1/verify_rq_impl.py`
Verifier output (durable): `.../attempts/implementer-1/verify-output.txt`
Command: `python3 .../attempts/implementer-1/verify_rq_impl.py` (exit 0).

Result:
- `dispatch`: checked 364 arrival sequences, 0 failures.
- Negative controls (each must be rejected by the same checks, demonstrating the checks are not
  vacuous):
  - plain arrival-order (the pre-change behaviour): rejected on 192 sequences, all R3 fairness
    violations (e.g. `['a','a','b'] -> a1,a2,b1`).
  - grouped-by-key: rejected on 306 sequences (R3).
  - drop-duplicates: rejected on 348 sequences (R1).
- Summary line: `RESULT: dispatch_ok=True negative_controls_detected=True`.

Illustrative outputs (direct calls):
- `[] -> []`
- `['a'] -> [('a', 1)]`
- `['a','a','b'] -> [('a',1),('b',1),('a',2)]`
- `['a','b','a','b'] -> [('a',1),('b',1),('a',2),('b',2)]`
- `['a','a','b','b','a'] -> [('a',1),('b',1),('a',2),('b',2),('a',3)]`
- `['a','b','c','a','b'] -> [('a',1),('b',1),('c',1),('a',2),('b',2)]`
- `['c','c','b','a','a'] -> [('c',1),('b',1),('a',1),('c',2),('a',2)]`

## Scope check (AC-003)
- `git status --porcelain` -> only `?? dispatch.py`.
- `git diff --name-only` -> empty (no tracked file modified).
- `goal.md` sha256 matches the contract; `requirements.md` sha256
  `9a4b9568775ecaa675f39cc8d89b06a8ed2a43f0ff72d8b18c4fe7d83e674db3` equals the committed
  `HEAD:requirements.md` hash.
- All work outside the project tree (verifier, output) was written only under the assigned
  attempt evidence directory, which the scope baseline excludes.

## Acceptance-criteria mapping
- AC-001: `dispatch.py` defines `dispatch(arrivals)` returning a list of `(key, n)` tuples — met
  (shape checked over all 364 sequences).
- AC-002: every numbered requirement holds over the declared domain — met (exhaustive, 0 failures).
- AC-003: no file other than `dispatch.py` modified — met (scope check above).

## Defects / uncertainty / decision boundaries
- None blocking. The implementation is a superset of the declared domain (works for any number of
  keys/items), but no claim of unbounded-domain correctness is asserted; acceptance evidence covers
  exactly the declared domain (<=3 keys, <=5 items) as `requirements.md` states.
- Key equality uses normal Python dict/hash semantics; `requirements.md` says keys are opaque, so no
  key-specific behaviour is assumed.
- No consequential decision outside authority was encountered, so no `DECISION_REQUIRED`.

## Remaining work
None. Fresh independent review is required before acceptance (implementer does not self-approve).
