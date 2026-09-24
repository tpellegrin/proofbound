# The coordinator protocol

Proofbound has **no default frontier orchestrator**. You choose the coordinator; the workflow does
not change when you do.

This document is the contract a coordinator satisfies. Codex and Claude Code have thin adapters
([`CODEX.md`](../CODEX.md), [`CLAUDE.md`](../CLAUDE.md)) that say nothing more than where to start —
everything they rely on is below, and any host that meets these requirements can coordinate the same
run.

## The four layers

| Layer | Responsibility | Who |
|---|---|---|
| **Owner** | The goal, consequential policy choices, resource authorization | A human |
| **Coordinator** | Decomposition, contracts, architectural tradeoffs, adjudication, escalation, acceptance | **Your** frontier host — Codex, Claude Code/Opus, or another capable agent. No product default |
| **Worker** | Repository discovery, proposed requirements, implementation, repair, fresh review, technical investigation | DeepSeek, by default, through the supported execution path |
| **Control plane** | Identity, admission, lifecycle, scope, deadlines, accounting, evidence, deterministic checks | Shared Python helpers in `scripts/` |

The separation is the point. The same frontier model can coordinate different projects; the same run
can be continued by a **different** capable coordinator from the retained state. Neither changes the
worker backend, the governing authority, prior evidence, or the remaining allowances.

## What a coordinator host must provide

Ordinary capabilities, deliberately:

1. **Read files** under the run root and the project.
2. **Run a command** and read its stdout — `python3 scripts/pb_workflow.py …`.
3. **Follow the decision protocol below**, which means holding a short amount of state across
   commands and making a judgment when asked for one.

That is all. In particular a coordinator does **not** need proprietary memory, hooks, native
subagents, background tasks, or a vendor-specific delegation API. Hooks can improve continuity and
are optional everywhere they appear.

A `continue` that launches can run as long as the attempt's deadline. If your host limits a
command's duration, or your session may end, that is safe. The launch is supervised by the run, not
by your shell. Afterwards run `status`: if it says `running`, `continue` waits for that same launch;
if it names `recover`, follow the [operator guide](operator-guide.md#if-the-session-running-continue-ends).
Do not run `continue` in the background and assume it finished.

You do **not** need the unused coordinator's CLI, credentials or subscription. Coordinating with
Claude Code requires no Codex installation, and the reverse.

## The decision protocol

```
status   →  tells you the single next permitted action, and why
continue →  performs the next *mechanical* step (bind, launch, gate, record)
decide   →  your semantic judgment: accept | repair | owner
revise   →  carry out a repair you decided
finish   →  seal the delivery
```

`status` returns one of:

| `action` | What it means | What you do |
|---|---|---|
| `bind`, `record-requirements`, `record-consistency`, `launch`, `gate` | A mechanical step is due | `continue` |
| `adjudicate` | A fresh clean review awaits **your judgment** | read the evidence, then `decide` |
| `blocked` | Something needs resolving — an owner decision, a pending repair, an unresolved launch | read `reason`; the `next` field names the command |
| `finish` | Everything required is accepted | `finish --report <your report>` |
| `complete` | A delivery is sealed. The run is over | the run's `delivery/` directory holds it; `status` returns an `inspect` object naming the patch, handoff and manifest, plus a ready-made `git apply`. There is no next command |

**The control plane never decides whether work is good.** It will not infer acceptance from an exit
code, and it does not read a reviewer's prose. When `status` says `adjudicate`, that is a real
question for you.

A `decide --reason` should let a later reader check the judgment without your context. It states:
the decision and the constraints it rests on; the material assumptions; the plausible ways it could
be wrong; the external evidence consulted — gate, checks, the artifact itself; and which evidence
supports the decision. For a disputed finding, **reproduce its witness**: a correct finding has
arrived with an incorrect example before. Self-reported confidence or coverage is a claim, not
provenance, and a longer reason is not a better one.

## What a coordinator should read, and when

Consume **mechanical state first**, then the smallest evidence sufficient for the decision in front
of you.

* `status` is the state surface. It is cheap and complete enough to route on.
* When adjudicating, read the `evidence` report and the `gate` it names — not the whole run tree,
  not the whole repository, and not every worker transcript.
* A report is a **claim by a worker**, retained verbatim and attributed. A clean integrity gate
  means the permitted process occurred, not that the engineering is sound.
* A truncated report prefix is not evidence that the omitted part contains nothing. If a surface
  says it truncated, ask for the rest before concluding.
* Full evidence stays available on demand. Reading less to save tokens is fine; concluding more
  than you read is not.

Do not poll. Mechanical steps and blocking waits should not cost model calls merely to narrate
progress.

## Delegation

Routine technical work goes to the configured DeepSeek worker through `continue`. That is what the
worker path is for, and it is what keeps frontier consumption down.

**Do not let a host's native sub-agent feature quietly become the delegation mechanism.** Codex
multi-agent and Claude Code subagents run *frontier* models; using them for repository discovery,
implementation, test authoring or routine review replaces cheap worker tokens with expensive
coordinator tokens and produces no Proofbound evidence. Proofbound's delegation is `pb_workflow.py
continue`.

Frontier attention is justified for: a substantive contradiction, a disputed review finding, a
cross-component design choice, a failed bounded repair, or evidence insufficient for acceptance.
Record the reason and the inputs when you escalate. Self-reported confidence is not a routing
criterion on its own, retries are bounded, and a failure never automatically upgrades the worker
model.

A fresh worker context is a **different** review context. It is not demonstrated statistical
independence, and nothing here claims it is.

## Recording who coordinated

Identity is recorded where it is available, and how it was obtained is recorded with it:

* `requested` — the coordinator you selected, as configured.
* `self_reported` — what the coordinating agent says it is. A claim, retained as one.
* `observed` — runtime metadata the host actually exposes, when it exposes any.

These are separate fields and never merged. Model identifiers are not guessed, and a model is never
silently substituted. If the host exposes nothing, that is recorded as unavailable rather than
filled in.

Set it once per run:

```bash
python3 "$PB/scripts/pb_workflow.py" coordinator --run "$RUN" \
    --requested "claude-code/opus" --self-reported '<what your host reports>'
```

## Another host

Any agent environment meeting *What a coordinator host must provide* can coordinate a run. Start it
with the goal, the run root, and this document; drive `status` / `continue` / `decide`.

**This has not been live-qualified for hosts other than the ones listed in the support matrix.**
Documented capability requirements are not a claim of tested support.
