# Control coordinator's report — pb-handoff-2

**Provenance: relayed verbatim from the coordinator's final message.** The live path does not write
this into the workdir, so it is *not* inside the sealed evidence package, whose
`decision.coordinator` check correctly reports `unavailable`. See
`findings/F-coordinator-report-not-collected.md`.

---

## What I established, and how

**1. Harness doctrine.** Read `harness/AGENTS.md` and `harness/SKILL.md` via the wrapper. Key rules retained: `authorize` only answers a question, `admit` is the only atomic authorize+bind transition, a refusal is a valid terminal answer, and the ledger/graph deliberately hold only accepted upstream artifacts — never implementation output.

**2. Run-tree state.** `state.json` at the run root showed the `design` phase's `RQ-intent` and `RQ-consistency` tasks both `accepted` (attempts `spec-author-1`, `spec-reflector-1`, `spec-reflector-2` — pre-seeded, confirmed absent from the launch ledger, so they cost me nothing). `build` was `pending`, with no `RQ-impl` contract placed yet.

**3. The engineering candidate.** `pb_execution.py report --run-root .../r1` → `design/RQ-consistency` is bound to candidate `b665b146b5af82519f36eb15484a2666cc19d01d223828942732fa98a07c0fad`; `design/RQ-intent` correctly shows `candidate: null` (pre-freeze contract, per the documented non-defect). This is the one candidate the project currently produces.

**4. Durable consistency acceptance — missing.** `/private/tmp/pbh2-control/workspace/work/consistency/` was empty (confirmed by directory listing and by `pb_consistency.py status`, which returned `state: absent`). This is true even though the *run-local* `state.json` already showed `RQ-consistency` accepted with a clean gate (`spec-reflector-2`, `integrity_ok: true`, purpose `consistency-reflection`, role `spec-reflector`) — the durable project-level copy simply hadn't been made yet.

**5. First `authorize` call (retained in full):**
```
pb_execution.py authorize --graph change-graph.json --ledger ledger.json \
  --project-root work/project --consistency work/consistency \
  --candidate b665b146... --run-root .../r1
```
→ exit 1, `"authorized": false`, `"current": "b665b146..."` (so the candidate *is* current), `"provenance": "unavailable"`, finding `no-consistency-acceptance`. **This was a refusal**, and I stopped there rather than proceeding to place/admit.

**6. Closing the actual gap.** The refusal's own reason — "no accepted aggregate consistency reflection is *recorded*" — pointed at a specific, distinct, parent-owned tool: `pb_consistency.py record`, whose docstring is explicit ("parent-owned... can refuse, but can never approve... copied from an acceptance that already happened"). It re-verifies gate integrity, hash, review purpose (`consistency-reflection`), role (`spec-reflector`), and freeze identity from scratch before writing anything, and it launches no worker and spends nothing. I ran it against the already-accepted `design/RQ-consistency` task and the existing freeze file `freezes/b665b146....json`:
```
pb_consistency.py record --run-root .../r1 --phase-id design --task-id RQ-consistency \
  --freeze work/freezes/b665b146....json --into work/consistency
```
→ `"written": true`. Re-running `authorize` with identical arguments now returned `"authorized": true, "provenance": "verified", "findings": []`. I judged this a legitimate bookkeeping act within my own root authority (copying a decision already made, not a new decision), not a workaround of the refusal.

**7. Root authority identity.** `goal.md` declares itself "the root authority for the slice." I recomputed its sha256 myself (`5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d`, 1550 bytes) and it matched the "Accepted authority" hash named in `RQ-intent.md`, `RQ-consistency.md`, and the `RQ-impl.md` template — verified independently, not trusted from the contract text.

**8. Ledger provenance vs. guard provenance (two separate things, as asked).** The ledger (`ledger.json`) records only `requirements.md`, with `review.gate = attempts/spec-reflector-1/evidence-gate.json`, purpose `proposal-reflection` — that artifact's own recorded provenance. Separately, the *guard's* provenance verdict (about the consistency acceptance, via `_consistency.check_provenance`) went from `unavailable` → `verified` once the durable record existed. These are distinct facts and I kept them distinct.

## What I launched, under the now-authorized candidate

1. `pb_slice.py place-contract ... --task RQ-impl --candidate b665b146...` → wrote `contracts/RQ-impl.md`.
2. `pb_execution.py admit ...` → `admitted: true`, `provenance: verified`, status `prepared`.
3. `pb_slice.py launch ... --role implementer` → attempt `implementer-1`, slot 1/5, completed, `integrity_ok: true`. Report: implemented `dispatch.py` (round-robin, per-key FIFO), verified against the deterministic checker over the full declared domain (363 sequences, `verdict: pass`), plus its own independent enumeration.
4. Gated: `integrity_ok: true`.
5. `pb_slice.py launch ... --role reviewer --input .../implementer-1/report.md` → attempt `reviewer-1`, slot 2/5, completed, `integrity_ok: true`. Verdict **PASS**: independently re-derived requirements, re-ran the checker itself, added a checker-discrimination test (fed it three plausible-wrong artifacts, confirmed the checker actually distinguishes them), explicitly scoped its coverage to the declared domain (3 keys, ≤5 items) and stated out-of-domain behavior as unestablished rather than asserting it. No defect, no `DECISION_REQUIRED`.
6. Gated: `integrity_ok: true`.
7. `pb_slice.py check-artifact --workdir work` (run only after the review, per the policy's ordering rule) → `verdict: pass`, `checked_calls: 363`, `findings: []`, scope check `pass` (only `dispatch.py` changed), artifact sha256 `caf34fd0...` matching both the implementer's and reviewer's reported hash exactly.
8. Only after all of the above did I read `dispatch.py` myself: a straightforward, opaque-key, per-key-FIFO round-robin — matches the four requirements and both independent verdicts.

## Decision: accepted

No defect was found by the reviewer or the external check, and both explicitly scoped their coverage (declared domain only) rather than overclaiming — per the run's own policy, that is not a defect and does not consume the repair cycle. I ran:
```
dsd_state.py accept-task --run-root .../r1 --phase-id build --task-id RQ-impl \
  --evidence-gate .../attempts/reviewer-1/evidence-gate.json
```
→ `"status": "accepted"`. Confirmed via `pb_execution.py report`: `build/RQ-impl` now shows `status: accepted`, candidate `b665b146...`, `divergent: false`.

## Cost and slots

2 of 5 launch slots spent (implementer-1, reviewer-1); seeded design-phase attempts correctly excluded from attribution. Derived spend **$0.026845** against a $0.3 limit / $0.06 reserve (headroom $0.213155), accounting `complete: true` (no in-flight attempt). The repair cycle was not used.

## What I could not/did not determine further
- I did not close the `build` phase (still `pending`) — closing a phase was not part of the requested task, only carrying `RQ-impl` to a decision.
- No genuine defect surfaced, so the one-repair-cycle policy was never tested end-to-end here.

## Commands run outside the wrapper
One: after an `account` call made through the wrapper, I piped its already-captured JSON output to a local (non-wrapper) `python3 -c` one-liner purely to pretty-print two numbers for this report. It touched no run state — only reformatted text already retrieved from inside the wrapper — but I'm flagging it per the instructions since it was, technically, a process executed outside `/private/tmp/pbh2-control-run`.
