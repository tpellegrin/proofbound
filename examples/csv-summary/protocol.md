# csv-summary-pilot-1 — freeze before either arm

Status: prepared, neither arm run. This is one diagnostic paired task, not a reliability study.
The common public task is `goal.md`, starting files `project/`; `prepare.py` creates a single seed
commit and two isolated clones with that exact identity. `freeze.json` records file digests and
starting revision. Freeze the committed harness revision too before launch. Do not tune on this task;
development uses the separate greeting-library rehearsal in `tests/test_operator_workflow.py`.

Both arms use fresh Codex/GPT-6 coordinator contexts with the same ordinary repository, shell and
coding tools. The direct arm may inspect, plan, implement, test and self-review competently. It gets
the same goal, checks, compatibility constraints, ordinary tools and opportunity to retain notes.
The treatment follows `pb_workflow.py` with pinned OpenCode/DeepSeek workers. This compares two
complete workflow configurations, not the isolated effect of contracts or review.

Common ceilings: 45 minutes elapsed per arm, 60,000 observed coordinator tokens per arm where
telemetry is available, at most 10 minutes human setup/intervention per arm. Subscription tokens and
cost that cannot be measured are unavailable, not zero. Record worker and coordinator effort
separately and total them where measurements permit. Treatment worker allowance proposal: $0.60
aggregate derived usage with $0.10 reserve, at most 9 launches, 900 seconds per attempt, one repair
cycle per producer task within that total. Direct arm receives the same overall optional external
worker allowance if it elects to delegate; otherwise report that resource difference. These numbers
are proposed ceilings, not spending authority, and do not cap provider billing.

Both arms may run project checks and public outcome checks during development. A failure may be
repaired once after review within the overall ceilings; no fresh trajectory. Stop on time/resource
ceiling, unresolved authority, unknown spend, unavailable worker, or a second failed repair. Retain
all terminal outcomes including infrastructure failures. Do not replace the task after seeing results.

Handoff: after recording proposed requirements/plan and before implementation, terminate each
coordinator context. Resume each in a fresh context with repository and retained notes. The treatment
uses `status`; direct receives its own normal notes and files. Record whether continuation succeeds,
manual interventions and elapsed setup friction. Do not withhold ordinary retained information from
the direct arm. Treatment requirements and upstream acceptance must actually be produced/challenged.

Outcome checks: run `check_outcome.py ARM` and project unittest in an evaluator process, retain the
exact output and code identity. These checks are independent of implementation reports and public:
no hidden requirements, reference implementation or answer key is supplied. The grader's public
assertions are visible to both arms. This avoids claiming a hidden-test boundary the host coordinator
cannot enforce. Record any additional evaluator material exposed. Before launch validate that the
checks reject the unchanged baseline and representative broken strict-mode implementations; do not
change predicates after freezing.

Final comparison has separate rows for requirement satisfaction, regressions/compatibility, concrete
independently reproduced defects, false acceptance and false rejection where observable, interventions,
fresh continuation, calls/tokens, elapsed time and monetary cost with accounting limits. A coordinator
accepting failing output is observable false acceptance; a sound rejected output requires independent
checking before counting false rejection. Unobserved rates are not zero. No composite score, percentage
improvement or superiority claim from one pair. A tie, worse result or unmeasured outcome stays so.

Record coordinator's final decision before sealing evidence, with direct/relayed provenance. Reviewers
state visibility, initially judging accepted requirements, code and checks before producer summaries
where practical. Fresh context does not prove independence. No reruns of a terminal arm.

Remaining execution dependency: owner-authorized external worker spend under these frozen limits.
Fresh GPT-6 coordinator contexts are available again after the initial development capacity interruption. Existing pb-handoff-2 authorization is exhausted and does not apply.
