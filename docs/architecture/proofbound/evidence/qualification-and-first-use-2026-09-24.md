# Qualification continuation and first use — 2026-09-24

**Qualification completed, and first-use delivery verified.** All three continuation trials met
their dimensions, so the first-use gate was met. The first-use run went from the ordinary goal to a
sealed, accepted delivery. That delivery applied to a fresh checkout of its baseline and passed both
the project checks and the unchanged public outcome check.

The planned handoff was exercised by genuinely fresh coordinator sessions. The first of them exited
with its launch still running, which is recorded below as a finding.

In total this milestone made 14 launches, for **$0.132969** derived. Provider billing was not
observed.

## Before execution

- **Checkout:** `3b0d133`, equal to `origin/main`. Since the freeze at `91a472e` only the
  proposal's `plan.json` and `proposal.md` and one evidence document had changed; no instrument code.
- **Proposal digest:** `d591a1485661dff3c48c5b897dd5e766cff11ea3a6afc4ced71622dd0853ee97`,
  verified against its bytes.
- **Instrument:** no problems against the frozen suite (`390c2c72…`), control plane (`371d962f…`),
  Python 3.10.14 or executor (`2f24593f…d669`).
- **Settings:** `6af2663d…`, revision `2026-09-24`, carrying the start-up policy, and resolving
  identically. `/opt/homebrew/bin/python3.10` is the planned interpreter.
- **Authorization:** `pb_qualify.py authorize` produced plan `8d69e767…`, with the owner's
  statement verbatim. Only the authorization fields changed.
- **Supersession of the earlier allocations.**
  - The four staged credential copies of the earlier runs were removed, as authorized; their homes
    are kept.
  - A `superseded.json` record sits beside that evidence.
  - The earlier plan is refused, because its instrument no longer matches.
  - No front-door command can zero a frozen policy, so the record states it instead.
- **Prepared runs:** `prepare-live` froze the plan's policy, settings, boundary rules and start-up
  staging in every run, and the launcher's start-up check found nothing to refuse.

## Qualification: three trials

| Trial | Launches / ceiling | Derived / limit | Graded outcome |
|---|---|---|---|
| requirements-challenge / contradictory | 2 / 3 | $0.012300 / $0.15 | detected and substantiated (`R2`, `R3`, witness `[a, a, b]`); correct stop |
| requirements-challenge / coherent | 2 / 3 | $0.016623 / $0.15 | clean; correct acceptance |
| dispatch-implementation / coherent | 5 / 11 | $0.043699 / $0.55 | first attempt passes the unchanged checker; accepted and sealed; no repair; review has no findings; reference corpus not observed in tool activity |
| **Total** | **9** | **$0.072622** | 3 of 3 completed, gradeable and met |

- **Graded under** plan `8d69e767…`, and `inspect` finds every retained grade recomputing.
- **Execution.** All attempts completed, and every ledger slot was classified. Every attempt's
  `executor-state.json` shows no lock, no cached catalogue, and nothing running afterwards.
- **Accounting.** Usage was complete, with no zero-token calls, and all calls were off-peak.

**Exposure.** In the contradictory case, the author stated the conflict and the witness. The goal
no longer shows the answer, so the author found it on its own. The reviewer confirmed it by its own
exhaustive enumeration. The grade records `verification: a witness this review gave was in what it
was shown`. This satisfies the operational gate and does **not** establish independent discovery.

**Observation outside the graded cells.** In the dispatch trial, both requirement-stage reviewers
reported an `R3` finding: the machine model's `round-robin` label against R3's prose. The goal
answers it: round-robin is advice, and the numbered points are the whole requirement. The
coordinator adjudicated it as not a defect. The challenge grader would count it as a false finding.

**Tool loop.**
- **The earlier observation stands, and is not re-run.** It is trial 1 of the 2026-09-23 plan, and
  it applies here within the scope of the start-up bridge (identical requests to the model).
- **It is not counted as a new trial.** Nothing contradicts it: in all nine new sessions, every step
  but the last ended in `tool-calls` and was followed by another step.

## First use

**Preparation.**
- **Frozen before any launch:** `first-use-2026-09-24-preparation.json` (sha256 `a24dddc4…`).
- **What it names:**
  - the repaired instrument (`ce57f29`, clean);
  - the coordinator configurations;
  - the public task: goal `107204b7…`, and outcome check `7ac13333…`, byte-identical to the
    repository's;
  - the limits: $0.55 with a $0.05 reserve, 11 launches, 900 s, containment;
  - the handoff point: after the consistency review, before implementation admission.
- **The owner's conditional authorization** was bound to it and recorded through
  `authorize-spending`.
- **The historical pilot.** `protocol-v2.md` and `preparation-identities.json` are unchanged and
  unrun. This is not the Codex/GPT-6 pilot.

**Design phase: this coordinator, 3 launches.**
- **Start:** the ordinary goal, with no preaccepted requirements.
- **Requirements.** The author proposed R-001 to R-029, with eight open choices, each with a stated
  default. The fresh challenge found no blocking defect, having re-measured the permissive behaviour.
  The requirements were accepted, with the proposal's defaults adopted as rulings.
- **Consistency.** It found coverage complete. It was accepted, with the blank-record rule
  confirmed.

**Handoff, build phase.**
- **Fresh session 1.** It started from the continuation prompt alone. It recorded itself, admitted
  the implementation and launched the implementer, running `continue` as a background command. It
  then ended its turn: in headless mode, the session exited.
- **What that killed.** The exit killed the host controller (`pb_workflow.py continue`), and with
  it containment, the post-exit sweep and ledger classification.
- **What survived.** The detached `run_worker.py` and the worker. The attempt completed within its
  deadline: exit 0 after 133 s.
- **What the original coordinator did about it:**
  - restored containment with the production `AttemptWatch` from 12:36:08, its baseline at the
    attempt's first row; counting from there, no rule was broken at any of 45 polls, and the
    session's 22 requests all finished normally (21 `tool-calls`, 1 `stop`);
  - ran the production post-exit sweep, which found nothing running;
  - reconciled the slot with the ledger's own `classify`, from the retained reservation and
    terminal record;
  - wrote a `launch reconciliation` receipt.

  Containment was absent for 1 min 51 s. The deadline applied throughout.
- **Fresh session 2.** It started from a second continuation prompt. Every `continue` went through a
  wrapper that runs it in its own process session, so it survives the caller.
  - **Gate and review.** It gated the implementation and launched the fresh reviewer, which found no
    defect.
  - **Its own verification before accepting:** 41 tests; file hashes against the attempt's records;
    67 probes of its own.
  - **Seal and verify.** It sealed the delivery as accepted and ran `verify-delivery`.
  - **Two edge cases disclosed in its report:** strict-mode handling of non-UTF-8 input, and the
    interpreter's 4,300-digit integer limit.

**Delivery verification, run twice** (by session 2, and independently by this coordinator):

| | Result |
|---|---|
| Patch `43254c6b…` on a fresh checkout of baseline `910da0a3…` | applied cleanly |
| Project checks | 41 tests OK |
| Unchanged public outcome check | 15 / 15 passed |
| Manifest | none altered or unlisted |
| Recomputed accounting | $0.060347, matching the record |

The implementer changed `cli.py` and `summary.py` and added `test_strict.py`. The reviewer changed
nothing. The delivered files equal the implementer's recorded hashes, so no coordinator wrote
project code.

## Launches and spend

| | Launches | Derived | Unused allocation (does not transfer or renew) |
|---|---|---|---|
| Contradictory challenge | 2 | $0.012300 | 1 launch, $0.137700 |
| Coherent challenge | 2 | $0.016623 | 1 launch, $0.133377 |
| Dispatch implementation | 5 | $0.043699 | 6 launches, $0.506301 |
| First use | 5 | $0.060347 | 6 launches, $0.489653 |
| **This milestone** | **14 of 28** | **$0.132969 of $1.40** | |
| Earlier experiment (still consumed) | 3 | $0.016342 | |
| **Cumulative** | **17 of 31** | **$0.149311 of $1.416342** | |

Derived cost is measured usage priced at `deepseek-2026-09-23`. It is not billing. The executor's
own cost field uses its bundled catalogue's V4 Flash prices and is not used. The two headless
coordinator sessions reported Claude usage of $0.63 and $1.50 at list price. That is the
coordinator host's cost, separate from the authorized worker spend.

## Identities

| | Requested | Self-reported (claim) | Observed by the run | Host-reported |
|---|---|---|---|---|
| Coordinator: qualification and first-use design | `claude-code/opus` | Claude Opus 5.5 | none | — |
| Coordinator: handoff sessions 1 and 2 | `claude-code/opus`, fresh headless | Claude Opus 5.5 | none | CLI result metadata: `claude-opus-5-5` (sessions `c70b739e…`, `92bd2f47…`) |
| Worker | `deepseek/deepseek-v4-flash`, `high` | — | the requested id only | — |

The provider documents the name as temporarily routed to V4.1 Flash. No served-model identity is
claimed.

## Finding: the host controller does not survive its caller

`pb_workflow.py continue` owns containment, the post-exit sweep and classification. It runs in the
foreground of whatever called it. A coordinator host that backgrounds the command and then exits
kills it, and leaves:

- an attempt without containment;
- a reserved slot that admission refuses to pass until it is reconciled.

That refusal is the designed safeguard, and it held. Recovery needed the ledger's `classify` from a
script, because the front door has no reconciliation command.

The smallest repair is for `continue` to detach its own host controller, or for the workflow to
offer a supported reconcile-from-evidence command. The wrapper used here is an operator
workaround, not a repair.

## Evidence

- **Committed.**
  - The authorized plan and graded result:
    `evals/results/qualification-live-2026-09-24-continuation-deepseek-v4-flash-high.json`.
  - This record.
  - The first-use preparation: [first-use-2026-09-24-preparation.json](first-use-2026-09-24-preparation.json).
- **Local and private.**
  - Qualification runs: `~/proofbound-evidence/qualification-2026-09-24-continuation-deepseek-v4-flash-high/`.
  - First-use run, handoff prompts and session outputs, restored-watch record and both
    verifications: `~/proofbound-evidence/first-use-2026-09-24-csv-claude-code-opus/`.

## What this does not establish

- Reliability: each cell is one observation.
- Independent discovery in the contradictory case.
- Held-out capability: the fixtures are development fixtures, and the dispatch corpus was readable.
- Which model served the requests.
- That derived limits bound billing.
