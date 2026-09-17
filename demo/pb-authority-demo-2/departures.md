# pb-authority-demo-2 — recorded departures

`protocol.md` says the run either follows it or stops, and that any departure is recorded as a
departure rather than absorbed. This file is that record. It is append-only, dated, and committed
before the next paid launch in every case.

---

## 2026-09-17 — D1: the frozen accounting rule contradicted the frozen deadline rule

**Found by executing it.** The first paid attempt, `spec-author-1`, reached its 900-second deadline
and was stopped. The lifecycle behaved correctly — SIGTERM to the process group, `stopped: true`, no
SIGKILL needed, report and scope frozen at terminal. But the stop left one of twelve model calls in
flight, so the session's usage totals do not include it.

Two clauses of the protocol then disagreed about what that means.

* The section on accounting scope defines a spend figure as complete only when, among other things,
  *"every terminal record is `completed`"* and *"calls started equal calls finished"*. Stop
  condition 1 refuses every further launch while the figure is incomplete. Under that reading a
  single deadline expiry ends the demonstration permanently and irreversibly.
* The section on launch limits says *"two deadline expiries on the same role slot with terminal
  evidence that the executor was reached is a stop condition"* — which is only meaningful if one
  expiry is survivable.

Both are frozen text. There is no reading that satisfies both, so the inconsistency has to be
resolved in one direction or the other, and resolving it by stopping would be as much a choice as
resolving it by continuing. Neither is "just following the protocol".

**Resolved in the direction that preserves the principle the rule exists for.** The principle, which
the b1 spend work established and which is not in question, is that unaccounted expenditure must
never be treated as zero when deciding whether another launch is affordable. What the rule got wrong
is conflating *unaccounted* with *unbounded*.

An interrupted attempt whose calls all finished leaves no gap at all — being stopped is not itself
an expenditure. What escapes the totals is specifically a call that started and never finished, and
the session database records every completed call's own token usage, so such a call has a defensible
ceiling: the dearest completed call in the same session. Accounting now charges that ceiling against
the aggregate limit, and admission spends against the **charged** figure rather than the derived
one.

This is stricter than the alternative, not laxer. Before this change a run could only ever be
stopped or carried on; it could not charge itself for work it knew it had incurred but could not
measure. The unbounded case is unchanged and still stops the run: if the per-call record cannot be
read, there is no bound, and `interrupted_call_bound` returns nothing rather than estimating.

Measured effect on this run: derived $0.010694, one unfinished call bounded at $0.002237, charged
$0.012931 against the $0.40 limit. Regressions in `tests/test_authority_demo2_accounting.py` cover
the bounded case, the unbounded case that still stops, and an interrupted attempt with no in-flight
call.

**Not changed:** the $0.40 limit, the $0.10 reserve, the 900-second deadline, the launch ceiling of
8, the repair policy, the handoff rules, or any other stop condition. The deadline in particular was
left alone deliberately — the attempt spent 600 of its 900 seconds inside a single hung shell
command that the worker wrote itself, and raising the deadline to accommodate that would be changing
frozen policy for convenience.

---

## 2026-09-17 — D2: the session lookup was asked from the wrong directory

**Not a departure from the protocol; a defect in the harness the protocol runs on, repaired
mid-run.** Recorded here because it changed repository code during a live demonstration.

`run_worker.lookup_session_id` ran `opencode session list` without a working directory. That command
scopes its answer to the directory it is asked from; asked from anywhere else it exits 0 and prints
nothing, which parses as *no sessions* rather than as an error. Every terminal record therefore lost
its session id silently, and usage could not be attributed to the launch that incurred it.

This is not new and was not caused by the timeout. Every terminal record in `pb-authority-demo-1`,
including the two attempts that completed cleanly, carries `session_id: null` with the identical
parse error. That demonstration's reported spend was derived from the database as a whole, which
happened to contain only its own sessions — so the figure was most likely right, but its claim of
completeness rested on an attribution check that could not have been performed.

Repaired in two places. `run_worker` now asks from the project root, with a regression in
`tests/test_worker_session_attribution.py` that pins the silent-empty-answer behaviour. And spend
accounting no longer depends on the id being present: it resolves the session by the exact title the
launcher used, which is what `run_worker` matches on anyway and which survives in the terminal
record. Recovery is not invention — a title matching no session still yields no attribution, and
that case is tested.

---

## 2026-09-17 — D3: the refused attempt's output was discarded before relaunch

`spec-author-1`'s evidence gate refused it: `integrity_ok: false`, `"worker lifecycle not
completed/0: status='timeout' exit=-15"`. The attempt had nonetheless written `spec.md` into the
project before it was stopped.

An artifact from an attempt whose gate refused cannot be accepted, and leaving it in place would
have made the relaunched attempt an edit of refused work rather than a production of its own. The
project tree was therefore reset to the scope baseline recorded at launch before `spec-author-2`
started. The refused attempt's own evidence directory is untouched and remains part of the record.

Permitted by the launch-limits section: one deadline expiry is survivable, the relaunch counts
against the ceiling of 8, and a second expiry on this role slot stops the run.
