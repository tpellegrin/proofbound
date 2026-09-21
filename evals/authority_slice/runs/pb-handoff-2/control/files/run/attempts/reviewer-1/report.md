# RQ-impl independent review report (reviewer attempt 1)

Role: DSD reviewer (project-read-only). Task: `RQ-impl`, contract revision `r0001`.

## Conclusion

**PASS.** The delivered `dispatch.py` satisfies AC-001, AC-002 and AC-003 over the declared
domain. I reproduced the implementer's decisive evidence and added independent enumeration and a
checker-discrimination test; I found no material defect. No `DECISION_REQUIRED`.

## Inputs verified (exact paths + hashes)

- `goal.md` sha256 `5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d` — matches
  the accepted authority named in the contract. (Recomputed with `shasum -a 256`.)
- Implementer report
  `.../attempts/implementer-1/report.md` sha256
  `f724e763a81ab059874196e0df3dba93c5e225a6d4497d5c0090411a4c4340e5` — matches the handoff.
- Delivered artifact `dispatch.py` sha256
  `caf34fd02cae4e12ed6b102155c1a6e844383c0d9ee3816d69940efa1f9c3716`, 1368 bytes — matches the
  hash the implementer reported.
- `requirements.md` sha256 `9a4b9568775ecaa675f39cc8d89b06a8ed2a43f0ff72d8b18c4fe7d83e674db3`, and it
  is byte-identical to the checker case copy at
  `harness/evals/authority_slice/cases/coherent-requirements/requirements.md` (same hash), and
  identical to `git show HEAD:requirements.md`. So the model the checker applies is the accepted
  requirements document, not a different one.

I treated the implementer report as claims, and re-derived every conclusion below myself.

## What the artifact is

`dispatch.py` defines `dispatch(arrivals)` (dispatch.py:35). It pairs each arrival with its 1-based
index within its key (`_enumerated`), builds per-key FIFO queues with keys in first-appearance
order (`_queues`), then cycles the keys, popping one item per key per pass
(dispatch.py:39-42). Keys are opaque: no branch inspects a key's value. The input sequence is not
mutated.

## Verification actually performed

### 1. Independent full-domain enumeration (my own predicates, no oracle import)
I loaded the delivered file by resolved path and applied my own re-implementations of the four
prose requirements (R1 exactly-once, R2 FIFO-per-key, R3 no double-serve while another key waits,
R4 first-dispatched = first-arrived) plus AC-001 shape checks, over every sequence over keys
`{a,b,c}` of length 1..5 — the declared domain. Script:
`/private/tmp/pbh2-control/tmp/opencode/reviewer_indep.py`.

Result:
```
sequences: 363
nonlist: [] shapefail: []
violations: {}
[a,a,b] -> [('a', 1), ('b', 1), ('a', 2)]
empty -> [] list
```
Every returned object is a `list`; every element is a 2-tuple `(str, int)`; zero violations of any
prose requirement. The discriminating burst case `[a,a,b]` interleaves (`a1,b1,a2`) rather than
draining the burst, which is the behaviour the change exists for. Empty input returns `[]` (outside
the checker's length>=1 domain; consistent with the prose, where head-first is vacuous).

### 2. The deterministic oracle (reproduced, not trusted)
```
python3 .../harness/evals/authority_slice/_checker.py --artifact .../project/dispatch.py
```
Reproduced the implementer's result exactly: `"verdict": "pass"`, `"checked_calls": 363`,
`"findings": []`, domain keys `["a","b","c"]`, `max_items` 5, exit 0. The checker loads the
artifact by resolved path in a subprocess, records its sha256, checks AC-001 on the actual returned
object (outer container must be a `list`) and AC-002 via the obligations oracle.

### 3. Is the pass meaningful? Checker-discrimination test
A pass from a lenient checker proves nothing, so I fed it three plausible-but-wrong artifacts:
- strict global-FIFO order (no rotation): `fail`, obligation AC-002 broken on 192/363.
- burst-completion (drain each key before the next): `fail`, obligation AC-002 broken on 306/363.
- correct order but returning a `tuple`: `fail`, AC-001 `return-type` on 363/363 calls.

So the checker genuinely distinguishes the claimed mechanism, and the candidate's evidence is not a
shortcut. This also directly rules out the two most plausible wrong implementations (no fairness,
and per-key burst draining).

### 4. AC-003 scope
`git status --porcelain` in the project root reports exactly `?? dispatch.py`. `git diff --stat
HEAD` is empty (no tracked file changed); tracked files are `.gitignore, PLAN.md,
change-graph.json, goal.md, requirements.md`. `dispatch.py` is the only change and is the sole
entry in the contract's `Allowed source changes`. The reviewer scope baseline
(`scope-baseline.json`) also pins `dispatch.py` to the same sha256.

## Defects / uncertainty

- **No material defect found.** The implementation meets every numbered requirement over the
  declared domain, and the evidence is exhaustive there (finite domain, all 363 sequences).
- **Out-of-domain behaviour is not established and not claimed.** The report correctly declines to
  assert properties for >3 keys, >5 items, non-string keys, or non-list inputs; the requirements
  make no claim there either. (The construction happens to extend naturally, but that is not part
  of the verdict.)
- **Minor, non-defect observations:**
  - The checker's domain is lengths 1..5 (363 sequences), so the empty sequence is excluded even
    though "up to five items" could include zero. This does not affect the verdict: `dispatch([])`
    returns `[]`, and all obligations are vacuous/undefined for empty.
  - A `__pycache__/dispatch.cpython-314.pyc` exists in the project root at review time, although
    the report says it was removed. Its mtime (15:45:46) coincides with verification imports
    (including my own independent run), so it is at least as likely to be my artifact as the
    implementer's. It is git-ignored and explicitly excluded from the scope checker's manifest, so
    it has no bearing on AC-003 either way.
- No unrelated pre-existing defect surfaced in the reviewed scope.

## Remaining

Nothing known to remain for this review. Implementation and its evidence are accepted.
