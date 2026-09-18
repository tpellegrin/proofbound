# DSD Reviewer report — RQ-impl (attempt reviewer-1)

Status: COMPLETE. Conclusion: **PASS** — the implementation satisfies AC-001, AC-002 and
AC-003 over the declared domain, with no task-relevant defects found.

This report is self-contained. It records the authority I read, the artifact I reviewed, the
independent checks I actually ran, the decisive evidence, and the residual uncertainty.

## 1. Task identity and authority

- Task: RQ-impl — implement the accepted requirements (`dispatch(arrivals)` in `dispatch.py`).
- Contract: `DeepSeekAndDestroy/plans/slice/runs/r1/contracts/RQ-impl.md` (revision r0001).
- Accepted authority named by the contract: `goal.md`, sha256
  `5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d`.
  I recomputed `shasum -a 256 goal.md` and it matches exactly.
- Requirements authority: `requirements.md` (the numbered points R1–R4).
- Allowed source changes (hard boundary): `dispatch.py` only.
- Proofbound candidate (contract): `b665b146b5af82519f36eb15484a2666cc19d01d223828942732fa98a07c0fad`.
- Input under review: implementer-1 report, sha256
  `766ac08a004c6438f7d566bb611e511906f0afe3df1d1f06e9f26a208a30da2b` (matches the supplied hash).

I treated the implementer's report and its verifier as claims/evidence pointers, not authority,
and re-derived every result below with my own code.

## 2. Artifact reviewed

`/private/tmp/pbh1-valid/workspace/work/project/dispatch.py`
sha256 `d998c0eaff9fbc2be8a601d809ae43102afebbe2fc60f4f92a2f67c527a890af` (matches the
implementer's stated hash and the reviewer scope baseline captured at launch).

Real source (verbatim):

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

Mechanism: one FIFO `deque` per key in first-arrival order; a rotation `deque` of keys that still
have work; pop one item per turn and re-append a key only after every other key still in rotation
has had a turn.

## 3. Requirements under test

From `requirements.md` (the numbered points are the whole requirement; the round-robin note is
advisory):

- R1 exactly-once: every enqueued item dispatched exactly once.
- R2 fifo-per-key: a key's items leave in arrival order.
- R3 fairness: a key is never dispatched twice in succession while an item of a different key is
  still waiting.
- R4 head-first: the first item dispatched is the first item that arrived.
- Domain: up to three tenant keys, up to five queued items.
- Not-change: items are dispatched only after enqueue; keys are opaque, no key privileged.

## 4. Independent verification actually performed

All commands run from the project root on 2026-09-18. I did not modify project state.

### 4.1 Exhaustive domain check (my own checker, written from scratch)

- Script (mine): `DeepSeekAndDestroy/plans/slice/runs/r1/attempts/reviewer-1/verify_rq_impl_reviewer.py`,
  sha256 `e277a542d030905dc3ccfd2ee295ded3a7073cb106b49d525464846312d5ed57`.
- It does **not** import or reuse the implementer's verifier.
- It enumerates the entire declared domain: all sequences over keys `{a,b,c}` of length 0..5
  (3^0+…+3^5 = 364 sequences).
- Checker formulation is temporal and independent of the implementation: it rebuilds each key's
  pending item list from `arrivals`, then walks the returned order, rejecting any item that is not
  the key's next undelivered item (R1+R2), and rejecting a repeat of the previous key at the moment
  the repeat is dispatched whenever any other key still has undelivered items (R3). R4 is checked as
  `order[0] == (arrivals[0], 1)` (and `[]` for empty input).
- Result: `[dispatch] checked 364, failures 0`.
- Output (durable): `.../reviewer-1/verify-output.txt`,
  sha256 `23fcbab2152385efe50296ce32731943e2a1061760041fa763d568dee934356e`.

### 4.2 Checker non-vacuity (negative controls, independent of the implementer's)

My checker must reject plausible-but-wrong implementations, or its pass is meaningless:

- arrival-order (pre-change behaviour) → rejected on 192/364 sequences (R3).
- appendleft-round-robin (re-queues a key at the front, starving others) → rejected on 306/364 (R3).
- fewest-items-left (the alternate policy the advisory note calls acceptable) → rejected on 276/364,
  because it reorders the head (R4) and/or serves a key twice.
- drop-all → rejected on 363/364 (R1/length; the empty-input case is correctly `[]`).
- Summary: `RESULT: dispatch_ok=True negative_controls_detected=True`, exit 0.

The appendleft variant is a same-root-cause family member I added; it confirms the R3 check
distinguishes a correct rotation from a starve-the-others rotation.

### 4.3 Opaque keys, purity, shape

Script `.../reviewer-1/extra_checks.py`, sha256
`391307a1bd551706f3229ba57dacfe1483b8ad9b418697564a938039be8cd04d`:

- Non-string opaque keys behave correctly: `[1,1,2] -> [(1,1),(2,1),(1,2)]`;
  `[(1,2),(1,2),(3,)] -> [((1,2),1),((3,),1),((1,2),2)]`; `[None,None,"x"] -> [(None,1),("x",1),(None,2)]`.
- Empty input → `[]`; single input → `[(key,1)]`.
- Input list is not mutated; return is a `list` of 2-tuples.
- Out-of-domain sanity (50 items, 10 keys) returns 50 items without error — not claimed as
  acceptance, only that nothing crashes.

### 4.4 Scope check (AC-003)

- `git status --porcelain` → only `?? dispatch.py` (untracked new file).
- `git diff --name-only` → empty (no tracked file modified).
- Tracked files: `.gitignore`, `PLAN.md`, `change-graph.json`, `goal.md`, `requirements.md`.
- `requirements.md` sha256 `9a4b9568775ecaa675f39cc8d89b06a8ed2a43f0ff72d8b18c4fe7d83e674db3` equals
  `git show HEAD:requirements.md` (unchanged). `goal.md` equals the contract hash (unchanged).
- Only other new path is `__pycache__/dispatch.cpython-314.pyc`, a gitignored interpreter artifact
  from importing the module during verification; it is not a source change and the scope inventory
  excludes it. I did not treat it as a project modification.

### 4.5 Boundary cases traced by hand

- `['a','a','b'] -> [('a',1),('b',1),('a',2)]` — burst cannot block b, and the head is a1.
- `['a','b','a','b','a','c'] -> a1,b1,c1,a2,b2,a3` — a late-appearing key gets its turn immediately;
  no key repeats while another waits.
- `['a','a','a','b'] -> a1,b1,a2,a3` — consecutive a's occur only after b has no waiting item,
  which R3 permits.

## 5. Acceptance-criteria findings

- **AC-001 — MET.** `dispatch.py` defines `dispatch(arrivals)` returning a list of `(key, n)` items;
  shape verified over all 364 sequences and over opaque non-string keys.
- **AC-002 — MET.** Every numbered requirement holds over the declared domain (<=3 keys, <=5 items):
  exhaustive 364/364 pass, with non-vacuous negative controls. R1 exactly-once, R2 fifo-per-key,
  R3 no repeat-while-others-wait, R4 head-first all confirmed. The implementation is in fact a
  general round-robin and also handles inputs outside the declared domain, but no unbounded-domain
  claim is made or relied upon.
- **AC-003 — MET.** Only `dispatch.py` was added; no other file modified; `requirements.md` and
  `goal.md` unchanged.

## 6. Defects, uncertainty, decision boundaries

- No task-relevant defects found.
- No unrelated pre-existing defects observed in scope (the project contains only `goal.md`,
  `requirements.md`, `PLAN.md`, `change-graph.json`, `.gitignore`).
- Uncertainty: I did not attempt to verify that `requirements.md` faithfully expresses `goal.md`;
  that is the requirements-review task's responsibility, and `requirements.md` is accepted
  authority for this contract. Key equality relies on Python hash/equality semantics; for the
  declared opaque keys and the machine model's `["a","b","c"]` this is not a defect, and the
  implementation assumes no key-specific ordering or privilege.
- No `DECISION_REQUIRED`: nothing in this review needed authority I do not hold.

## 7. What remains

Nothing for this task. Fresh independent review was required before acceptance and this report is
that review; it does not self-approve any parent task.

## 8. Evidence index (durable)

- Reviewed source: `dispatch.py` @ `d998c0eaff9fbc2be8a601d809ae43102afebbe2fc60f4f92a2f67c527a890af`.
- My exhaustive verifier: `.../reviewer-1/verify_rq_impl_reviewer.py` @
  `e277a542d030905dc3ccfd2ee295ded3a7073cb106b49d525464846312d5ed57`.
- My verifier output: `.../reviewer-1/verify-output.txt` @
  `23fcbab2152385efe50296ce32731943e2a1061760041fa763d568dee934356e`.
- My extra checks: `.../reviewer-1/extra_checks.py` @
  `391307a1bd551706f3229ba57dacfe1483b8ad9b418697564a938039be8cd04d`.
- Implementer evidence pointer: `.../implementer-1/report.md` @
  `766ac08a004c6438f7d566bb611e511906f0afe3df1d1f06e9f26a208a30da2b`.
