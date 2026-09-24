# Current roadmap: evidence before expansion

This is the current product route; the [historical implementation plan](architecture/specification-reflection-harness-implementation-plan.md)
retains design history. Capability tests establish mechanisms; regression tests protect known behavior.
Neither a larger test count nor more agent activity establishes product value. The product claim is
better engineering outcomes at acceptable total effort — not more agents, more documentation or more
tests.

Four words are kept apart everywhere below: **ready to configure** (the software accepts and checks
the configuration), **mechanically qualified** (stand-ins exercised the production path and its
graders), **live-observed** (a real model or agent did the work, once per condition), and
**comparatively beneficial** (a declared comparison showed an improvement worth its effort).

## Stages

| Stage | Capability | Evidence gate | Status |
|---|---|---|---|
| Now | [`CAP-profiles`](#cap-profiles) — selectable worker profiles and trustworthy configuration qualification and comparison | Production-path offline demonstration, missing-data and adversarial checks, DeepSeek compatibility | **Mechanically qualified** (2026-09-23) |
| Now | [`CAP-first-use`](#cap-first-use) — minimum live qualification, then one first-use delivery; a paired comparison later | Retained live delivery from unseeded upstream authority, applied to a fresh baseline checkout with checks rerun; for a later pair, the same coordinator in each arm | Prepared; **awaiting owner spending authorization** |
| Next | [`CAP-progression`](#cap-progression) — mechanical progression to the next judgment, and interruption inspection | Same authority and attempts as single-step driving; fewer coordinator interactions; no automatic adjudication or reroll; read-only diagnostics mutate and signal nothing | Not started |
| When a local model is installed | [`CAP-local-worker`](#cap-local-worker), then [`CAP-local-coordinator`](#cap-local-coordinator) | Actual hardware, model, server and template identities; tool-loop and role tasks; cold/warm performance, context pressure, cancellation and resources; no borrowed "Opus-level" claim | Ready to configure; unqualified |
| After an observed context bottleneck | [`CAP-context`](#cap-context) — bounded discovery, compact evidence, retrieval and caching | Original-source fallback, missed cross-file defects, cache invalidation, permissions and total usage measured | Research |
| Product evolution | [`CAP-durable-binding`](#cap-durable-binding) — durable implementation-to-authority binding and architectural checks across changes | Delete runtime evidence without losing the binding; a second realistic change exposes prevented drift and false positives | Gap stated in A6.6 |
| Evaluation maturity | [`CAP-eval-panel`](#cap-eval-panel) — failure-to-regression pipeline, role-specific panel, calibrated semantic graders, selection guidance | Curated real failures, held-out tasks, repeated outcomes, human/checker calibration, explicit populations; no automatic leaderboard | Not started |
| Conditional | [`CAP-falsifiers`](#cap-falsifiers) — orthogonal falsifiers and selected formal-consequence checks, including a Bend experiment | Unique defects beyond existing tests; independently accepted formalization; weakened/vacuous-law controls; toolchain and semantic boundaries recorded | Research |
| Conditional | [`CAP-interop`](#cap-interop) — more executor adapters and normalized trace import/export | Adapter contract tests, truthful missing fields, per-host qualification; Harbor/ATIF only when a concrete integration consumes it | Research |
| Research | [`CAP-reasoning`](#cap-reasoning) — decision, assumption and failure-case obligations as a candidate treatment | Frozen comparison against the current policy, counting real defects found, wrong corrections introduced and effort | Non-normative |

**Not required now**, each needing a demonstrated bottleneck and a testable benefit first: native
frontier subagents as delegation, automatic model escalation, dashboards, cloud evaluation services,
MCP expansion, parallel swarms, distributed scheduling. Harbor, Portal, LangSmith and Bend are sources
of design lessons, never core dependencies. **Coordinator neutrality is a property of the workflow,
not a milestone**; see the README's support matrix.

Development fixtures, regression anchors and held-out tasks are different things. Optimising against
the same exposed fixture and calling it generalization is how a benchmark fits itself (`E24.5`);
public benchmarks may supplement, never replace, Proofbound's own architecture and authority tasks.

## Capability records

Each record states: problem · proposed behavior · why · dependencies · evidence already available ·
smallest next experiment · accept/defer condition · status · next action.

### CAP-profiles

- **Problem.** The worker route was hard-coded, and there was no way to learn what a configuration can do here before choosing it. Comparisons could certify controls nobody recorded.
- **Behavior.** `--worker-profile` fixes a resolved, digested worker configuration per run. `authorize-resources` bounds an unbilled worker. `evals/pb_qualify.py` plans, replays, grades, inspects and compares.
- **Why.** Selection needs evidence gathered on the path that will be used, not a model's reputation.
- **Dependencies.** None open.
- **Evidence.** [2026-09-23 record](architecture/proofbound/evidence/worker-profiles-qualification-2026-09-23.md): offline production path, 17/17 replay variants graded as declared, comparison overclaim repaired.
- **Next experiment.** A live qualification plan for DeepSeek under explicit owner authorization, to observe the three worker cases once.
- **Accept/defer.** Accepted as offline-tested infrastructure. Nothing about any model follows.
- **Status.** Mechanically qualified. **Next action:** owner decides whether to authorize the live DeepSeek plan.

### CAP-first-use

- **Problem.** The goal-to-change workflow has never run end to end against a real agent.
- **Behavior.** Unchanged workflow. First, the minimum live qualification: four worker trials
  proposed with enumerated per-trial limits. Then one first-use delivery of the public CSV task,
  separately identified under the coordinator that actually drives it. A paired comparison comes
  later, with the same coordinator in both arms.
- **Why.** Usability defects surface faster in one real use than in another platform.
- **Dependencies.** Owner spending authorization; coordinator capacity.
- **Evidence.** [Readiness, 2026-09-23](architecture/proofbound/evidence/first-use-readiness-2026-09-23.md):
  six qualification defects repaired, containment of the executor's response loop, the V4.1 Flash
  price interpretation, and a stand-in rehearsal of the first-use recipe through fresh-checkout
  verification. The [protocol-v2 pilot](../examples/csv-summary/protocol-v2.md) stays frozen for
  aff0c75 and Codex/GPT-6, and unrun.
- **Next experiment.** The live qualification proposal, then `examples/csv-summary/first_use.py`.
  Never re-executed under changed instrument bytes without a new freeze.
- **Accept/defer.** One sealed delivery that applies to a fresh baseline checkout, with checks
  rerun, is a usability observation. It is not reliability, and not superiority.
- **Status.** Prepared; not authorized; not run. **Next action:** the owner's spending decision on
  the stated proposal.

### CAP-progression

- **Problem.** Driving `status`/`continue` one mechanical step at a time costs coordinator interactions that carry no judgment. An interrupted attempt needs manual process and evidence inspection.
- **Behavior.** Advance through mechanical steps until the next judgment or blocker. Add a read-only inspector for terminal-less attempts.
- **Why.** Coordinator tokens are the expensive resource (`P13`).
- **Dependencies.** `CAP-first-use` observations of where interactions are actually spent.
- **Evidence.** None yet beyond the design of `continue`.
- **Next experiment.** Replay the goal-to-change fixture both ways; compare interactions, attempts and receipts.
- **Accept/defer.** Accept only if authority, attempts and receipts are identical. It never adjudicates, rerolls or signals.
- **Status.** Not started. **Next action:** wait for first-use interaction counts.

### CAP-local-worker

- **Problem.** An owner with local hardware cannot tell whether a local model can do Proofbound's worker roles.
- **Behavior.** A `local-openai-compatible` profile through the same pinned executor, with loopback-only network, no credential and unbilled resources ([worker-profiles.md](architecture/proofbound/worker-profiles.md)).
- **Why.** Cost and privacy preferences are the owner's to trade, on evidence.
- **Dependencies.** A local server and model. For llama.cpp, [tool calling](https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md) needs the right chat template. OpenCode's [provider docs](https://opencode.ai/docs/providers/) describe newer features the pinned build may lack.
- **Evidence.** Mechanics only: a scripted endpoint through the real executor. It showed zero-usage recording and an unbounded retry storm until the deadline.
- **Next experiment.** `pb_qualify.py plan --mode live` for the installed profile. Record hardware, server, weights, quantization and template as declared; then the tool loop, the two worker cases, cold and warm timing, context pressure, and deadline behaviour.
- **Accept/defer.** Per configuration, per host. Accounts such as [this local-agent report](https://ailocal.substack.com/p/im-running-an-opus-level-coding-agent) and [this setup](https://mysetup.ai/u/gareth) are scoped claims to investigate, never inherited properties.
- **Status.** Ready to configure; unqualified. **Next action:** install a model, then run the live plan.

### CAP-local-coordinator

- **Problem.** A local agent as coordinator is a separate question from a local worker.
- **Behavior.** Unchanged protocol; the coordinator identity is recorded as requested, self-reported and observed.
- **Dependencies.** `CAP-local-worker`, and the live half of `authority-recovery`, which is not wired yet.
- **Next experiment.** A coordinator comparison (`E27.1`) with the worker path held fixed.
- **Status.** Not started. **Next action:** wire the live half of `authority-recovery` with seeded states.

### CAP-context

- **Problem.** Workers may miss cross-file constraints, or spend context rediscovering them.
- **Behavior.** Portal-style bounded discovery (compare Spotify's [shunt](https://github.com/spotify/portal-ai-plugins/blob/main/plugins/shunt/README.md)), compact evidence, retrieval and caching — reusing `dsd-discovery` rather than a new code-writing path. Summaries navigate; governing requirements are always read in the original.
- **Why.** Only after a context bottleneck is observed; see [context-economy.md](architecture/proofbound/context-economy.md) and [context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).
- **Evidence.** MLR series (one fixture, one model).
- **Next experiment.** A frozen `E24` comparison against the current policy: missed cross-file defects, fallback to the original source, cache invalidation, permissions, total usage.
- **Status.** Research. **Next action:** none until a bottleneck is observed.

### CAP-durable-binding

- **Problem.** Implementation-to-authority binding lives in the run tree and dies with it ([A6.6](architecture/proofbound/freeze-and-binding.md#a66-execution-binding-only--the-durability-limitation-stated)).
- **Behavior.** A durable record some invariant actually consumes, plus architectural checks derived from accepted constraints.
- **Next experiment.** Delete runtime evidence after delivery; show a second realistic change catching dependency, API or data-lifecycle drift, and count false positives.
- **Status.** Gap stated. **Next action:** after `CAP-first-use`.

### CAP-eval-panel

- **Problem.** Every task so far is a development fixture; nothing is held out, and real failures are not yet turned into regressions systematically.
- **Behavior.** Curated real failures become regressions (the loop [LangSmith](https://docs.langchain.com/langsmith/evaluation) describes, without the service). A role-specific task panel, graders calibrated against humans and checkers, and selection guidance with explicit populations.
- **Why.** Evaluate model and harness together, outcomes apart from transcripts ([agent evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)); compare within one identified suite version ([CursorBench](https://cursor.com/blog/cursorbench)).
- **Next experiment.** Convert this milestone's observed executor behaviours — zero usage, retry storm — into permanent anchors, already done offline. Add the first held-out task.
- **Status.** Not started. **Next action:** after repeated live outcomes exist.

### CAP-falsifiers

- **Problem.** Existing tests may share blind spots with the implementation they test.
- **Behavior.** Orthogonal falsifiers and selected formal-consequence checks, including a [Bend](https://github.com/bendlang/bend/blob/main/guide/GUIDE.md) experiment.
- **Accept/defer.** Only for unique defects beyond existing tests, an independently accepted formalization, and controls with weakened or vacuous laws.
- **Status.** Research. **Next action:** none scheduled.

### CAP-interop

- **Problem.** One executor adapter; traces are Proofbound-specific.
- **Behavior.** More executor adapters with contract tests and truthful missing fields. Normalized trace import/export ([Harbor concepts](https://docs.harborframework.com/core-concepts), [ATIF](https://docs.harborframework.com/core-concepts/agents/atif), [separate verifiers](https://docs.harborframework.com/core-concepts/tasks/separate-verifier)) that keeps provenance and privacy boundaries.
- **Accept/defer.** Only when a concrete integration consumes it; qualification per host.
- **Status.** Research. **Next action:** none scheduled.

### CAP-reasoning

- **Problem.** Better adjudication might come from stating the decision and constraints, exposing material assumptions, naming plausible failure cases, obtaining external evidence, and saying which evidence supports the decision. Self-critique might add defects found, or wrong corrections.
- **Behavior.** Non-normative until adopted. The coordinator protocol already asks for the first four as adjudication practice. Worker-side reflection would be a candidate treatment, never a default.
- **Why.** The supplied [prompting article](https://medium.com/profitable-minds/most-prompts-dont-make-ai-think-this-one-does-9aa05b27ff51) is a hypothesis from personal experience, not an experiment. Reasoning reports are [not reliably faithful](https://www.anthropic.com/research/reasoning-models-dont-say-think), so narrative is never execution evidence. Repository maps and mechanical constraints follow [harness engineering](https://openai.com/index/harness-engineering/).
- **Next experiment.** A frozen `E24` comparison on the requirements-challenge and dispatch cases, counting real defects found, wrong corrections introduced and effort. It must never be paid on every simple task by default.
- **Status.** Non-normative. **Next action:** only after live qualification data exists.
