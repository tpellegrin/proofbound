# Proofbound

**From engineering intent to verified implementation.**

Proofbound is an orchestration harness for agent-assisted engineering work where the requirements,
the review boundary, the execution contract and the acceptance evidence matter as much as the code
that gets written. It keeps five things that a single agent conversation collapses into one — what
you intended, what was authorized, what changed, what was independently reviewed, and what the
evidence actually proves — as separate, durable, checkable facts.

It is also, deliberately, its own first test subject: when a change to the harness is supposed to
make the work better, cheaper or more thorough, that claim is measured rather than assumed.

**Specify. Challenge. Execute. Prove.**

---

## Contents

- [The problem, and who this is for](#the-problem-and-who-this-is-for)
- [What the name means](#what-the-name-means)
- [A worked example](#a-worked-example)
- [The core concepts](#the-core-concepts)
- [What is implemented, and what has actually run](#what-is-implemented-and-what-has-actually-run)
- [What survives, and what a fresh coordinator must reconstruct](#what-survives-and-what-a-fresh-coordinator-must-reconstruct)
- [Quick start](#quick-start)
- [Where human judgment is required](#where-human-judgment-is-required)
- [Built for long runs: context, drift, and neutrality](#built-for-long-runs-context-drift-and-neutrality)
- [How evaluation improves Proofbound](#how-evaluation-improves-proofbound)
- [Direction, and the evidence that would justify it](#direction-and-the-evidence-that-would-justify-it)
- [Reading routes](#reading-routes)
- [Glossary](#glossary)
- [Current limitations](#current-limitations)
- [Provenance and license](#provenance-and-license)

---

## The problem, and who this is for

Coding agents are good at producing code. Producing code was never the hard part.

The hard part is keeping five things aligned: what you intended, what the agent understood, what it
actually changed, what was independently reviewed, and what the evidence really proves. A
conventional agent loop collapses all five into one conversation and one opinion — the agent's own.

Over a long run that degrades in specific ways:

- an agent works around an incident locally, and the workaround quietly becomes the house style;
- the reasoning behind a decision decays out of context, so later work contradicts it unknowingly;
- the agent that wrote the code also reviews it, carrying every assumption that produced it;
- a task "looks done" without anything mechanically establishing that it is;
- a hundred individually reasonable changes add up to an architecture nobody chose;
- the harness itself gets changed — a new role, a different context policy, a bigger prompt — and
  nobody can say whether it helped, because nothing was held fixed and nothing was measured.

**Who this is for.** Engineers running agents on work that has to survive being handed over:
software with real constraints, changed across sessions and across context windows, where somebody
will later have to establish what was decided and why. It suits a person who is willing to write
down intent and adjudicate findings. It is overkill for a one-off script, and it is not an
autonomous developer — it is a harness that makes an agent's work inspectable and bounds what it may
do.

**The product boundary.** Proofbound orchestrates, records and checks. It does not host anything,
does not manage secrets, does not ship a model, and does not decide whether engineering is good. It
takes an explicit statement of intent, produces a trail from that intent to accepted work, and
refuses to let acceptance rest on an agent's own say-so.

**The value, concretely.** At the end you have: the requirements that were accepted and their exact
content identity; what each artifact depended on when it was accepted; which independent review
qualified it, and under what declared purpose; what the implementation was authorized against;
what changed and whether anything undeclared did; and a state a fresh coordinator can pick up
without the conversation that produced it.

> Engineering intent should be specified, challenged, versioned and recorded — not described once in
> a prompt and then forgotten.

> An agent does not get to declare itself done. Acceptance is bound to evidence.

---

## What the name means

Two boundaries, one word:

1. **Execution is bound to an accepted engineering contract** — work happens against explicit,
   reviewed, versioned intent rather than a remembered prompt.
2. **Completion is bound to proof** — acceptance comes from evidence, not from an agent's assertion
   that it is finished.

### "Proof" here means deterministic, checkable facts

Proofbound divides every question into two kinds, and the split is enforced in code:

> **Code verifies facts. Agents and humans judge meaning.**

| Mechanically checkable — Python answers these exactly | Semantic judgment — no Python here decides |
|---|---|
| Did the expected file change, and did anything undeclared change? | Is this design any good? |
| Does the artifact still hash to what was accepted? | Are these requirements the right requirements? |
| Did something it depended on move? | Is this trade-off acceptable? |
| Is a required artifact missing from the declared graph? | Is the architecture coherent? |
| Does the task contract still match its immutable hash? | Is this finding genuine? |
| Did a qualifying fresh independent review actually happen, under the declared purpose? | Is the work complete in any sense beyond its contract? |

A clean mechanical gate means **safe to interpret** — never *the engineering passed*. The boundary
is enforced by `tests/test_v15_3_semantic_boundary.py`: helpers must not interpret worker prose or
decide engineering outcomes.

### What it is not

- **Not formal verification.** Nothing here proves a program correct. There is no model checker, no
  theorem prover, and no claim that accepted software is free of defects.
- **Not authenticated authorship.** A SHA-256 establishes **integrity, not authority**: it proves
  content did not drift, never who wrote it or whether they were allowed to. Proofbound has no
  signing keys and no trust root, and claims none.
- **Not a guarantee from tests.** A suite establishes what it exercises. Passing a finite suite
  supports its stated coverage and nothing wider — and an oracle can be wrong in ways no amount of
  careful running reveals, which
  [happened here](docs/architecture/proofbound/evidence/authority-workflow-demo-2-audit.md) and is
  the reason that document exists.
- **Not a measurement of engineering quality.** The evaluation machinery measures configurations
  under conditions held fixed. It produces facts for a person, and it authorizes nothing.

---

## A worked example

A shared work queue serves several tenants. One tenant enqueues a burst and everyone behind it
waits. You want fairness without making the queue unpredictable.

This walkthrough is **illustrative**: it is the runnable example in
[`evals/authority_slice/`](evals/authority_slice/README.md), and every mechanical step below has
been executed end to end with a fake executor. What has *not* happened is a real agent carrying it
from requirements to accepted implementation — see
[what has actually run](#what-is-implemented-and-what-has-actually-run).

```text
   ┌─ owner's goal ─────────────────────────────────────────────┐
   │ "a tenant's burst should stop blocking other tenants"      │  ◆ human decision
   │  the root authority. Nothing in the chain reviews it.      │    (bootstrap boundary)
   └───────────────────────────┬────────────────────────────────┘
                               │  digest stamped into every contract        ⚙ tool
                               ▼
   ┌─ proposed requirements ────────────────────────────────────┐
   │ four numbered obligations + the domain they hold over      │  ◆ authored (agent or human)
   └───────────────────────────┬────────────────────────────────┘
                               ▼
   ┌─ independent challenge ────────────────────────────────────┐  ⚙ launched, gated, scope-checked
   │ a FRESH reviewer, purpose `proposal-reflection`:           │  ◆ the verdict is judgment
   │ do these express the goal? is the domain stated?           │
   │ do any two contradict — which, and with what witness?      │
   └───────┬───────────────────────────────────┬────────────────┘
           │ a concrete defect                 │ no defect found within coverage
           ▼                                   ▼
   ┌─ routed back to authority ──┐   ┌─ accepted ──────────────────────────┐
   │ "requirements 2 and 3 can-  │   │ recorded with its exact content     │ ⚙ ledger record
   │  not both hold; witness:    │   │ identity, its dependencies, and the │
   │  arrivals a,a,b"            │   │ declared review purpose             │
   │ the reviewer does NOT       │   └─────────────────┬───────────────────┘
   │ choose between them         │                     ▼
   └─────────────────────────────┘   ┌─ graph satisfied → candidate frozen ┐ ⚙ pb_graph, pb_freeze
                                     │ one canonical contract identity     │
                                     └─────────────────┬───────────────────┘
                                                       ▼
                                     ┌─ aggregate consistency challenge ───┐ ⚙ attempt + gate
                                     │ do the accepted artifacts agree     │ ◆ judgment
                                     │ AS A WHOLE, not one at a time?      │
                                     └─────────────────┬───────────────────┘
                                                       ▼
   ════════ handoff: a fresh coordinator, with none of the above conversation ════════
                                                       ▼
                                     ┌─ authorization ─────────────────────┐ ⚙ pb_execution
                                     │ the guard DERIVES the candidate,    │   authorize
                                     │ checks it has consistency accept-   │   — refuses, and a
                                     │ ance, checks provenance             │   refusal is an answer
                                     └─────────────────┬───────────────────┘
                                                       ▼
                                     ┌─ implementation, bound to that exact candidate ┐ ⚙ contract
                                     └─────────────────┬──────────────────────────────┘   is immutable
                                                       ▼
                                     ┌─ fresh implementation review ───────┐ ◆ judgment
                                     └───────┬─────────────────────┬───────┘
                                     findings│                     │no findings
                                             ▼                     ▼
                                     ┌─ repair ────┐      ┌─ mechanical evidence gate ┐ ⚙ scope,
                                     │ producer    │      │ then the parent accepts   │   hashes,
                                     │ role, same  │      └───────────────────────────┘   review
                                     │ contract    │                                      provenance
                                     └──┬──────────┘
                                        └──► fresh review again (the old one is stale)
```

**Legend.** ⚙ implemented by tools, deterministic. ◆ decided by a person or an agent — Proofbound
records the decision and who was allowed to make it, never the answer. Every step above is
implemented today; *proposed* behaviour is marked as such where it appears in this document.

What the chain caught in this example, mechanically: requirements 2 and 3 conflict at a three-item
witness, proved by enumerating all six dispatch orders. Nothing was authorized, because nothing was
accepted, because the challenge found a real defect — and the guard refuses rather than the harness
merely declining to proceed.

---

## The core concepts

Why each exists, before what it is called.

| The problem | The concept | Where it is defined |
|---|---|---|
| Somebody has to say what they want, and that is not the agent's call | **Owner's goal** — the root authority. External to the ledger, because no task produced it. Its digest is stamped into every contract so a stranger can check it | [execution-and-review §51.3](docs/architecture/proofbound/execution-and-review.md#513-a-proposed-requirements-document-is-an-ordinary-artifact) |
| A goal is not buildable until someone writes down what must become true | **Reviewable requirements** — an ordinary artifact, authored under a contract and challenged like anything else. No special kind, no special role | same |
| Later work must know what earlier work assumed | **Artifacts and dependencies** — content plus the exact dependency identities it was accepted *against* | [artifacts-and-provenance](docs/architecture/proofbound/artifacts-and-provenance.md) |
| An agent needs bounded, unambiguous instructions that cannot move mid-flight | **Task contract** — immutable, hash-verified, names its own acceptance criteria and allowed source changes | [execution-and-review](docs/architecture/proofbound/execution-and-review.md) |
| Work gets retried, repaired and re-reviewed; that history matters | **Attempt** — one launch of one role against one contract. A review is a *later attempt on the same task and same contract*, never a new task | same |
| "Reviewed" is meaningless unless you know what question was asked | **Role** and **review purpose** — purpose is declared by authority in the contract and checked against a closed purpose→role table. A `reviewer` cannot satisfy a task declaring `design-reflection` | [§51](docs/architecture/proofbound/execution-and-review.md#51-what-each-review-purpose-actually-asks) |
| Self-approval is not review | **Review freshness** — a recorded project mutation cannot be accepted without a fresh, independent, non-mutating review attempt. Enforced, not encouraged | same |
| Claims about what changed must be checkable | **Evidence gate** — scope diff, contract hash, lifecycle, review provenance. Objective integrity only | same |
| Accepted work must outlive the run that produced it | **Ledger** — durable record of accepted artifacts, their dependency identities and their review purpose | [artifacts-and-provenance](docs/architecture/proofbound/artifacts-and-provenance.md) |
| A set of individually accepted artifacts is not yet one coherent contract | **Candidate / freeze** — one canonical identity binding content, exact dependencies and review purpose. Excludes which role ran and which attempt it was, so an equivalent fresh re-review does not invent a new contract | [freeze-and-binding](docs/architecture/proofbound/freeze-and-binding.md) |
| A candidate is not permission | **Execution authorization** — a guard that *derives* the candidate from graph and ledger, requires a durable consistency acceptance, and checks provenance. A candidate string written in a contract is a declaration, not an authorization | same |
| Fixing a defect must not preserve the approval the defect had | **Repair** — the producer role repairs under the same immutable contract, and every downstream judgement about the artifact is re-earned by a fresh attempt | [§51.2](docs/architecture/proofbound/execution-and-review.md#512-discovery-downstream-is-repair-not-a-new-workflow) |
| Intent legitimately changes; history must not be rewritten | **Supersession** — a new artifact supersedes an old one, and dependents become `needs-revalidation` through ledger closure. Nothing is edited in place | [core-model](docs/architecture/proofbound/core-model.md), `P9` |
| Done has to mean something | **Acceptance** — recorded by the parent against a qualifying gate, never by the producing agent | [execution-and-review](docs/architecture/proofbound/execution-and-review.md) |

**There are no artifact kinds.** "Proposal", "design" and "specification" are words for what a
document is *for*, not types the system knows about. A kind field was tried and rejected: a taxonomy
attracts behaviour that then depends on it. What is enforced is narrower and more useful — the
declared review purpose must match a role authorized for that purpose, and nothing more is claimed.

**An artifact changing is not the same as the contract requiring more.** If the accepted graph is
`A`, `B → A` and authority later decides it also needs `C`, then `A` and `B` did not become invalid
— nothing about them moved. The *graph* is unsatisfied until `C` is accepted. Equally, `B`'s bytes
may be untouched while the topology is unsatisfied because `B` now depends on `C` and has not been
re-reviewed against it. Conflating the two would make the model unusable, so they stay separate
dimensions.

---

## What is implemented, and what has actually run

**These are five different facts about a capability, not a maturity score.** A thing can be
implemented and never observed; observed once and never repeated; repeated and never compared
against an alternative. Reading the first column as "done" is the error this table exists to
prevent.

"Repeated" here means *the same condition measured more than once* — twelve slots of one
configuration, five trials of one scenario. It does not mean twelve independent demonstrations, and
where a column says "1–2 per case" the denominator is the point, not the numerator.

| Capability | Implemented | Exercised deterministically | Observed with real agents | Repeated | Controlled comparison |
|---|---|---|---|---|---|
| Bounded workers, parent orchestration, immutable contracts | yes (inherited) | yes, canonical suite | yes — evals, MLR series, both authority demos | yes | — |
| Fresh independent review enforced before acceptance | yes (inherited) | yes | yes | yes | — |
| Scope checking, evidence gates, recovery/resume | yes (inherited) | yes | yes | yes | — |
| Attempt deadline actually stopping a live worker | yes | yes | yes — [field check](docs/architecture/proofbound/evidence/lifecycle-field-check.md), 2 trials | 2 trials | — |
| `spec-author` / `spec-reflector`, declared review purpose | yes | yes | yes — demos 1 and 2 | yes | — |
| Canonical artifact identity; ledger; derived validity; provenance | yes | yes | yes — demo-2 recorded `spec.md` | once | — |
| Declared change graph, mechanical graph satisfaction | yes | yes | yes — demo-2 | once | — |
| Freeze: one canonical contract identity | yes | yes | yes — demo-2 froze a candidate | once | — |
| **Aggregate consistency acceptance** (`pb_consistency record`) | yes | yes | **no** — demo-2's consistency attempt ran and found a real defect, so no acceptance was ever recorded | — | — |
| **Execution authorization** (`pb_execution authorize`) | yes | yes — rehearsals and the slice, both paths | **no** | — | — |
| **Candidate-bound implementation → review → acceptance** | yes | yes — fake executor only | **no. Both authority demonstrations stopped before implementation** | — | — |
| **Fresh-context handoff of authority state** | n/a (a procedure) | yes — slice fixtures | **partially**: two read-only recovery probes, and two fresh coordinators that drove the whole continuation against a **stand-in executor**. No live run | 1–2 per case, all against a stand-in | — |
| **The guard that makes the launch policy govern launches** | yes | yes — ceiling, budget, repair allowance, unreconciled slot, pre-executor evidence | **no** | — | — |
| **External check of the delivered artifact** | yes | yes — 3 sound implementations accepted, 12 defective rejected | **no** | — | — |
| Per-execution profile — calls, tokens, tools, time, context by origin | yes | yes | yes | yes | — |
| Evaluation of the harness: scenarios, trials, blind grading | yes | yes | yes — V1–V3 | yes | — |
| Independence control (`P12`): withhold the author's reasoning | yes | yes | yes — V4 | yes | **yes**, under V4's scenarios, model and grader — withholding produced *higher* observed completeness there, which is a result about that configuration |
| Comparative pipeline evaluation, paired and interleaved | yes | yes | yes — MLR `q1` 12/12 valid; `eventbus-b1` 12/12 valid | yes | **yes**, for one fixture and one question |
| System-craft measurement | yes | yes | yes — V5–V7 | yes | instrument **not reliable**: reflector conclusion moves on 43% of identical repeats |
| Per-role provider/model routing | **no** — architecture protects it | — | — | — | — |
| Decision provenance, cumulative coherence auditing | **no** — direction only | — | — | — | — |

**The load-bearing gap, stated plainly.** The authority chain's *second half* has never run with a
real agent. Both demonstrations stopped at genuine review findings — which is the chain working, and
is a result about **refusal**. A successful rejection and a successful continuation are different
capabilities, and only one of them has evidence. Everything about implementation, review and
acceptance under a frozen candidate has been exercised only with a fake executor.

**Neither demonstration is a controlled observation.** Both amended frozen rules mid-run; demo-2's
departures `D1` and `D4` resolved a rule contradiction in favour of continuing and raised a launch
ceiling mid-run. The observations survive — a real reviewer found a real defect, twice — but any
claim that a demonstration was a *conforming execution of its frozen protocol* does not. The
adjudication is in
[the demo-2 audit](docs/architecture/proofbound/evidence/authority-workflow-demo-2-audit.md).

**What the MLR findings are, narrowly.** The modularity series asks: for a change whose
responsibility lies outside a module, does reading that module's implementation contribute to
getting the change right? It has run twelve valid trajectories on one fixture with one model and
replicated its core phenomenon. That is not evidence that Proofbound improves engineering quality,
nor that bounded context is generally better, nor that any of it transfers to another repository.

---

## What survives, and what a fresh coordinator must reconstruct

Three tiers, and confusing them is how a long run loses its authority.

| Tier | What it holds | Lifetime |
|---|---|---|
| **Durable, in Git** | Requirements and other accepted artifacts; the ledger's record of what was accepted, against which dependency identities, under which review purpose; freezes; declared graphs; protocols and reports | Permanent, versioned, reviewable |
| **Execution evidence, outside Git** | Run trees: attempts, prompts, worker reports, gates, scope diffs, terminal records, session databases — **and the task contracts that bind work to a candidate**. Large, machine-specific, in `DeepSeekAndDestroy/` or a workspace path | Until deleted. **Deletion is expected** |
| **Working notes and agent context** | Conversations, summaries, compaction checkpoints, an agent's reasoning | Gone when the session ends. Never authority |

**When execution evidence is gone**, the durable record still says what was accepted. What is lost
is the ability to *re-verify the execution*, and that is reported as `provenance: unavailable` —
explicitly neither "fine" nor "broken".

**One limit worth stating precisely**, because it is easy to over-read the word durable: *execution
binding is not durable provenance*. Task contracts and acceptance live inside the run tree, so once
that tree is deleted no project file records that an accepted implementation task was governed by a
particular candidate. The ledger's durability is about **artifacts** — content, dependencies and
review purpose — not about which contract authorised which attempt. A recovery probe confirmed the distinction behaves as
documented: dropping the run root turns provenance from `verified` to `unavailable` while validity
stays `valid`, so `verified` is earned rather than assumed.

**A fresh coordinator reconstructs nothing from history.** It reads live state first, and derives:
which candidate the project currently produces (from graph + ledger, not from a string in a
contract); whether that candidate has a durable consistency acceptance; the provenance state; where
the root authority lives and whether its digest still matches what contracts carry; and what the
next permitted action is. Session history is cold continuity, not a reason to re-derive the run.

**What "missing evidence" means** depends on what is missing. A missing consistency record means
*not authorized* — the guard refuses. A missing run tree means *unverifiable execution*, which does
not revoke an acceptance already recorded. Missing historical execution artifacts constrain
verification; they do not by themselves invalidate accepted repository content.

---

## Quick start

**Prerequisites.** Python **3.10 or newer**, standard library only — no third-party packages and no
virtual environment. CI runs the suite on **3.10 and 3.14**, which brackets the supported range;
versions in between are expected to work and are not continuously verified.

> On macOS `/usr/bin/python3` may still be 3.9. Check with `python3 --version`. Record
> `sys.executable` rather than a nominal path when identity matters: this repository has a
> demonstration that recorded `/usr/bin/python3` at a version that binary is not.

**Platforms.** Developed and exercised on macOS (arm64) and Linux in CI. The worker transport is an
external CLI; nothing here is Windows-tested.

### Installing it

Proofbound runs as a **skill** inside a parent harness rather than as an installed package. There
are two directories, and operational documents refer to them constantly:

| | |
|---|---|
| `<skill>` | **This repository, wherever you put it.** Operational docs write `python3 <skill>/scripts/…`; substitute the checkout path. Nothing is copied into your project except the adapter fragment below |
| `<project>` | The repository whose code the agents will change. Run trees appear under `<project>/DeepSeekAndDestroy/` |

Clone this repository, then install the adapter for your parent harness into the project you want
to work on — once per project:

```bash
python3 <skill>/scripts/install_harness_adapter.py --harness claude-code --project-root <project>
```

`--harness` accepts `codex`, `claude-code`, `opencode`, `kilo` or `auto`. It writes a project-local
hook or plugin fragment (compaction and, for Claude Code, async re-wake) whose bodies are the
checked-in assets under [`adapters/`](adapters/README.md); re-run it only when the hook definition
itself changes. Some harnesses also discover the skill by placing or symlinking the checkout in
their own skills directory — that is harness-specific and outside this repository.

The default technical worker backend is external OpenCode using `opencode-go/deepseek-v4-flash`. No
configuration file is required for the default profile; [`CONFIG.example.md`](CONFIG.example.md)
shows optional overrides. **Do not store credentials in Proofbound configuration** — they live in
the worker harness's own configuration, and nothing here reads, stores or prints them.

### Run this first — no credentials, no model, no cost

```bash
python3 -m unittest discover -s tests -t .
```

The canonical suite: 1,147 tests, **about 8 minutes**, and exactly what CI runs. Serial by design —
the tests share host state, so do not reach for a parallel runner. It should end `OK (skipped=1)`;
the skip is environment-dependent.

Then exercise the authority chain end to end without a provider. This builds disposable projects,
drives the real scripts with a fake executor, and reports four cases:

```bash
python3 evals/authority_slice/pb_slice.py validate
python3 evals/authority_slice/pb_slice.py replay
```

More credential-free routes are listed in the [evaluation guide](evals/README.md#what-runs-with-no-credentials-at-all).

### Driving a real run

Hand the parent harness a plan:

```text
Use Proofbound to execute the authoritative plan at <path>.
Continue autonomously until complete or genuinely human-blocked.
```

Attempt orchestration is mechanical. **These commands launch model work and spend money:**

```bash
python3 scripts/dsd_attempt.py launch --run-root <run> --phase-id <phase> --task-id <task> --role <role> [--detach]
python3 scripts/dsd_attempt.py wait   --run-root <run> --phase-id <phase> --task-id <task>
python3 scripts/dsd_attempt.py gate   --run-root <run> --phase-id <phase> --task-id <task> [--surface]
python3 scripts/dsd_state.py accept-task --run-root <run> --phase-id <phase> --task-id <task> --evidence-gate <gate.json>
```

`gate` and `accept-task` spend nothing themselves; `launch` and `wait` drive a real worker.

Proofbound's own artifact layer — all deterministic, none of it invokes a model:

```bash
python3 scripts/pb_ledger.py record   --run-root <run> --phase-id <phase> --task-id <task> --artifact <file> --ledger <ledger.json>
python3 scripts/pb_ledger.py validate --ledger <ledger.json> --project-root <project> [--run-root <run>]
python3 scripts/pb_graph.py  validate --graph <graph.json> --ledger <ledger.json> --project-root <project>
python3 scripts/pb_freeze.py create   --graph <graph.json> --ledger <ledger.json> --project-root <project> --into <freezes>
python3 scripts/pb_freeze.py compare  <freeze.json> --graph <graph.json> --ledger <ledger.json> --project-root <project>
python3 scripts/pb_consistency.py record --run-root <run> --phase-id <phase> --task-id <task> --freeze <freeze.json> --into <consistency>
python3 scripts/pb_execution.py authorize --graph <graph.json> --ledger <ledger.json> --project-root <project> --consistency <consistency> --contract <contract.md> [--run-root <run>]
```

Angle brackets are values you supply, and every line above is complete as written. **Elsewhere in
this repository an ellipsis in a command means an argument list to fill in, never a runnable
line** — `SKILL.md`, `PROMPTS.md` and the harness adapter documents all use that shorthand for the
orchestrator, which already knows the arguments. A schematic line is not a runnable command, and
this repository has been burned by the difference, so the runnable ones are written out here.

> The public project is **Proofbound**. Inherited paths and commands keep the `dsd_` prefix and the
> `DeepSeekAndDestroy/` workspace directory: these are compatibility-sensitive wire identifiers that
> installed projects and historical runs depend on, not branding. Renaming them is a separate
> migration milestone with its own evidence. New Proofbound-native tooling uses the `pb_` prefix.

---

## Where human judgment is required

Proofbound does not remove people from the loop. It moves them to the decisions that are actually
theirs, and it records what they decided. **Each of these is a product cost worth measuring**, not a
rough edge to hide.

| Decision | Why it cannot be delegated |
|---|---|
| **Stating and approving the goal** | The root authority. Somewhere a person says what they want; demanding a reviewed parent for every human decision is an infinite regress, not a guarantee |
| **Adjudicating a finding** | A reviewer reports; someone with authority decides whether it is genuine. In demo-2 a finding was correct while its decisive exhibit was wrong, and taking the verdict on trust would have accepted the right conclusion for an invalid reason |
| **Ruling on a conflict in the requirements** | A challenge may name a contradiction. Choosing which requirement survives is the owner's, and a reviewer that chooses has replaced the owner |
| **Deciding a trade-off** | Cheaper and less correct is a trade for a person to weigh, never an improvement a number can declare |
| **Spending money** | Every paid launch is admitted against a declared budget, and unknown expenditure blocks further launches |
| **Adopting a harness change** | A measurement is evidence. Nothing adopts a change because a number moved |

The interventions a run required — coordinator decisions, adjudications, context reconstruction —
belong in its result. A configuration that needs constant babysitting is not cheaper because its
token count is lower.

---

## Built for long runs: context, drift, and neutrality

**Context is an engineering resource, not a container to fill.** A large window does not make
context free: everything a worker is given is paid for in tokens, in latency, in money, and — the
part that is easiest to forget — in attention, because material that is present but irrelevant is
material the model may reason from. Mechanically, a worker receives only:

```text
WORKER_RULES.md                 run facts
worker/COMMON.md                universal worker behavior
worker/roles/<role>/SKILL.md    exactly one specialist role
task contract                   exact task semantics
PROOF-PATTERNS.md               only when that task names it
```

The target is **not** "less context" — it is the smallest context that still supports correct
reasoning for this role and this task. A reviewer starved of the authority it is reviewing against
will miss real problems, which is a worse failure than a large prompt. Where Proofbound has an
opinion about a context policy, that opinion is something to **measure**, which is what the
comparative evaluation machinery exists for. The same discipline governs this documentation: the
architecture is split with a routing map so a bounded task reads what it needs. There is
[evidence that repository context files can fail to help and still cost](https://arxiv.org/abs/2602.11988),
which is a reason to test documentation access rather than to stop writing documentation.

**Two different things go wrong over a long run, and they need different defenses.** *Context
degradation* — the rationale behind a decision becomes unavailable or hard to retrieve — is
addressed today by durable artifacts, explicit contracts, bounded worker context and fresh
reviewers. *Decision compounding* — each local decision changes the environment the next one is made
in, so a sequence of locally reasonable adaptations drifts a system away from the architecture
anyone chose — is the harder problem and is **architecture, not a shipped feature**: explicit
decisions with recorded scope, immutable baselines, and cumulative coherence review. See
[long-running-autonomy.md](docs/architecture/proofbound/long-running-autonomy.md).

> Local adaptation should not silently become global policy.

> Agents should be able to accumulate knowledge without silently accumulating doctrine.

**`role` ≠ `provider` ≠ `model` ≠ `harness`.** `spec-reflector` is a *role* — responsibilities and a
review purpose. Which model executes it is a runtime choice, kept separate so that different roles
can later run on different providers; a reviewer independent of the implementer's model is the
cheapest real form of reviewer independence. Per-role routing is **not implemented yet**, and
provenance records the *role*, never the model: model identity belongs to execution evidence, not to
durable engineering meaning.

---

## How evaluation improves Proofbound

Three questions that are easy to conflate and must not be:

| | What it establishes |
|---|---|
| **Tests of the harness** | The controls enforce their declared rules. Deterministic, credential-free, in the canonical suite |
| **Evaluations of agent behaviour** | Whether a fresh reviewer detects a planted contradiction; whether a coordinator recovers state correctly. Needs real models, repeats, blind grading, and an instrument validated on its own |
| **Evidence about the software produced** | Whether the artifact that was asked for exists and works. A favourable test tally is not this |

The operational guide — entry points, what each spends, the six-step process, what to report, and
what runs without credentials — is **[evals/README.md](evals/README.md)**.

Two rules from that programme are general enough to state here. **Correctness gates everything
else**: resource figures are interpretable only once the property they were supposed to preserve has
been checked and held. And **do not interpret a difference smaller than the instrument's own
variation under identical conditions** — reliability comes before validity, and consistency is never
evidence of correctness.

**The instrument is part of the experiment.** A pilot once ran cleanly — six valid executions, no
harness failure, a clear result — and was still uninterpretable, because the correctness oracle
asserted an internal function's signature while claiming to observe product behaviour, and the
context telemetry scored a package's own `help()` output as unclassified. Neither would have been
found by running the agents more carefully.

---

## Direction, and the evidence that would justify it

Ordered by what would most change what Proofbound can claim. **Each is a hypothesis with a gate, not
a roadmap commitment.**

1. **A reliable valid path through authority recovery and delivery.** *Gate:* a fresh coordinator
   recovers authority state and carries one bound implementation to acceptance, repeatedly, with
   correct refusals on mutated states. The protocol is **frozen** in
   [next-live-experiment.md](evals/authority_slice/next-live-experiment.md) — policy enforced by a
   launch guard, an external check on the delivered artifact, a measured information boundary — and
   two fresh coordinators have driven the whole continuation against a stand-in executor. It has
   not run against a provider, so the chain's second half remains untested with real agents.
2. **A second change to already-accepted software.** *Gate:* supersession, `needs-revalidation`
   closure and re-review behave as designed when intent moves — measured, not rehearsed. This is
   where decision compounding first becomes observable.
3. **Multi-artifact, multi-change coherence on a real repository.** *Gate:* an aggregate consistency
   challenge over a candidate with several members that catches a real cross-artifact contradiction.
   Every freeze to date has had exactly **one** member, so aggregate coherence is currently a
   narrower claim than its name suggests.
4. **Proportionate review effort.** *Hypothesis:* earlier challenge finds more defects per unit of
   cost. *Gate:* a pre-registered comparison with declared baseline, repeats, guardrails and cost.
   A paid intent reviewer moves detection earlier; it does not make detection free.
5. **Qualified interchangeable executors and review tools.** *Gate:* per-role routing implemented,
   plus evidence that a reviewer on a different model finds defects the implementer's model misses.
   Reviewer independence today is independence of *context and input*, not of architecture or
   training.

Milestone status and acceptance criteria:
[implementation plan](docs/architecture/specification-reflection-harness-implementation-plan.md).

### External ideas, evaluated at their actual boundary

- **Deterministic context preparation** is genuinely useful for facts: changed paths, hashes, rule
  matches, dependency edges, scheduling, comment coordinates. That the selected context is
  *semantically sufficient* remains a hypothesis — so record omissions and support justified
  exploration beyond the diff rather than treating a computed slice as complete.
- **Challenging a finding's evidence** would have helped here: demo-2's reversed-clock exhibit was
  invalid while its finding was true. An invalid exhibit weakens support; it does not refute the
  concern. Keep unknown, contradicted and corroborated findings distinct.
- **More review rounds or more agents must earn their cost.** "No new findings" is not a certificate
  that no defects remain. Measure marginal discovery, false findings, missed risks and coordination
  cost.
- **Durable memory** should preserve accepted facts and their provenance; compressed context stays a
  derived aid. Plugin outputs and execution transcripts do not acquire engineering authority by
  being persisted.
- **OpenCodeReview** (as a review producer) and **DeepSeek Harness** (as an execution adapter) are
  evaluable when a concrete need justifies them, qualifying their information, cancellation,
  evidence and accounting boundaries. Neither is required, and a reflection filter that drops
  comments contradicted by visible evidence has a survival condition narrower than correctness.

Primary research that motivates these experiments — and does not establish their conclusions:
[demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents),
[harness design for long-running apps](https://www.anthropic.com/engineering/harness-design-long-running-apps),
[FixedBench](https://arxiv.org/html/2605.07769v1) (abstention can suppress needed repairs, so
measure appropriate continuation too), [Building to the Test](https://github.com/yanuoma/b2t) (high
oracle scores coexisting with failure to deliver the requested library — check the artifact, not the
tally), [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988) (repository context files did not
generally improve success and increased cost — which is a reason to *test* documentation access and
instruction burden, not to withhold documentation), and the
[OpenCodeReview paper](https://arxiv.org/html/2608.09290v1).

---

## Reading routes

**A new contributor.** [CONTRIBUTING.md](CONTRIBUTING.md) → [AGENTS.md](AGENTS.md) (policy for
coding agents, including Git authorship) → the architecture entry point's "Read this if…" table at
[docs/architecture/proofbound/README.md](docs/architecture/proofbound/README.md), and read only the
rows your task matches.

**A fresh coordinator resuming a run.** [SKILL.md](SKILL.md) first — resolve run identity, read live
state, execute the mechanical next action. [WORKSPACE.md](WORKSPACE.md) only on an abnormal
lifecycle symptom; [OPENCODE.md](OPENCODE.md) only on a transport symptom;
[COMPACTION.md](COMPACTION.md) only when checkpoint state requires it. Do **not** read this README
to resume a run — it teaches, and it is not the operational surface.

**An evaluator.** [evals/README.md](evals/README.md) → the design documents it links →
[evals/authority_slice/](evals/authority_slice/README.md) for the newest cases.

**Anyone asking "why is this rule like this?"**
[evidence/implementation-findings.md](docs/architecture/proofbound/evidence/implementation-findings.md).

The architecture is a routed corpus, not one document. **The README teaches; those documents
define. Where they disagree, they win.**

| Document | Covers |
|---|---|
| [core-model.md](docs/architecture/proofbound/core-model.md) | Truth layers, the three orthogonal dimensions of an artifact, principles `P1`–`P13`, evidence authority |
| [execution-and-review.md](docs/architecture/proofbound/execution-and-review.md) | Mechanical invariants `I1`–`I15`, attempts, review purposes and what each asks, the parent's boundary |
| [artifacts-and-provenance.md](docs/architecture/proofbound/artifacts-and-provenance.md) | Artifact identity, the ledger, derived validity, the change graph |
| [freeze-and-binding.md](docs/architecture/proofbound/freeze-and-binding.md) | Freeze schema and identity, validation layers, what a freeze does *not* authorize |
| [long-running-autonomy.md](docs/architecture/proofbound/long-running-autonomy.md) | Drift, decision provenance, coherence auditing, threats `T1`–`T10` |
| [evaluation.md](docs/architecture/proofbound/evaluation.md) · [evaluation-comparison.md](docs/architecture/proofbound/evaluation-comparison.md) · [system-craft.md](docs/architecture/proofbound/system-craft.md) · [context-economy.md](docs/architecture/proofbound/context-economy.md) | Measuring one run; discriminating between systems; whether a system stays changeable; context as a resource |

---

## Glossary

**Artifact** — a versioned file whose content identity, dependencies and review purpose are
recorded. **Attempt** — one launch of one role against one contract. **Candidate** — a frozen
contract identity derived from a satisfied graph. **Contract** — immutable task definition.
**Evidence gate** — deterministic integrity check over an attempt. **Freeze** — the act producing a
candidate. **Gate-clean** — safe to interpret, not "passed". **Ledger** — durable record of accepted
artifacts. **Parent / coordinator** — the premium agent holding authority; never a worker.
**Provenance** — `verified` / `unavailable` / `contradicted`, orthogonal to validity. **Review
purpose** — the declared question a review answered. **Role** — one worker doctrine. **Run root** —
where execution evidence lives. **Scope diff** — what actually changed. **Supersession** — replacing
accepted intent without editing history. **Validity** — `valid` / `invalid` / `needs-revalidation`,
derived and transitive. **Worker** — a bounded specialist agent with one role and one contract.

Worker roles: **Spec Author**, **Spec Reflector**, **Phase Surveyor**, **Discovery**,
**Implementer**, **Fixer**, **Reviewer**, **Verification**, **Recovery**, **Phase Auditor**,
**Evidence Clerk** (read-only interpretation of existing evidence; it cannot invent proof, rerun
verification, repair code, waive integrity failures, or approve work). Worker reports are **natural
language**, not a wire protocol: no verdict line, no proof matrix, no machine-parseable test
arithmetic. A report is evidence; if proof is genuinely absent, it stays absent.

---

## Current limitations

1. **The authority chain's second half has never run with a real agent** — no recorded consistency
   acceptance, no live authorization, no candidate-bound implementation, no fresh-context
   continuation.
2. **Every freeze so far has had exactly one member**, so "aggregate coherence" is currently a
   judgement about one artifact against intent.
3. **Neither authority demonstration conformed to its own frozen protocol**; both amended rules
   mid-run.
4. **Reviewer independence is contextual, not architectural** — the same model in different roles
   with different inputs. Running a reviewer on a *different* model would change the context, not
   establish independence: two models sharing training data, tokenisation or failure modes are not
   demonstrably independent, and nothing here has measured that.
5. **The craft instrument is not reliable enough to interpret**, and its successor comparison has
   not been run.
6. **Per-role routing is not implemented.**
7. **Cost accounting has five distinct categories** — measured usage, derived cost, estimated
   reserve, justified bound, provider-confirmed billing — and the last is never observed here.
8. **Evaluation cases live in the same repository they evaluate**, so a probe can read an answer
   instead of deriving it. Currently mitigated evidentially, by requiring command-by-command
   reporting, rather than physically.
9. **No Windows support**, and the worker transport depends on an external CLI whose behaviour has
   already produced one silent attribution defect.

---

## Provenance and license

Proofbound was bootstrapped from **DeepSeek-and-Destroy** (MIT, © 2026 FrozenPepper), inheriting
`v15.5.5`. From DSD it keeps the execution and review mechanics that already worked: bounded
specialist workers, parent orchestration that routes rather than re-reviews, fresh independent
reviewers, the repair/re-review loop, immutable task contracts, scope checking, objective integrity
gates, and recovery/resume behaviour.

Proofbound is becoming a distinct system focused on what DSD does not address: reviewable
requirements before implementation, durable artifacts with content-addressed provenance, explicit
review purpose, dependency graphs, contract freeze and binding, architectural coherence over long
runs, and provider neutrality. It is **not affiliated with or endorsed by** the DeepSeek-and-Destroy
project.

MIT — see [`LICENSE`](LICENSE), preserved unchanged from upstream.
