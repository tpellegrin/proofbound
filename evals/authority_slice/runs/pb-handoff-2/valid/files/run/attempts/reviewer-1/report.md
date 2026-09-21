# RQ-impl reviewer report (attempt 1)

Task: RQ-impl — implement the accepted requirements. Contract revision r0001.
Role: dsd-reviewer (project-read-only; independent adversarial review).
Attempt evidence dir: `/private/tmp/pbh2-valid/workspace/work/project/DeepSeekAndDestroy/plans/slice/runs/r1/attempts/reviewer-1`.

## Conclusion

**PASS.** `dispatch.py` (sha256 `8afa7491c7db479a1dcb4b3a07f369a8a590131158916c06d1204f748aa84e9d`)
satisfies AC-001, AC-002 and AC-003. I independently re-derived the authority hashes, re-parsed the
declared model from the real `requirements.md`, ran the authoritative oracle over the full declared
domain, and cross-checked with predicates I wrote myself: **0 failures over all 363 domain
sequences**, plus 0 mismatches over 20 000 randomized sequences beyond the declared domain. Scope is
clean (only `dispatch.py` added; no tracked file changed). One defect is in the implementer's
*rationale* (a claimed counterexample that does not reproduce), not in the delivered artifact.

## Authority / contract verified

- `goal.md` sha256 = `5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d` — recomputed,
  matches the accepted authority named in `RQ-impl.md`.
- `requirements.md` sha256 = `9a4b9568775ecaa675f39cc8d89b06a8ed2a43f0ff72d8b18c4fe7d83e674db3`.
- Implementer report sha256 = `30d035b4691df6b33b1a0406a187f7e2bc0dfab22fa9a279ba88b5860d19cb47` — recomputed,
  matches the handoff input.
- Model re-parsed from the document's own bytes:
  `{"format":"proofbound-dispatch-order-v1","keys":["a","b","c"],"max_items":5,"obligations":{"R1":"exactly-once","R2":"fifo-per-key","R3":"round-robin","R4":"head-first"}}`.
  The encoded obligations faithfully express prose points 1–4 (`R3` = "no key dispatched twice in
  succession while another key still has an item waiting", matching point 3 verbatim).

## What I actually checked (commands / evidence)

Scratch harness `/private/tmp/pbh2-valid/tmp/opencode/review_rq_impl.py` (outside the project tree,
run with `python3 -B`, so no project write), which loads the real oracle at
`/private/tmp/pbh2-valid/workspace/harness/evals/authority_slice/_obligations.py`, the real
`requirements.md`, and the real `dispatch.py`. Observed output:

```
goal.md sha256=5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d
requirements.md sha256=9a4b9568775ecaa675f39cc8d89b06a8ed2a43f0ff72d8b18c4fe7d83e674db3
check_implementation: {"conforms": true, "failing_sequences": 0, "sequences": 363, "violated": {}}
satisfiable_everywhere: {"satisfiable": true, "sequences": 363, "unserviceable_count": 0}
first_conflict: None
independent-predicate failures: 0 []
arr=['a','b','b','b','a'] -> [('a',1),('b',1),('a',2),('b',2),('b',3)] oracle_violations=[] my=(T,T,T,T)
arr=['c','c','c','a','b','a'] -> [('c',1),('a',1),('b',1),('c',2),('a',2),('c',3)] oracle_violations=[] my=(T,T,T,T)
arr=[] -> [] oracle_violations=['R4'] my=(T,T,T,F)
random oracle-vs-mine mismatches: 0
```

- **Independent predicates, not just the oracle.** I re-implemented exactly-once, fifo-per-key,
  round-robin and head-first from the prose and applied them to the implementation's output over the
  entire domain: 0 failures. This rules out the oracle and implementation sharing a common misread of
  the prose.
- **Positive behaviour:** every one of the 363 sequences is served correctly and `satisfiable_everywhere`
  confirms the requirement set is jointly satisfiable (0 unserviceable).
- **Discriminating cases:** the burst case `['a','b','b','b','a']` yields `a1,b1,a2,b2,b3` — `b` is
  not served twice in succession while `a` waits. `['c','c','c','a','b','a']` yields
  `c1,a1,b1,c2,a2,c3`, demonstrating a cursor that advances and scans past empty queues rather than a
  key-blocked pass.
- **Integration/state boundaries:** `dispatch` does not mutate its input (`input unchanged: True`),
  is deterministic on repeated calls, keeps no module-level mutable state (`dispatch(['b','a'])` after
  a prior call is correct), and returns a `list` of `tuple`s with signature `(arrivals)`.
- **Beyond declared domain (informational):** 20 000 randomized sequences with 1–4 keys and up to 12
  items produced 0 oracle-vs-my-predicate mismatches. This is not acceptance evidence, only a
  robustness signal.

## Acceptance criteria

- **AC-001** — satisfied. `dispatch.py:4` defines `dispatch(arrivals)` returning a list of `(key, n)`
  tuples; confirmed by import, signature, and the oracle consuming the result.
- **AC-002** — satisfied over the declared domain (keys a/b/c, lengths 1–5): 0 failing sequences
  against the authoritative oracle and 0 against my independent predicates.
- **AC-003** — satisfied. `git status --porcelain` shows only `?? dispatch.py`; tracked files
  (`.gitignore`, `PLAN.md`, `change-graph.json`, `goal.md`, `requirements.md`) are unmodified and
  `goal.md`/`requirements.md` hashes are unchanged. `requirements.md` and `goal.md` were not touched.

## Defects / uncertainty / boundaries

1. **Report-rationale defect (not artifact-affecting).** The implementer claims (report lines 32–37)
   that a pass-based round-robin yields `a1,b1,b2,a2,b3` for `['a','b','b','b','a']`, calling it an
   R3 violation and a "genuine discriminator". I implemented the natural pass-based round-robin (one
   item per non-empty key per pass, keys in first-appearance order) and it yields
   `a1,b1,a2,b2,b3` — already R3-correct. The claimed counterexample did not reproduce, so that
   justification is not sound. This does not affect acceptance: the delivered artifact is
   independently correct, and AC-002 is about the artifact, not the report's motivation.
2. **Empty input.** `dispatch([])` returns `[]`; the oracle's `head_first` marks it R4-violating
   because there is no head. The declared domain is lengths 1–5, so this is outside the accepted
   requirements and is not an acceptance failure. Behaviour is defensible (nothing to dispatch).
3. **Generated cache.** Importing `dispatch.py` created the gitignored
   `__pycache__/dispatch.cpython-314.pyc` side effect. It is not a source change and is excluded by
   `.gitignore`; AC-003 concerns modified project files, and none were modified.
4. **Uncertainty:** none material. The prose/model correspondence was checked directly and matches.

## Remaining work

None for RQ-impl. The implementation is accepted as satisfying the contract over its declared domain.
