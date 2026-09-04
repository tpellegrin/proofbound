# Proofbound

**From engineering intent to verified implementation.**

Proofbound is an agent orchestration harness for engineering work where the specification, the review
boundary, the execution contract, and the acceptance evidence matter as much as the generated code.

Instead of asking one agent to interpret a request, implement it, and then decide it is done, Proofbound
separates those responsibilities. Engineering intent is made explicit and independently challenged
*before* implementation. Implementation runs under bounded task contracts. Fresh reviewers challenge the
result. Deterministic checks verify facts — what changed, what the artifact hashes are, whether a
dependency moved, whether a qualifying independent review actually happened.

**Specify. Challenge. Execute. Prove.**

---

## Why Proofbound?

Coding agents are good at producing code. Producing code was never the hard part.

The hard part is keeping five things aligned: what you intended, what the agent understood, what it
actually changed, what was independently reviewed, and what the evidence really proves. A conventional
agent loop collapses all five into one conversation and one opinion — the agent's own.

Over a long run, that gets worse in specific ways:

- an agent works around an incident locally, and the workaround quietly becomes the house style;
- the reasoning behind a decision decays out of context, so later work contradicts it without knowing;
- the agent that wrote the code also reviews it, carrying every assumption that produced it;
- a task "looks done" without anything mechanically establishing that it is;
- a hundred individually reasonable changes add up to an architecture nobody chose.

Proofbound exists to make those relationships explicit rather than implicit.

> Engineering intent should be specified, challenged, versioned, and recorded — not described once in a
> prompt and then forgotten.

> An agent does not get to declare itself done. Acceptance is bound to evidence.

### A concrete example

Suppose you ask an agent to change how authentication works.

A conventional workflow goes from the request straight to a diff. Whether the agent understood the
constraint, whether it considered the session-expiry edge case, and whether "done" means anything are all
left to the same agent that wrote the code.

With Proofbound the request first becomes an explicit written specification. A **fresh** reflector — one
that never saw the authoring reasoning — challenges it: is the problem framed right, are the assumptions
stated, does this contradict something already accepted? What gets accepted is recorded with its exact
content hash and what it depended on. Implementation then happens under a bounded task contract, a
different reviewer checks the code, and mechanical gates verify that only the declared files changed,
that the contract was not edited mid-flight, and that a qualifying independent review actually exists.

Nothing here makes the design correct. It makes the design *visible, attributable, and challengeable* —
and it stops "done" from being a claim the author gets to make alone.

---

## How it works

```text
        engineering intent
                │
                ▼
    proposal / design / specification         ← written as ordinary repo files
                │
                ▼
       independent reflection                 ← a fresh agent challenges it before any code
                │
                ▼
   accepted, content-addressed record         ← what was accepted, and what it depended on
                │
                ▼
      implementation task contract            ← immutable, bounded, hash-verified
                │
                ▼
        fresh implementation review
                │
         ┌──────┴──────┐
      findings      accepted
         │              │
         ▼              ▼
       fixer     mechanical evidence gate
         │        scope · hashes · review provenance
         └──► fresh review
```

The loop is deliberately boring: **mutation → fresh independent review → acceptance**. What Proofbound
adds is that the same loop now applies *before* implementation, to the specification itself.

---

## The core idea

A typical agent flow:

```text
prompt → generate code → the agent says it is done
```

Proofbound:

```text
intent → explicit artifact → independent challenge → bounded contract
       → implementation → independent review → mechanical evidence
```

Two rules carry most of the weight:

1. **The agent that produced a change is not the sole authority on whether it satisfies the contract.**
2. **Completion comes from independently reviewed work plus mechanical evidence, not from confidence.**

---

## What makes it different

### Reflection before implementation, not just review after

Proofbound separates two reviews that answer genuinely different questions.

| | Asks |
|---|---|
| **Reflection** (before code, role `spec-reflector`) | Is the problem framed correctly? Are assumptions explicit? Does the design satisfy the proposal? Do the requirements contradict each other? |
| **Review** (after code, role `reviewer`) | Does the implementation satisfy the accepted contract? Is it correct? Is the evidence adequate? Did it stay inside its declared scope? |

They share the same mechanical plumbing and are still different jobs. Which one applies is *declared* in
the task contract as a **review purpose**, never guessed from a filename. A `reviewer` cannot satisfy a
task that declares `design-reflection`, and the check is a table lookup, not an interpretation.

### Review comes from a fresh context

The agent that authored something carries its own assumptions, its own justification, and its own reading
of anything ambiguous. Asking it to review its own work asks it to doubt reasoning it just found
convincing.

A fresh reviewer starts from the contract and the evidence instead. This does not guarantee correctness —
nothing here does — but it is a materially stronger review boundary than self-approval, and Proofbound
enforces it mechanically: a recorded project mutation cannot be accepted without a fresh, independent,
non-mutating review attempt.

### Code verifies facts; agents judge meaning

> **Proofbound uses code to verify facts and agents to judge meaning.**

Deterministic checks answer questions with exact answers:

- did the expected file change, and did anything undeclared change?
- does the artifact still hash to what was accepted?
- did something it depended on move?
- is a required artifact missing from the declared graph?
- does the task contract still match its immutable hash?
- did a qualifying fresh independent review actually happen?

Agents and humans answer the rest: is this design any good, is the specification sensible, is this
trade-off acceptable, is the architecture coherent. **No Python in this repository decides whether
engineering is good**, and a clean integrity gate means *safe to interpret*, never *the engineering
passed*.

### Durable artifacts instead of transient context

The thinking lives in version-controlled files — proposals, designs, specifications, task definitions,
graph declarations — not in a chat window. Alongside them, Proofbound records for each accepted artifact:

- the exact content that was accepted;
- the exact dependency identities it was accepted *against*;
- the declared semantic review purpose that applied.

Execution evidence (worker reports, gates, run trees) is large and eventually deleted. When it goes, the
durable record still says what was accepted; only the ability to *re-verify the execution* is lost, and
that is reported honestly as unavailable rather than silently treated as fine — or as broken.

### An artifact changing is not the same as the contract requiring more

A distinctive and easily-missed separation. Suppose the accepted graph is:

```text
A
B → A
```

and authority later decides it also needs `C`:

```text
A
B → A
C → A
```

`A` and `B` did not suddenly become invalid. Nothing about them moved. The *graph* is now unsatisfied
because `C` has not been accepted yet. Equally, if the graph later requires `B` to depend on `C`, `B`'s
bytes may be untouched while the topology is unsatisfied until `B` is re-reviewed against its new
dependency set.

Conflating "this artifact changed" with "the contract now requires more" would make the model unusable,
so Proofbound keeps them as separate dimensions. Details in
[artifacts-and-provenance.md](docs/architecture/proofbound/artifacts-and-provenance.md).

---

## What is implemented today

Proofbound is under active development. This table reflects the current checkout, not intent.

| Capability | Status |
|---|---|
| Bounded specialist workers, parent orchestration, immutable task contracts | **Implemented** (inherited) |
| Fresh independent review enforced before acceptance | **Implemented** (inherited) |
| Scope checking, evidence gates, recovery and resume | **Implemented** (inherited) |
| Historical protocol snapshots verified under the semantics they recorded | **Implemented** |
| `spec-author` and `spec-reflector` roles — reflection as an ordinary reviewed mutation | **Implemented** |
| Declared review purpose, enforced against a closed purpose→role table | **Implemented** |
| Canonical text artifact identity (stable across platforms and checkouts) | **Implemented** |
| Durable ledger of accepted artifacts, dependencies and review purpose | **Implemented** |
| Derived artifact validity (`valid` / `invalid` / `needs-revalidation`), transitive | **Implemented** |
| Provenance status (`verified` / `unavailable` / `contradicted`), orthogonal to validity | **Implemented** |
| Declared exact change graph and mechanical graph satisfaction | **Implemented** |
| Freeze: one canonical engineering-contract identity | **Implemented** (M2C-A) |
| Aggregate consistency reflection over a whole contract candidate | **Planned** (M2C-B) |
| Binding implementation tasks to an exact frozen contract | **Planned** (M2C-C) |
| Architectural decision provenance and applicability | **Planned** |
| Cumulative coherence auditing | **Planned** |
| Per-role provider/model routing | **Planned** |
| Context-economy telemetry and refactoring-economics experiments | **Research track** |
| Migration of inherited `dsd_*` internal names | **Planned, separate milestone** |

**Freeze, precisely.** A freeze reduces a satisfied graph and its accepted records to one canonical
identity binding each artifact's content, its exact dependency identities, and its review purpose. It
deliberately excludes which reviewer role ran, which gate produced it, and which attempt it was — so an
equivalent fresh re-review does not invent a new contract, while a changed dependency set does change it
even when the bytes are identical.

A freeze is a **durable engineering-contract candidate**. It is not yet an authorization to execute:
aggregate coherence review and task-to-freeze binding are subsequent milestones. Proofbound is building
toward binding downstream execution to an exact frozen contract; today the identity layer exists and the
binding layer does not.

---

## Quick start

Proofbound runs as a skill inside a premium parent harness — Codex, Claude Code, OpenCode, Kilo Code, or
comparable. The default technical worker backend is external OpenCode using
`opencode-go/deepseek-v4-flash`.

Copy the repository directory into the skills directory your parent harness uses. First-class adapters
for Codex, Claude Code, OpenCode and Kilo Code are included. No configuration file is required for the
default worker profile; [`CONFIG.example.md`](CONFIG.example.md) shows optional overrides. **Do not store
credentials in Proofbound configuration.**

Then hand the parent a plan:

```text
Use Proofbound to execute the authoritative plan at <path>.
Continue autonomously until complete or genuinely human-blocked.
```

For long runs, exact state and evidence are preserved along with a single `next_action`. A fresh parent
reads live state first and executes a mechanical next action immediately; session history is cold
continuity, not a reason to reconstruct the run.

### Commands

Attempt orchestration is mechanical:

```bash
python3 scripts/dsd_attempt.py launch  …     # reserve, launch, bind an attempt
python3 scripts/dsd_attempt.py wait    …     # detached workers only
python3 scripts/dsd_attempt.py gate    …     # objective integrity only
python3 scripts/dsd_state.py   accept-task … # record acceptance
```

Proofbound's own artifact layer:

```bash
python3 scripts/pb_ledger.py record   …   # record an accepted artifact (parent-owned)
python3 scripts/pb_ledger.py validate …   # derive artifact validity and provenance
python3 scripts/pb_ledger.py withdraw …   # remove an accepted record
python3 scripts/pb_graph.py  validate …   # check a declared graph against accepted records
python3 scripts/pb_freeze.py create   …   # derive a contract identity from a satisfied graph
python3 scripts/pb_freeze.py validate …   # interpret a freeze from the file alone
python3 scripts/pb_freeze.py compare  …   # does the project still produce this freeze?
```

> The public project is **Proofbound**. Some inherited paths and commands keep the `dsd_` prefix and the
> `DeepSeekAndDestroy/` workspace directory: these are compatibility-sensitive wire identifiers that
> installed projects and historical runs depend on, not branding. Renaming them is a separate migration
> milestone with its own evidence. New Proofbound-native tooling uses the `pb_` prefix.

Python **3.10 or newer**, standard library only — no third-party packages and no virtual environment.
Tests: `python3 -m unittest discover -s tests -t .`

---

## Roles

Each worker gets exactly one role, one task contract, and nothing else.

- **Spec Author** — writes one specification artifact.
- **Spec Reflector** — fresh, read-only challenge to a specification artifact before implementation.
- **Phase Surveyor** — measures current state before decomposition.
- **Discovery** — traces one unfamiliar subsystem and writes a durable construction brief.
- **Implementer** — builds one bounded change.
- **Fixer** — repairs explicit supplied findings.
- **Reviewer** — fresh adversarial read-only review of implementation.
- **Verification** — establishes one technical predicate; read-only unless the contract grants writes.
- **Recovery** — read-only forensic disposition of suspect interrupted changes.
- **Phase Auditor** — fresh whole-phase audit against frozen phase evidence.
- **Evidence Clerk** — read-only interpretation and compression of evidence that already exists. It
  cannot invent proof, rerun verification, repair code, waive integrity failures, or approve work.

Worker reports are **natural language**, not a wire protocol. No `Verdict: PASS` line, no proof matrix,
no machine-parseable test arithmetic. A report is evidence; if proof is genuinely absent, it stays absent.

---

## Context economy

Workers receive only what their task needs:

```text
WORKER_RULES.md                 run facts
worker/COMMON.md                universal worker behavior
worker/roles/<role>/SKILL.md    exactly one specialist role
task contract                   exact task semantics
PROOF-PATTERNS.md               only when that task names it
```

The same discipline applies to the architecture documentation itself: it is split into focused documents
with a routing map, so a bounded task reads what it needs rather than the whole corpus.

---

## Designed for long-running agent work

Two different things go wrong over a long autonomous run, and they need different defenses.

**Context degradation** — the rationale behind a decision becomes unavailable, compressed, or simply hard
to retrieve. Proofbound addresses this today through durable artifacts, explicit contracts, bounded
worker context, and fresh reviewers.

**Decision compounding** — each local decision changes the environment the next one is made in. Even with
perfect memory, a sequence of locally reasonable adaptations can drift a system away from the
architecture anyone chose. This is the harder problem, and Proofbound is *being designed* to address it
through explicit architectural decisions with recorded scope, immutable baselines, mechanical invariants
where they fit, and cumulative coherence review. Those are architecture, not shipped features.

Two principles guide that work:

> Local adaptation should not silently become global policy.

> Agents should be able to accumulate knowledge without silently accumulating doctrine.

See [long-running-autonomy.md](docs/architecture/proofbound/long-running-autonomy.md).

---

## Provider and model neutrality

> `role` ≠ `provider` ≠ `model` ≠ `harness`

`spec-reflector` is a **role** — a set of responsibilities and a review purpose. Which model or provider
executes it is a runtime choice. The architecture keeps them separate specifically so that different
roles can later run on different providers — a reviewer independent of the implementer's model is the
cheapest real form of reviewer independence.

Per-role routing is **not implemented yet**; it is an architectural requirement the design protects. Note
also that provenance records the *role*, never the model or provider: model identity belongs to execution
evidence, not to durable engineering meaning.

---

## What "proof" means here

Proofbound does **not** formally prove software correctness, and the name is not a claim that it does.

"Proof" here means deterministic, checkable evidence:

- artifact content identity and dependency identity;
- scope validation — what changed, and whether anything undeclared did;
- immutable contract and reservation hashes;
- the existence of a qualifying fresh independent review;
- whatever tests and checks a task's contract requires.

A SHA-256 establishes **integrity, not authority**: it proves content did not drift, never who wrote it
or whether anyone was allowed to. Proofbound has no signing keys or trust roots and claims none.

---

## Built on DeepSeek-and-Destroy

Proofbound was bootstrapped from **DeepSeek-and-Destroy** (MIT, © 2026 FrozenPepper), inheriting version
`v15.5.5` of that project. The inherited MIT license and copyright notice are preserved unchanged in
[`LICENSE`](LICENSE).

From DSD, Proofbound keeps the execution and review mechanics that already worked: bounded specialist
workers, parent orchestration that routes rather than re-reviews, fresh independent reviewers, the
repair/re-review loop, immutable task contracts, scope checking, objective integrity gates, and
recovery/resume behavior. That machinery is genuinely good, and Proofbound builds on it rather than
around it.

Proofbound is becoming a distinct system, focused on what DSD does not address: specification and
reflection *before* implementation, durable engineering artifacts with content-addressed provenance,
explicit review purpose, artifact dependency graphs, contract freeze and binding, architectural coherence
over long runs, and provider neutrality.

Proofbound is **not affiliated with or endorsed by** the DeepSeek-and-Destroy project.

---

## Why the name Proofbound?

Two boundaries, one word:

1. **Execution is bound to an accepted engineering contract** — work happens against explicit, reviewed,
   versioned intent rather than a remembered prompt.
2. **Completion is bound to proof** — acceptance comes from evidence, not from an agent's assertion that
   it is finished.

---

## Architecture documentation

The architecture is a routed corpus, not one document. Start at the entry point and follow its map:

**[docs/architecture/proofbound/README.md](docs/architecture/proofbound/README.md)**

| Document | Covers |
|---|---|
| [core-model.md](docs/architecture/proofbound/core-model.md) | Truth layers, the three orthogonal dimensions of an artifact, the principles, evidence authority |
| [execution-and-review.md](docs/architecture/proofbound/execution-and-review.md) | Inherited mechanical invariants, attempts, review purposes, the parent's boundary |
| [artifacts-and-provenance.md](docs/architecture/proofbound/artifacts-and-provenance.md) | Artifact identity, the ledger, derived validity, the change graph |
| [freeze-and-binding.md](docs/architecture/proofbound/freeze-and-binding.md) | Accepted engineering bindings, freeze schema and identity, validation layers |
| [long-running-autonomy.md](docs/architecture/proofbound/long-running-autonomy.md) | Drift, decision provenance, coherence auditing, the threat model |
| [context-economy.md](docs/architecture/proofbound/context-economy.md) | Research: how much repository context a bounded change costs |
| [implementation plan](docs/architecture/specification-reflection-harness-implementation-plan.md) | Milestone status, acceptance criteria, deferrals |

The README teaches; those documents define. Where they disagree, they win.

Parent-harness and operational references: [`SKILL.md`](SKILL.md), [`WORKSPACE.md`](WORKSPACE.md),
[`PROMPTS.md`](PROMPTS.md), [`COMPACTION.md`](COMPACTION.md), [`OPENCODE.md`](OPENCODE.md).
Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md). Policy for coding agents: [`AGENTS.md`](AGENTS.md).

---

## License

MIT — see [`LICENSE`](LICENSE). Copyright © 2026 FrozenPepper, preserved from the upstream
DeepSeek-and-Destroy project.
