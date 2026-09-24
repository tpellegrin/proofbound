# Qualification continuation — proposed, NOT authorized

`plan.json` beside this file is the frozen proposal, digest
`d591a1485661dff3c48c5b897dd5e766cff11ea3a6afc4ced71622dd0853ee97`, status
`proposed-not-authorized`. Every executing command refuses it until
`pb_qualify.py authorize --proposal … --owner-authorization '<the owner's statement>'` turns it
into a plan. It does not amend the 2026-09-23 plan (`8370c2d4…`), whose failed attempt stays
recorded as it was. See [executor-startup-2026-09-24.md](../../../../docs/architecture/proofbound/evidence/executor-startup-2026-09-24.md).

## Identities frozen

| | |
|---|---|
| Harness | `91a472e`, clean (provenance) |
| Suite | `390c2c7286d6c590…`: answer-free findings format, and challenge `exposure` |
| Control plane | `371d962fd7606a00…`: the executor start-up repair |
| Interpreter | Python 3.10.14, `/opt/homebrew/opt/python@3.10/bin/python3.10` |
| Executor | OpenCode 1.18.29, `2f24593f…d669` |
| Worker settings | `6af2663d197d9322…`: `deepseek-v4-flash-high` revision `2026-09-24`; request `deepseek/deepseek-v4-flash --variant high`; priced at `deepseek-2026-09-23` as `deepseek-flash` |
| Model catalogue | the one bundled in the executor bytes above; fetching is disabled, and a cached copy refuses the launch |
| npm dependencies | none: the executor's install of `@opencode-ai/plugin` is skipped, and the launcher refuses any state in which it would run |
| Coordinator (planned) | `claude-code/opus`; each run records requested, self-reported and observed separately |

## Trials and what each measures

| Trial | Measures | Path (launches) | Minimum | Ceiling | Derived limit |
|---|---|---|---|---|---|
| requirements-challenge / contradictory | **Production-path challenge.** A fresh reviewer, shown the goal and the author's proposal, names the conflicting requirements with a witness that reproduces by enumeration. The coordinator does not accept. `exposure` says whether the witness was already in what the reviewer saw (**verification**) or not (**found on the production path**). Unassisted discovery is not claimed | author, fresh challenge; + 1 pre-executor | 2 | 3 | $0.15 |
| requirements-challenge / coherent | Sound control: no false finding, and correct acceptance | the same | 2 | 3 | $0.15 |
| dispatch-implementation / coherent | Delivered code satisfies the contract under the unchanged checker, first attempt and after at most one repair; review findings reproduce on the bytes reviewed; accepted through the review path | author, challenge, consistency, implementer, reviewer; + repair (fixer, reviewer) 2; + revision (author, challenge, consistency) 3; + 1 pre-executor | 5 | 11 | $0.55 |
| **Total** | | | **9** | **17** | **$0.85** |

Each limit is the ceiling times the $0.05 per-launch allowance, with a reserve of one allowance per
trial. The deadline is 900 s per attempt, and containment is 150 requests, 5 trailing incomplete
responses, or derived spend beyond the trial's remaining room.

**Information exposure.** Nothing on the production path is hidden. The author's proposal is a
normal input, and an author that flags a conflict is behaving well. No goal states any case's
answer: the example that did is gone, which is why both case identities changed. The dispatch
reference corpus remains readable by the worker, so dispatch results are development evidence, not
held-out capability. Unassisted discovery would need a separately identified setup, in which the
reviewer sees only the owner's text; it is not proposed.

## Prior evidence reused, and its limits

- **Tool loop: met** once, in the 2026-09-23 plan's trial 1 (suite `0dfed363…`, control plane
  `e68a5ba2…`, settings `7aa8ef0d…`). It is carried forward as that observation and is not
  re-measured.
  - **Why it applies.** An unpaid bridge showed the executor's requests byte-identical under
    trial 1's start-up and the repaired one, and trial 1 already used the bundled catalogue.
  - **Limits.** It is one observation. The bridge compares requests, not the provider's behaviour.
    First-use gate condition 1 rests on it. If the owner prefers a direct observation under the
    new settings, adding the `tool-loop` case costs 1–2 launches and $0.10; that is not proposed.
- **Not reused.**
  - The failed trial's author attempt: its goal showed the answer, and the suite differs.
  - Its failed reviewer attempt: an infrastructure failure, which stays recorded as one.

## Repair, retry and stopping

- **No reroll.** The challenge cases have no repair. Dispatch has only the enumerated repair and
  revision above.
- **The pre-executor allowance** covers only a launch that fails before the executor starts. A
  start-up state the launcher refuses reserves no slot at all.
- **An attempt that reaches the executor and fails with no model request** is retained, with its
  `worker.log` and `executor-state.json`, and stops its trial. If its logged cause lies in the
  shared start-up path, it stops the remaining trials too.
- **These also stop affected execution:**
  - unknown spend;
  - unresolved lifecycle evidence;
  - failed containment;
  - exhausted allowances;
  - a material failure affecting the shared execution path, which stops the trials after it.

  Allowances never transfer between trials, and never renew through resumes, restarts, new run
  directories or coordinator contexts.
- **No grader, check or instrument changes during measurement.** `prepare-live` and `grade` refuse
  a changed suite, control plane or interpreter.

## Spending and authorization

| | Launches | Derived |
|---|---|---|
| Consumed by the 2026-09-23 plan (stays consumed) | 3 | $0.016342 |
| This proposal, at most | 17 | $0.85 |
| Cumulative, at most | 20 | $0.866342 |

**Requires a new owner authorization of $0.85 and 17 launches.** The earlier qualification
authorization does not cover it. Its allowances do not transfer between trials or renew through
new runs, and 3 + 17 launches would exceed its 19 anyway.

**First use stays contingent on the gate, and is not started.** The earlier conditional first-use
authorization ($0.55, 11 launches) was granted against the earlier qualification. Whether it
applies to a gate met by this continuation is the owner's decision, to be asked when the gate is
met.

Derived spend is measured usage at a dated table, not billing. In-flight calls and missing usage
can make actual charges exceed it.

## Running it, and fresh-session handoff

1. `pb_qualify.py authorize --proposal evals/qualification/proposals/2026-09-24-deepseek-v4-flash-high-continuation --owner-authorization '<statement>' --into evals/qualification/plans/2026-09-24-deepseek-v4-flash-high-continuation`
2. `pb_qualify.py prepare-live --plan <that plan> --into <runs>`. It checks readiness, starts and
   authorizes one run per trial, and launches nothing. The code must still carry this proposal's
   suite and control-plane digests.
3. The coordinator drives each run with `pb_workflow.py status`/`continue`/`decide` only. It
   records itself with `pb_workflow.py coordinator` and adjudicates for real.
4. `pb_qualify.py grade --plan <plan> --live <runs>`, then `inspect`.

**A fresh coordinator session** needs only three things:
- each trial's run path;
- `pb_workflow.py status --run <run>`, which gives the governing facts and the single next action;
- that trial's remaining launches and derived room, stated in the handoff prompt.

The new session records its own identity before acting. Nothing it does renews an allowance. First
use, if the gate is met and the owner confirms, is handed to a genuinely separate session with a
paste-ready prompt.
