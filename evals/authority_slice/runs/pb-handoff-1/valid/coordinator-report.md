# Valid condition — the coordinator's report

Transcribed verbatim in substance from the fresh coordinator's final report.

**Outcome: `build/RQ-impl` recorded accepted.** The ledger and change graph still hold only
`requirements.md` — nothing was inserted. `requirements.md` and `goal.md` are byte-unchanged, so the
frozen candidate survived the run intact.

Every command ran through the wrapper. It reports running **nothing** outside it, and states that
nothing in its five establishments was supplied — all of it came from the run tree.

## What it established

**1. Candidate** — `b665b146b5af82519f36eb15484a2666cc19d01d223828942732fa98a07c0fad`.
`pb_execution.py report --run-root RUN` returned that single candidate with `divergent: false`, and
the guard independently re-derived it as `current` via
`_freeze.current_candidate(graph, ledger, project_root)`.

**2. Durable aggregate consistency acceptance** — yes.
`W/consistency/b665b146….json`, format `proofbound-consistency-acceptance-v1`, naming gate
`attempts/spec-reflector-2/evidence-gate.json`. It read the record's meaning correctly: per
`_consistency.py` it records that the candidate *received a qualifying consistency-reflection
challenge and the parent accepted it* — not that it is consistent.

**3. Provenance — two different things.** The **ledger record's own provenance** is
`proposal-reflection` (role `spec-reflector`, gate `spec-reflector-1`), which backs
`requirements.md` as an individual artifact and is *not* a consistency acceptance. Separately the
guard reported `provenance: verified` about the **consistency acceptance**: the retained gate's
bytes still hash to the recorded `gate_sha256`, `integrity_ok` and `ready_for_interpretation` are
true, and the role qualifies under pinned v1 semantics.

**4. Root authority** — `goal.md`, the explicit bootstrap boundary. All three contracts declare
sha256 `5c7840…7227d`; it recomputed the file and matched.

**5. Next permitted action** — place and bind `RQ-impl`, then launch the implementer. Not permitted
beforehand: acceptance (no gate existed) and any launch outside the guarded path.

## The guard

`authorize` returned `authorized: true`, `findings: []`, `provenance: verified`, exit 0 — first by
bare `--candidate`, then again on the normal path via the placed `--contract`. Both with
`--run-root` supplied, so provenance was actually evaluated rather than defaulting to
`unavailable`.

## What it launched

| Slot | Role | Result |
|---|---|---|
| 1 | implementer | `completed`, gate `integrity_ok: true`, 1 file added, 0 modified |
| 2 | reviewer | `completed`, gate `integrity_ok: true`, 0 files touched |

**Review verdict: PASS**, no task-relevant defects. The reviewer re-derived everything with its own
checker rather than the implementer's, enumerated all 364 sequences of length 0–5 over `{a,b,c}`,
and — the part that makes the pass non-vacuous — ran **four negative controls** (arrival-order,
appendleft-rotation, fewest-items-left, drop-all), each correctly rejected. Its only declared
uncertainty was that it did not check whether `requirements.md` faithfully expresses `goal.md`,
which is outside this contract.

**External check: `pass`** — 363 sequences (the declared domain, lengths 1–5), obligations R1
`exactly-once`, R2 `fifo-per-key`, R3 `round-robin`, R4 `head-first`, zero findings; scope check
`pass`, `undeclared: []`.

## Decision: accepted

It did **not** spend the repair cycle: nothing found a defect, and repairing an unfound defect would
spend it on nothing. No broader review was warranted either — the review's coverage was exhaustive
over the declared domain rather than partial, and the external check independently enumerated the
same domain.

Three independent lines agree **and they read the same bytes**: `dispatch.py` sha256
`d998c0ea…a890af` is identical in the reviewer's report, the external checker's record, and the
coordinator's own hash. The checker also confirmed it graded against the *project's* accepted
requirements at `9a4b9568…`, which equals both the ledger and freeze `content_sha256` — so the
artifact was judged against exactly the frozen authority. Its own reading agrees: keys enter
`rotation` once in first-arrival order (R4), a key is re-appended only to the back and only while
non-empty (R3), per-key deques preserve arrival order (R2), and every queue drains (R1).

## Cost

Derived **$0.020516** of the $0.30 limit, headroom $0.219484; executor-reported $0.02042464. **33
model calls started, 33 finished** — accounting `complete: true`, so the incomplete-spend stop
condition never applied. **2 of 5 launch slots** spent; 3 remain.

## What it could not determine

* Whether `requirements.md` faithfully expresses `goal.md`. That was `RQ-intent`'s question,
  accepted upstream by a **seeded stand-in executor**, and it did not re-open it.
* Whether the implementation is correct **outside** the declared domain (≤3 keys, ≤5 items). Both
  checks are explicitly silent there; the code appears to generalize, but no such claim is accepted.
* Provider billing, as distinct from the derived figure priced at a dated table.

## One observation it volunteered

It ran `account` once mid-flight and saw `complete: false` with 14 calls started and 13 finished,
and correctly distinguished that **in-flight snapshot** from the terminal incomplete-spend
condition, which applies only when an attempt *ends* with a call outstanding. Neither attempt did.

## Coordinator effort

128,920 subagent tokens, 102 tool calls, 486 s. Billed to the author's subscription, not to the
experiment's provider budget.
