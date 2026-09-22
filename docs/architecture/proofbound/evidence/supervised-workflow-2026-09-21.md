# Supervised workflow — 2026-09-21 development observation

Baseline: `c83efbfdf5968cf73ff9b927a28b134f1eea5f04`. Fetched without merging; the initial worktree
was clean and no later local commits were present. Historical instrument:
`af10cbfb6e886eb82aafc04c329ec45979cb6ca8`. No paid experiment was rerun and no new provider request
was authorized or launched for this milestone.

## Interpretation retained

Reproduced qualification with the public `pb_evidence.py qualify` commands: pb-handoff-2 valid
qualifies; control does not. Historical packages were not changed. One real continuation from seeded
upstream authority delivered an accepted implementation with mechanically enforced admission and
replayable artifact checks. It did not establish reliability, superiority to a direct agent, or good
upstream authority production. The control legitimately restored a derived consistency record from
retained qualifying accepted evidence. Missing a derived record differs from never earning authority.
See [the committed report](../../../../evals/authority_slice/runs/pb-handoff-2/run-report.md).

The old live refusal receipt and coordinator report were absent because writers lived only in
rehearsal code; the home probe addressed the staged home instead of the host home. Those are
collection defects, not revisions to historical outcomes. New code records actual authorization and
admission refusals separately from unchanged authority state, retains direct/relayed coordinator
reports before delivery sealing, and distinguishes absolute host paths from the staged home.

## What changed

[The operator guide](../../../operator-guide.md) describes the new `pb_workflow.py` commands. They
compose existing task bindings, attempts, gates, artifact ledger, freeze, consistency and admission.
Initialization generates unaccepted authority templates from an ordinary project and goal. Semantic
adjudication is explicit; no worker prose is parsed as acceptance. Within-goal requirements revisions
create new immutable contracts and renewed challenge. Owner decisions and new spend remain explicit.
There is no new general scheduler or parallel agent platform.

The launch guard, accounting rows/profile/dated pricing and constructed view moved to production
modules under `scripts/`. Evaluation imports the shared implementation, retaining its own experiment
policy and fixture constructors. Production contains neither seeded authority constructors nor task
answer implementations. Budget limits govern this supervised wrapper's derived usage, not all tools
or provider billing. Direct executor use remains outside it.

The supported new path is macOS arm64 / Python 3.10+ / pinned OpenCode 1.18.29 /
`deepseek/deepseek-v4-flash`, high. The inherited `opencode-go/deepseek-v4-flash` default is not the
same provider route. The local interpreter is 3.14.7. The pinned executable matches the digest in
pb-handoff-2. Readiness reports credential presence without exposing it or probing a provider.

Codex CLI 0.155.1 locally reports hooks and multi_agent as available features. This does not show
that project hooks are trusted or have fired. The new path uses explicit `status`/`continue` and
requires no hook or native worker support. GPT-6 is the requested development/coordinator environment,
not a qualified replacement worker backend.

## Development checks and limits

Credential-free integration tests drive the actual operator CLI from `start` through fresh role
attempts, explicit scripted adjudication, admission, implementation, project checks and delivery.
They include paths with spaces and repeated initialization; initial refusal with state bytes
unchanged; retained-evidence recovery; clean consistency review without semantic acceptance;
admitted C1 continuation after intent movement; stale-review rejection; requirements revision;
and unreconciled launch intents. Stand-ins explicitly label their reports and never fall through
to real credentials. These are mechanical capability/regression observations, not agent evaluation.

Separate tests check malformed/missing token accounting, and a real macOS boundary process probes
an absolute denied host sentinel and an allowed staged home without retaining contents. The existing
public-path/semantic-view tests also pass on this platform. Nested sandbox-exec is denied by the
Codex enclosing sandbox; the readiness diagnosis detects this. Running the credential-free probe
outside that enclosing sandbox passes. Other operating systems are unqualified; macOS-only tests
must skip there. No SIGKILL-safe finalization claim is made.

Development friction found and repaired: initial contract generation omitted the inherited revision
header; the first front-door tests caught it before any live use. Nested task attempt names exposed
an accounting collision (two spec-reflector-1 directories); production attribution now uses distinct
relative paths while preserving old leaf-name callers. Final acceptance/delivery compares the live
project with the fresh review baseline so later source edits cannot quietly reuse a stale review.
A refused or interrupted run keeps evidence; blocked delivery is explicitly labelled unaccepted.

## First use and comparison

The [ordinary CSV project](../../../../examples/csv-summary/README.md) is executable and its existing
three tests pass. The proposed strict-mode change affects parsing, aggregation, CLI failure behavior
and compatibility. The frozen public outcome checker rejects the unchanged baseline. Sensitivity
checks reject implementations that ignore strict mode, reject valid input, or print partial output
before a CLI error. No reference implementation is embedded in the harness. The checker is public
to both arms; no hidden-test or hidden-answer-key isolation is claimed.

The [paired protocol](../../../../examples/csv-summary/protocol.md) fixes the task, common constraints,
starting identity, resource ceilings, single repair policy, stopping conditions and equivalent fresh
handoff opportunities. `prepare.py` builds two isolated clones and a manifest before either arm.
The separate greeting-library task is used for development rehearsals; CSV has not run as an agent
trajectory or been used to tune the workflow.

**No paired result and no new observed real-agent goal-to-change result.** Two attempted parallel
development contexts failed with an account usage-limit response. Worker spending was not authorized.
Fresh coordinator capacity and explicit worker spending authorization are the remaining live execution
dependencies. Neither stand-in success nor this preparation substitutes for that observation. Calls,
tokens and cost for these unrun arms are not measured outcomes; subscription development usage is
unavailable, not zero.

The next evidence gate is this frozen first pair, then repeated fresh tasks and a second change in
the same project, reporting engineering quality and total effort together. See the
[current roadmap](../../../operator-roadmap.md).

## Methodological inputs, not performance evidence

[OpenAI harness engineering](https://openai.com/index/harness-engineering/) informs short reading
routes and enforceable constraints. [Anthropic long-running harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
informs explicit initialization and resumable progress. [Agent evaluation methodology](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
informs independent outcome checks and preserving terminal outcomes. [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988)
cautions against treating additional instructions as automatically useful. None establishes
Proofbound performance.


## 2026-09-22 addition: fresh development review

Fresh coordinator capacity became available again. A separate context read the current production
code/tests before reporting findings; this was a development review, not a pilot arm. It found stale
requirements acceptance, C1 record recovery incorrectly selecting current intent, preflight failures
stranding slots, aggregate pricing across rate windows, and owner requests disappearing on resume.
All five were repaired and focused regressions added. A second read-only review of those repairs
found no further release-blocking issue within that bounded coverage. No statistical independence
or real-worker qualification follows from this review.

The pricing correction uses retained message timestamps for finished calls, grouping token counts by
applicable window before rounding and retaining call identities. Missing timestamps leave costs
unknown; message timestamps are an observed proxy, not provider billing timestamps. The package
reader has a new-method branch while historical packages retain their original interpretation.

Owner requests now persist as attributable decision receipts and require an explicit retained owner
response before adjudication resumes. Requirements are checked against reviewed bytes before both
acceptance and ledger recording. Recovery uses the candidate actually named by the accepted
consistency contract. Deterministic interpreter/executable preflight failures retain refusal receipts
without reserving a paid slot; genuinely uncertain launches still block as unresolved.

Fresh coordinator capacity is no longer the live dependency. The remaining dependency for the
unrun frozen pilot is explicit owner authorization for its external-worker spend. No past budget
was reused.

Final boundary review found the production worker PATH could select Apple's older Python and the
staged hard-linked executor fell under the runtime write allowance. The production boundary now
stages the recorded interpreter and explicitly denies writes to tools and the boundary profile.
A credential-free real sandbox test observes the supported interpreter, denies attempted writes,
and verifies the original linked bytes remain unchanged. This is bounded coverage, not a hostile-code
sandbox qualification.

The first serial suite ran 1,289 tests with one failure: finalization exposed absolute attempt paths
where the existing flat-run wire format expected names. The repair preserves flat names and uses
run-relative identities for nested attempts; a focused reload/collision regression passes. A later
serial run was deliberately interrupted for the boundary repair above. Neither run is reported as
passing final validation. A focused invocation also had a mistyped unittest class selector; the
corrected class passed separately. These are development interventions, not pilot outcomes.

## Final offline validation — 2026-09-22

At the final code state, the canonical serial command
`python3 -m unittest discover -s tests -t .` passed: **1,290 tests in 777.778 seconds,
one skipped**. The skipped historical MLR round-trip test requires a retained session archive
absent on this machine. Current macOS boundary tests executed outside the enclosing Codex sandbox;
Linux/Windows worker boundaries and other Python versions were not qualified by this run.
Documentation references and route costs pass. Source-inspection checks follow the extracted
production modules instead of inspecting only their compatibility wrappers.

A no-request readiness check reported Python 3.14.7, the pinned OpenCode 1.18.29 digest,
`deepseek/deepseek-v4-flash` / high, credential presence and an available macOS boundary, with
zero provider requests. This is configuration readiness, not credential validity or live workflow
qualification. Final-state replay again qualified historical valid and did not qualify control;
no historical package bytes changed.

Implemented functionality and offline validation are complete for this bounded path. Real-agent
first use and the paired outcome remain unobserved, pending the frozen protocol's explicit worker
spending authorization. Total development subscription usage is unavailable, not zero. No software
quality advantage, reliability estimate or reduced total effort is established by this milestone.
