# First-use readiness — 2026-09-23 (second milestone)

Baseline `0d2f9ee`, which **is** on `origin/main`: the previous record's "not pushed" was true
when written and the owner has since pushed all four commits. The working tree was clean. **No
provider request was made, no model was installed, and nothing was spent.** No owner spending
authorization exists for this milestone. The frozen CSV `protocol-v2.md` and
`preparation-identities.json` are unchanged and remain unrun.

## Where the product stood

- **Demonstrated.** The supervised workflow is exercised offline, through the real front door,
  from goal to sealed delivery. The DeepSeek worker path was observed live once, in `pb-handoff-2`,
  continuing from seeded authority. Qualification mechanics are replayed with stand-ins.
- **Unobserved.** No real agent has taken a goal to a delivery. No live qualification has run.
  V4.1 Flash, which the provider now serves for the requested model name, has never been observed.
- **Blocking live qualification.** Six instrument defects, reproduced below, one unbounded failure
  mode, and a price table that no longer described what new runs are served.
- **What establishes readiness.** A qualification whose passes need causal evidence and whose
  identities are enforced. Bounded, stated exposure. One sealed delivery applied to a fresh baseline
  checkout, with checks rerun and evidence inspected after relocation.

## Reproduced on `0d2f9ee`, then repaired

| | Reproduction | Repair | Falsifying regression |
|---|---|---|---|
| A | Finished calls at 1 and 2, the only completed tool at 3, marker and gate present: `pass`, `continuation_observed: true` | Continuation follows the pinned executor's own sequence. Each model call is one assistant message; a call whose step-finish reason is `tool-calls` must be followed by a later call in the same session. Message identifiers ascend within the executor process. Creation order and tool end times must agree with that sequence. Anything missing or contradictory is `insufficient-evidence`. One field, the step-finish `reason`, joins the usage allowlist | Shape-realistic controls: a real continuation; calls that precede the tool; another session; duplicate parts; a failed tool; a call that ended `stop`; missing reasons or identifiers; contradictory order; a tool ending after the next call; and the reproduction itself. On a real executor session the rule finds `read` → next call → `write` → next call; a real-executor replay passes on its own recorded chain, and its malformed variant does not |
| B | A validly digested plan recording interpreter `0.0` passed `assert_executable` on 3.10.14; so did an executor whose bytes differed from the plan's | Execution checks the interpreter's minor version and the planned executor's bytes. Each run `start` freezes during preparation must match the plan, or it is left out of the plan and retained. `inspect` checks nothing, so historical results stay readable | Interpreter `0.0`, moved executor bytes, and a run that froze another interpreter all refuse |
| C1 | `grade` succeeded after the grader's bytes changed | Grading refuses under a changed suite, control plane or interpreter. It names the planned harness commit to grade from and touches no run. The instrument digest now also covers `pb_qualify.py`, both stand-ins and the replay corpus | A changed suite digest refuses grading |
| C3 | An attempt with `attempt.json` and no terminal record was graded `completed` | A trial is `completed` only when every attempt concluded, every launch slot is classified, and the case's own stopping point was reached. Otherwise it is `incomplete`, with the reason | No attempt; an unterminated attempt; an unclassified slot; a missed stopping point |
| C4 | After a repair, reviewer-2's clean report on the repaired code was graded as the review of the defective first attempt | Each review is graded against the retained bytes whose sha256 its own scope baseline recorded; with no such bytes it is `unavailable`. A first-attempt snapshot counts only if it is what the first reviewer saw | Three reviewers: first bytes, delivered bytes, unretained bytes; and a mismatched snapshot |
| C6 | A result's configuration carried the plan's coordinator (`null`) and the profile's executor pin, with nothing observed | Each trial reports what its run recorded: interpreter, executor bytes, settings digest, coordinator receipts, and the executor-reported model. Results carry `observed_configuration` beside the planned one. Comparisons prefer the record and name any conflict with the plan | Agreement, disagreement and absence among runs; a plan contradicted by its record |

Also repaired: a live plan can now only be a **proposal** or **authorized**. A proposal is frozen,
retained and refused by every executing command; `pb_qualify.py authorize` turns it into a plan only
with the owner's own statement, and otherwise changes nothing. Launch ceilings are enumerated per
case rather than set by one per-trial flag.

## The provider changed under the requested name

Read on 2026-09-23 from [the updates page](https://api-docs.deepseek.com/updates/) and
[pricing](https://api-docs.deepseek.com/quick_start/pricing/). On 2026-09-10 V4 Flash was
retired. `deepseek-v4-flash` is "temporarily routed to V4.1 Flash" and "billed at the Flash
price": $0.003 cache hit, $0.15 cache miss and $0.60 output per million tokens off-peak, doubled at
peak. Peak now excludes Chinese public holidays, which is not modelled; that can only overstate.

- **Request.** Unchanged: `deepseek/deepseek-v4-flash`, `--variant high`, which is the request
  shape the pinned executor was observed sending. `deepseek-flash` appears in the executor's
  fetched model catalogue but has not been exercised through it, so it is not adopted.
- **Interpretation.** New runs use profile revision `2026-09-23`: the `deepseek-2026-09-23`
  table, priced as `deepseek-flash`, with the documented routing recorded as a dated provider
  statement. Runs recorded before profiles keep revision `2026-09-09` and its table, and started
  runs keep their frozen settings. Nothing was reinterpreted.
- **Identity.** The executor records only the requested model id and does not retain the
  response's `model` field. No alias or model string identifies weights. `pb-handoff-2` observed
  V4 Flash, and nothing retained covers V4.1 Flash.

## The 4,649-request storm, recounted

Its session holds one executor launch and 4,650 assistant messages; 4,649 are complete model steps
whose stream ended without a finish reason, recorded as `unknown` with zero tokens. There were no
tool calls and no semantic repairs. Only the last message shows transport-level retries: a
retryable connection error after the stand-in closed. The executor treats a response that ended
without a finish reason as a finished step and re-requests at once.

**What the pinned executor lets us bound.** Its agent `steps` option ("maximum number of agentic
iterations") was measured against a scripted endpoint: it stopped a healthy tool loop at 2 and 3
requests, and **did not** count the storm, which drew 420 requests in 60 s with `steps: 5`. So the
host bounds it. `AttemptWatch` reads the run's session read-only every 0.5 s and stops the attempt
through the existing host-owned teardown on any of: more than 150 requests; 5 trailing responses
without a finish reason; or, for a priced worker, derived spend of the finished calls beyond the
trial's remaining room. Against the same endpoint it stopped the attempt after 2.7 s and 6
requests — 11 at a 1 s interval, before the interval was halved — confirmed every owned process
stopped, and left the run `blocked` rather than relaunching.
A limit can be passed by the requests made within one polling interval; a call in flight, or
recorded with zero tokens, has no usage the watch can see. Runs started without containment keep
their old behaviour.

## Minimum live qualification — proposed, NOT authorized, not run

The three worker cases expand to four trials. Each trial's derived-spend limit is its enumerated
ceiling times a **$0.05 per-launch allowance**, about four times the most expensive launch in
`pb-handoff-2` at the old, higher prices. Its reserve is one allowance. Attempt deadline 900 s.

| Trial | Enumerated path | Minimum | Ceiling | Derived limit |
|---|---|---|---|---|
| tool-loop / marker | author | 1 | 2 | $0.10 |
| requirements-challenge / contradictory | author, fresh challenge | 2 | 3 | $0.15 |
| requirements-challenge / coherent | author, fresh challenge | 2 | 3 | $0.15 |
| dispatch-implementation / coherent | author, challenge, consistency, implementer, reviewer; + repair 2; + revision 3; + 1 pre-executor | 5 | 11 | $0.55 |
| **Campaign** | | **10** | **19** | **$0.95** |

These are admission and containment limits over **derived** spend, and never a provider billing
cap. Between attempts, admission refuses a launch that would exceed a trial's limit. During an
attempt, containment stops it once finished calls pass the remaining room. What neither sees:
the call in flight when a limit is crossed, calls recorded with zero tokens (at most five in a row
before containment stops them), and provider-confirmed billing, which is not observed at all.
Allowances do not renew across trials, resumes or coordinator contexts. The dispatch
implementation's reference corpus is readable by the worker. These are development fixtures, not
held-out evidence of coding capability.

## First use — prepared, NOT authorized, not run

`examples/csv-summary/first_use.py` prepares a separately identified, single-arm run of the public
CSV task under the coordinator that will drive it. The proposed limits are 11 launches and a $0.55
derived limit with a $0.05 reserve. It is diagnostic, not the frozen pilot and not held out. A
stand-in rehearsal went from the goal through requirements, challenge, consistency, admission,
implementation, review, acceptance and sealing. The delivery was then relocated and applied to a
fresh baseline checkout with `pb_workflow.py verify-delivery`. Project checks passed there, and
the public outcome check **failed**, correctly: the stand-in does not implement strict mode, and
no answer to the task was written into the harness. `verify-delivery` also re-derived usage and
derived cost from the retained rows. The authority-slice evidence exporter was tried on the same
run and is **not** a supported path for workflow deliveries: it counts the delivery's own evidence
copies as attempts.

## Tests

- **Falsification.** Every new regression fails or errors on `0d2f9ee`. The ones that use an API
  the baseline already had fail on behaviour: the external continuation reproduction, moved
  executor bytes, a mismatched first-attempt snapshot. The rest error because the guarantee they
  test did not exist.
- **Focused, macOS arm64, Python 3.10.14.** The modules the changes touch — workflow, teardown,
  deadlines, usage, evidence packages, profiles, authority slice, handoff, comparison, neutrality,
  model index — ran 332 tests, all passing. Qualification ran 44. The real-executor tests ran
  against the pinned build inside `sandbox-exec`, including containment and the continuation
  replay.
- **Canonical suite.** Recorded below by addition, from the clean commit that also freezes the
  live proposal.

**Addition, same day.** The canonical suite, `python3 -m unittest discover -s tests -t .`, ran once,
serially, on Python 3.10.14, macOS arm64, at clean commit `89c4c16`: **1,409 tests, OK, none
skipped**, in 18 min 14 s. The real-executor and boundary tests ran, because the pinned build and
`sandbox-exec` were available. On Linux CI the macOS boundary, teardown and real-executor tests
skip, and establish nothing about macOS isolation.

The live proposal is retained at `evals/qualification/proposals/2026-09-23-deepseek-v4-flash-high/`.
Its digest is `5c3b2c553fb43099ffbee87eb45bd21b0464939f00cb9360845c2d528cba93ca`, and it was frozen
from clean commit `89c4c16`: suite `0dfed3636d0a0180…`, control plane `e68a5ba21912b1bf…`, Python
3.10.14, executor `2f24593f…d669`, readiness `ready` with no provider request. Its status is
`proposed-not-authorized`, and `prepare-live` refuses it.

## What this does not establish

That any model can do the work, that the workflow delivers on a real goal, that containment bounds
billing, or that one run would say anything about reliability. The live observations this
milestone prepares for have not happened.
