# Live qualification — 2026-09-24 (UTC), `deepseek-v4-flash-high` revision `2026-09-23`

**Blocked.** One of four trials completed, and the tool loop was shown. The contradictory
requirements challenge is incomplete: its fresh reviewer's executor failed before making any model
request. The remaining two trials were not launched, because the failure is in the executor
start-up that every trial shares. The first-use gate is not met, and nothing was spent on first use.
Three launches were made, for **$0.016342** in derived cost. That figure is not provider billing,
which was not observed.

## What ran, and under what

| | |
|---|---|
| Harness | `c4b83cc`, clean, equal to `origin/main` |
| Proposal | `evals/qualification/proposals/2026-09-23-deepseek-v4-flash-high/`, digest `5c3b2c55…ca93ca` |
| Authorized plan | `evals/qualification/plans/2026-09-23-deepseek-v4-flash-high/`, digest `8370c2d4…1e15a`, made by `pb_qualify.py authorize` with the owner's statement; its frozen fields are identical to the proposal's |
| Instrument | suite `0dfed363…`, control plane `e68a5ba2…`, Python 3.10.14 (`/opt/homebrew/bin/python3.10`), executor OpenCode 1.18.29 `2f24593f…d669` |
| Worker settings | digest `7aa8ef0d05e9ea23…`, the same in all four runs |
| Per trial | the proposal's allocation, a reserve of one $0.05 allowance, 900 s attempt deadline, containment at 150 requests / 5 incomplete responses / derived spend |
| Frozen pilot | CSV `protocol-v2.md` and `preparation-identities.json` unchanged and unrun |

`prepare-live` passed readiness with no provider request. It then started and authorized each run
through `authorize-spending`, and checked that each run froze the plan's interpreter, executor
bytes and settings. The runs were then driven with `pb_workflow.py status`/`continue` only. Every
coordinator command is logged per trial.

## Per trial

| Trial | Launches / ceiling | Derived / limit | Status | Dimension |
|---|---|---|---|---|
| tool-loop / marker | 1 / 2 | $0.006127 / $0.10 | completed | **met**: causal continuation, marker present, gate integrity OK |
| requirements-challenge / contradictory | 2 / 3 | $0.010215 / $0.15 | incomplete | not measured: no review exists |
| requirements-challenge / coherent | 0 / 3 | $0 / $0.15 | not run | not measured |
| dispatch-implementation / coherent | 0 / 11 | $0 / $0.55 | not run | not measured |
| **Qualification** | **3 / 19** | **$0.016342 / $0.95** | | |
| First use | 0 / 11 | $0 / $0.55 | not started | gate not met |
| **Combined** | **3 / 30** | **$0.016342 / $1.50** | | |

All calls were in the off-peak window. Usage was complete, with no zero-token calls, and priced at
`deepseek-2026-09-23` as `deepseek-flash`. The executor's own cost field read $0.00472907 and
$0.0085335. Neither that field nor the derived figure is billing. Unused allowances stay with their
trials and do not renew. Trial 2's third slot is its pre-executor allowance, and the failure below
reached the executor, so that slot does not cover a relaunch.

**Tool loop.** Thirteen model calls ran in one session. Twelve of them ended with `tool-calls` and
were followed by a later call; 30 tools completed and none failed. The marker line is in
`specs/QUAL/requirements.md`. Input was 13,373 tokens, output 5,897 (2,363 of them reasoning), and
194,304 were read from cache. The case stops after the author's gated attempt, so no reviewer was
launched.

**Contradictory challenge.** The spec-author kept the owner's requirements byte-for-byte, and itself
named the R2/R3 conflict with witness `["a","a","b"]`. A reviewer launched after it would therefore
have seen the defect already stated, so this document tests less independence than intended. It
ran 16 calls: input 29,767, output 7,455 (3,881 reasoning), cache 425,728. The fresh
spec-reflector's executor exited 1 after 1.005 s, as follows:

```
{"name": "UnknownError", "data": {"message": "Unexpected server error. Check server logs for details.", "ref": "err_114f4b40"}}
```

Its session holds one user message and no assistant message, so no model request was made. The
gate recorded `worker lifecycle not completed/0: status='process-error' exit=1`, and the run is
`blocked` with no permitted next action. `grade` reports the trial `incomplete` because the stopping
point, the coordinator's adjudication, was never reached. `inspect` finds both retained trials
unaltered, and their grades recompute.

## The blocker: the executor's start-up depends on an undeclared npm download

Retained evidence establishes these facts:

- **Every DeepSeek-route launch downloads the executor's plugin package.** The pinned executor
  installs `@opencode-ai/plugin` 1.18.29 into the run's staged `~/.config/opencode`. In trial 1 it
  resolved 32 packages from `registry.npmjs.org`, between 00:33:41 and 00:33:52. The worker
  profile does not declare this download, and Proofbound does not pin or observe it beyond the
  direct version. The route's unrestricted worker network permits it.
- **In trial 2 the install never completed.** The staged configuration directory has no
  `package.json` or `node_modules`. The lock that guards the install is
  `sha1("npm-install:<staged home>/.config/opencode")`, matched against the lock directory's name.
  The reflector (pid 2900) acquired that lock at 00:37:03.536 and died holding it.
- **A lock-breaking step began after the author's executor had exited, and never finished.** A
  `.lock.breaker` directory was created at 00:36:25.745. That is 0.61 s after the author's main
  process exited, at 00:36:25.134, and before its attempt was sealed. The executor creates this
  directory only while breaking a lock it judges stale, and removes it in a `finally` block. The
  host's post-exit ownership sweep for that launch found nothing running. **Which process wrote it
  is not established.**
- **The error's details were not retained.** The executor's file log lost its last ~6.3 s for the
  author and everything for the reflector. The server log that `err_114f4b40` refers to does not
  exist.

**Cause: not established.** An offline reproduction ran three runs, each with two real-executor
launches (author then reflector), on a local profile against a scripted loopback endpoint. All six
launches completed, and no breaker was left. So a second launch in one run does not always fail.
The reproduction says nothing about the DeepSeek route's network path. The sanitized record, with
timestamps, lock metadata (token omitted) and the trial-1 comparison, is retained locally with the
raw evidence as `blocker-executor-startup.json`.

**Decision (coordinator).** The owner's rules were: *"A material failure affecting the shared
execution path stops subsequent trials too"* and *"Use only the predeclared repair/relaunch
allowances. Do not reroll failures."* The failure is in the executor start-up that every trial runs.
Its cause is unresolved, and trials 3 and 4 launch the same executor into the same kind of home.
The failure was judged material, and nothing further was launched. The prepared runs for trials 3
and 4 are untouched. No lower-level helper was used to relaunch.

## Identities

| | Requested | Reported | Observed |
|---|---|---|---|
| Coordinator | `claude-code/opus` | "Claude Opus 5.5 (`claude-opus-5-5`)", as the host's system prompt states it; a claim | none |
| Worker | `deepseek/deepseek-v4-flash`, variant `high` | executor records `deepseek` / `deepseek-v4-flash` / `high`, one model and variant throughout | the requested id only |

The provider documents that the name is "temporarily routed to V4.1 Flash" (statement of
2026-09-23). The executor keeps no response `model` field, and no string identifies weights. **No
served-model identity is claimed.**

## Coordinator interactions, repairs, interventions

- **Coordinator.** Tool loop: one `status` and three `continue`. Contradictory challenge: three
  `status` and five `continue`, with no `decide`. The stop decision is recorded in trials 2, 3
  and 4.
- **Repairs.** None.
- **Human interventions.** The owner's authorization, and nothing after it.
- **Delivery verification.** Not run, because no first use was made.

## First-use gate

Condition 1 holds. Condition 2 does not: there is no review, so there is no finding. Conditions 3
and 4 were not measured. Condition 5 does not hold: identities and accounting reconcile, but an
infrastructure defect is unresolved. The first-use allocation is unspent, and no new paid
experiment was started.

## What this does not establish

- That the configuration can challenge requirements or implement a dispatch. Those dimensions were
  not measured.
- What caused the start-up failure, or how often it happens.
- That containment bounds billing.
- Any reliability, from one tool-loop observation.

The raw run trees stay local and uncommitted, under
`~/proofbound-evidence/qualification-2026-09-24-deepseek-v4-flash-high/`. The graded summary is
`evals/results/qualification-live-2026-09-24-deepseek-v4-flash-high.json`. Each run's staged
credential copy (mode `0600`) remains under `/private/tmp/pb-workflow-*`, alongside the staged home
this record cites.

## Addition, later on 2026-09-24: two corrections

The text above is unchanged. [executor-startup-2026-09-24.md](executor-startup-2026-09-24.md)
records both corrections, with their evidence.

- **The cause.** The reviewer's failure is reproduced from this run's own retained state. The
  author's attempt cached the live model catalogue in the shared home. That catalogue lists
  `deepseek-v4-flash` as `deprecated`, and the pinned executor refuses such a model before any
  request. The npm install and lock activity above were correlated with the failure, not its cause.
- **The limitation of the contradictory case.** The suite's findings-format example was this
  case's defect and witness, and it was shown to the author and would have been shown to the
  reviewer. The author's proposal repeated it. So this trial could not have shown unassisted
  discovery, and a review would have measured at most verification of a finding it had been shown.
