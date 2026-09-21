# RQ-impl implementer report (attempt 1)

Task: RQ-impl — implement the accepted requirements. Contract revision r0001.
Attempt evidence dir: `/private/tmp/pbh2-valid/workspace/work/project/DeepSeekAndDestroy/plans/slice/runs/r1/attempts/implementer-1`.

## Conclusion

`dispatch(arrivals)` is implemented in `dispatch.py` at the project root and satisfies all four
numbered requirements (R1 exactly-once, R2 fifo-per-key, R3 round-robin, R4 head-first) over the
declared domain. The deterministic oracle `_obligations.py` reports **363/363 arrival sequences
conform, 0 failing** (`check_implementation` -> `conforms: true, failing_sequences: 0`). Only
`dispatch.py` was added; no other project file changed.

## Authority and contract read

- `goal.md` sha256 recomputed = `5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d`,
  identical to the accepted authority named in `RQ-impl.md` and `RQ-intent.md`/`RQ-consistency.md`.
- `requirements.md` sha256 = `9a4b9568775ecaa675f39cc8d89b06a8ed2a43f0ff72d8b18c4fe7d83e674db3`. It is the
  behavioural authority: 4 numbered points, plus the machine-checkable model
  (`proofbound-dispatch-order-v1`, keys `["a","b","c"]`, `max_items` 5, obligations R1..R4).
- `RQ-impl.md`: objective is `dispatch(arrivals)` returning the dispatch order as a list of
  `(key, n)` items; AC-001..AC-003; `Allowed source changes: dispatch.py` (hard boundary).

## Work performed

Added `dispatch.py` (sha256 `8afa7491c7db479a1dcb4b3a07f369a8a590131158916c06d1204f748aa84e9d`).

Construction: a FIFO `deque` per key, keys tracked in first-appearance order, and a single cursor
that advances to the next key with a pending item after every dispatch. This is the round-robin
rotation named as advice in the requirements; the numbered points are what it is judged on.

Why this and not a naive "one item per key per pass" loop: a pass-based round robin can emit two
items of one key back-to-back when a later key has more items. Concretely, for
`["a","b","b","b","a"]` a pass-based loop yields `a1,b1,b2,a2,b3`, where `b1` is immediately
followed by `b2` while `a2` is still waiting — an R3 violation. The advancing-cursor version yields
`a1,b1,a2,b2,b3`, which satisfies R3. This case is a genuine discriminator between the two
constructions.

Properties by construction:
- R1: every item is appended once and popped once.
- R2: each key's deque preserves arrival order; the n-th pop for a key is its n-th arrival.
- R3: the cursor always moves after a dispatch and scans forward, so a key is only served twice in
  succession when no other key has a pending item (the checker's exact `_round_robin` predicate).
- R4: the cursor starts on the first-appearance key, whose head is `arrivals[0]`.

Keys are opaque: ordering among keys is first-appearance only, and no priority is inferred from a
key's value.

## Verification actually performed

Command (run from the project root environment, Python 3.14.7):

```
python3 /private/tmp/pbh2-valid/tmp/opencode/verify_rq_impl.py
```

The script loads the authoritative oracle at
`/private/tmp/pbh2-valid/workspace/harness/evals/authority_slice/_obligations.py`, parses the model
out of the real `requirements.md` bytes, imports the real `dispatch.py`, and runs the oracle's own
domain enumeration and predicates. It is a scratch harness outside the project tree, so it is not a
project change.

Observed output (verbatim):

```
model: {"format": "proofbound-dispatch-order-v1", "keys": ["a", "b", "c"], "max_items": 5, "obligations": {"R1": "exactly-once", "R2": "fifo-per-key", "R3": "round-robin", "R4": "head-first"}}
check_implementation: {"conforms": true, "failing_sequences": 0, "sequences": 363, "violated": {}}
satisfiable_everywhere: {"satisfiable": true, "sequences": 363, "unserviceable": [], "unserviceable_count": 0}
first_conflict: None
sample ['a', 'b', 'b', 'b', 'a'] -> [('a', 1), ('b', 1), ('a', 2), ('b', 2), ('b', 3)]
extra [] -> [] violations: ['R4']
extra ['z'] -> [('z', 1)] violations: []
extra ['z', 'z', 'z'] -> [('z', 1), ('z', 2), ('z', 3)] violations: []
extra ['x', 'y', 'x', 'y', 'x', 'y'] -> [('x', 1), ('y', 1), ('x', 2), ('y', 2), ('x', 3), ('y', 3)] violations: []
extra ['p', 'p', 'q', 'p', 'q', 'q', 'p'] -> [('p', 1), ('q', 1), ('p', 2), ('q', 2), ('p', 3), ('q', 3), ('p', 4)] violations: []
```

- `check_implementation` runs the real implementation over all 363 sequences in the declared domain
  and applies the oracle's R1..R4 predicates: 0 failures, nothing violated.
- `satisfiable_everywhere` independently confirms the accepted requirements are jointly satisfiable
  over the domain (0 unserviceable), consistent with the consistency reflection.
- The extra sequences are outside the declared domain and are informational only; they show the
  construction generalizes (more keys, longer queues). The `[]` entry "violates" R4 only because
  the oracle's `head_first` requires a non-empty order; the empty queue has no first item, and the
  declared domain is lengths 1..5, so this is a boundary, not an acceptance failure.

Scope evidence (project root, `git status --porcelain`): only `?? dispatch.py`. `goal.md` and
`requirements.md` hashes are unchanged from before the edit (see above). No test or authority file
was modified, weakened, or bypassed.

## Acceptance criteria

- AC-001: `dispatch.py` defines `dispatch(arrivals)` returning a list of `(key, n)` items — verified
  by import and by the oracle consuming the result (`check_implementation`).
- AC-002: every numbered requirement holds over the declared domain — verified by the oracle's 363
  sequences, 0 failures.
- AC-003: no file other than `dispatch.py` modified — verified by `git status --porcelain` and the
  unchanged hashes of `goal.md`/`requirements.md`.

## Collateral effects, defects, uncertainty, boundaries

- Collateral effects: none. `dispatch.py` uses only the standard-library `collections.deque`; no
  other module or shared state is touched.
- Decision boundaries: none requiring parent authority. The rotation policy is explicitly advice in
  the requirements, and the chosen construction meets the numbered points; no priority/weight/
  deadline concept was introduced.
- Boundary/unknown: behaviour for `arrivals == []` returns `[]`; the empty queue is outside the
  stated domain and no numbered point constrains it. Behaviour for more than three keys or more
  than five items is not acceptance evidence, only informational.
- Not independently reviewed by this attempt; a fresh reviewer follows.

## Remaining work

- Independent review (per contract `Independent review`).
