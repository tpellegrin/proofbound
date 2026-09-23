# Worker profiles

> **Normative.** What a worker configuration is, how a run fixes it, what resources mean for a
> worker with no external bill, and what the local route's boundary does and does not establish.
> Whether a configuration can do the work is a different question, answered by
> [evaluation-qualification.md](evaluation-qualification.md). Implementation:
> `scripts/_worker_profiles.py`.
>
> Entry point: [README.md](README.md).

## A model name is not the system under test

Five identities are distinct and recorded separately; none is inferred from another.

| Identity | Examples | Where recorded |
|---|---|---|
| Coordinator host and model | Codex / GPT-6, Claude Code / Opus | `coordinator` receipts: requested, self-reported, observed — never merged |
| Worker executor build | OpenCode 1.18.29, pinned by sha256 | run config `executor`, re-checked at every launch |
| Inference route | provider, endpoint, model, variant, limits | the resolved **worker settings** |
| Worker role | spec-author, implementer, reviewer, … | the attempt and its contract |
| Control plane | the `scripts/` bytes that admitted, bounded and accounted | plan and evidence records |

A **profile** names the inference route plus everything the route needs to run honestly: executor
pin, tool permission flag, credential entry, billing basis, resource allowance and network
boundary. Profiles are independent of the coordinator. Changing who coordinates never changes the
worker, and choosing a worker never selects a coordinator.

## Resolution, identity and immutability

A profile is **resolved once, at `start`**, into a settings record carrying a SHA-256 digest over
its canonical JSON. The run keeps the settings, not the profile's source:

- **Resume reads the recorded settings.** Editing a profile file later does not reach a started
  run. Every command that reads the run refuses settings whose bytes no longer match their digest,
  and refuses a run whose top-level `model`/`variant` disagree with them. Recovery never involves
  editing run JSON.
- **A repeated `start` names what it did not apply.** A different profile, an edited profile file
  or a different `--deadline-seconds` is refused, listing each differing field
  (`limits.output`, `profile.source_sha256`, …). Nothing changes.
- **Historical runs are read as recorded (`P6`).** A run-config written before profiles has no
  settings block. It is interpreted as the DeepSeek route with the model and variant it recorded,
  derived on read and never written back. A legacy record whose model is not DeepSeek's prices to
  nothing, so its spend is unknown rather than priced wrongly.

Selection has one public mechanism: `--worker-profile NAME|PATH` on `pb_workflow.py doctor` and
`start`, defaulting to `deepseek-v4-flash-high`. `pb_workflow.py profile` prints resolved settings
or, with `--template`, a local profile to fill in. Nothing is inferred from a model name: a local
profile states its endpoint, model id and both token limits, and unknown fields are refused rather
than ignored.

## The two kinds

| | `deepseek-v4-flash-high` (default) | `local-openai-compatible` (a file) |
|---|---|---|
| Route | OpenCode's native `deepseek` provider | `@ai-sdk/openai-compatible`, bundled in the pinned executor |
| Endpoint | provider-managed | a **loopback** URL with an explicit port; no userinfo, query or fragment |
| Variant | `--variant high` | none is passed: `high` means nothing to a local server |
| Credential staged | the `deepseek` entry only | **none** |
| Billing basis | `dated-table` at `deepseek-2026-09-09` | `no-external-api-billing` |
| Worker network | unrestricted | **loopback-only** |
| Authorization command | `authorize-spending` | `authorize-resources` |
| Live qualification | `pb-handoff-2`, one seeded-authority continuation | **none** |

The DeepSeek route is selected by its built-in name only; it cannot be redefined by a file. A
profile carrying a secret-looking key (`api_key`, `token`, `authorization`, `headers`, …) is
refused, so profile identity cannot contain a credential. Refusals name every problem at once.

## Credentials and fallback

A worker must not reach a model or service its profile did not name:

- **Only the named credential is staged**, into the run's isolated home, mode `0600`. A local
  profile stages none. A missing entry refuses authorization and makes no provider request.
- **A local worker gets a minimal environment in every mode**: `PATH` limited to the executor's
  directory and system paths, the staged `HOME`, `LANG`, `TMPDIR`, and the executor switches
  below. Ambient provider keys and `OPENCODE_*` variables do not pass.
- **The executor's configuration is written at `start`**, into the run's runtime directory
  outside the project. Written any later, an offline launch could fall back to the executor's
  default hosted model. It enables only the `local` provider, and sets both `model` and
  `small_model` to the profile's model, so no auxiliary call names a hosted default. It is pointed
  to by `OPENCODE_CONFIG`, alongside switches that disable project config, the model-catalogue
  fetch, self-update, LSP download and sharing.
- **The launcher refuses bytes that moved.** A missing or altered executor configuration refuses
  the launch before the executor, without consuming a slot. Inside the boundary that file is
  write-denied to the worker.

## Resources: priced and unbilled workers

The run's billing basis is **frozen into its launch ledger** with the first reservation.
`LaunchLedger` and `spend()` receive it explicitly from the run's settings wherever the supervised
workflow calls them: admission, status, finish and evidence export. A ledger recorded under one
basis refuses a caller naming another. A ledger that predates profiles keeps the historical
DeepSeek interpretation and refuses reuse by an unbilled worker. Only callers with no run
settings, such as historical experiment guards, get the DeepSeek default.

Paid usage, derived price, executor-reported cost and confirmed billing remain five different
facts (`evals/README.md`). For an **unbilled** worker:

- **No price is derived and none is implied.** A known absence of API billing is not a claim that
  compute, electricity or hardware cost nothing; those stay unknown. The executor's own cost field
  reads `0` for a local provider and is not evidence of anything.
- **Lifecycle and telemetry are separate findings.** An attempt without a readable terminal record,
  or a launch intent never classified, blocks every further launch, whatever the worker costs. An
  unresolved attempt never silently buys another trajectory. Telemetry gaps — unattributed
  sessions, unbalanced calls, zero-token calls — block exactly the allowances computed from
  telemetry. Today that is the optional output-token allowance.
- **A finished call recording zero input and zero output tokens is unknown, on any basis.**
  Observed with the pinned executor: when a server omits its usage field, OpenCode 1.18.29 records
  zeros. For a priced worker that would have been a `$0` figure for an unmeasured call. It now
  leaves the figure incomplete, and admission refuses.

What bounds a local run, stated so nothing configured is mistaken for enforced:

| Enforced by Proofbound | Configured, not enforced by Proofbound |
|---|---|
| launch ceiling, one shared repair allowance, the attempt deadline (host-owned teardown of the worker client), one supervised launch per run at a time, the output-token allowance between attempts when set | per-call output limit (sent as `max_tokens`; the server may or may not honour it), context limit (used by the executor for compaction), server concurrency |

`authorize-resources` records the owner's authorization with that split, and accepts no money
limit, because a money limit would bound nothing here.

## Network and privacy claims

The local route's worker boundary denies all network access and then allows outbound connections
to loopback only. Authorization probes the boundary before recording anything. A wrapped child
must reach the configured endpoint and must be refused (`EPERM`) connecting to `192.0.2.1`, an
address that is never routed. Otherwise authorization fails. The DeepSeek boundary's text is
unchanged.

Three claims stay separate:

- **Loopback-only worker network** — enforced for the worker's process tree, as above.
- **Local inference** — a property of whatever answers on that port, which Proofbound neither
  launches nor identifies.
- **Offline execution** — not claimed. The coordinator runs outside the boundary and may send
  project content anywhere its own host allows, as may any tool it invokes. Endpoint
  configuration alone never establishes privacy.

The worker still sees the project, the harness and the paths its interpreter needs, exactly as on
the DeepSeek route. Neither route protects against malicious code or a compromised operator.

## Readiness is layered, and `doctor` generates nothing

`doctor --worker-profile …` reports each layer separately:

| Layer | How `doctor` checks it |
|---|---|
| profile validity | resolution, with every problem named |
| executor | installed, and its bytes equal the profile's pin |
| boundary | `sandbox-exec` can start in this process |
| credential | presence of the named entry; values never read out |
| endpoint | a TCP connection and `GET …/models`; no completion requested |
| tool-loop compatibility | **not established by `doctor`** |
| task qualification | **not established by `doctor`** |

With nothing listening, a local profile is **not ready**. The problem names the URL and says to
start the server or edit the profile. It never suggests using a cloud credential instead. An
endpoint that answers HTTP is not thereby shown to handle tool calls, report usage or honour
cancellation; those are qualification questions
([E26](evaluation-qualification.md#e26-qualifying-a-configuration-before-selecting-it)).

## The shared server and cancellation

A local inference server is long-lived and shared; **no attempt owns it**. Teardown recognises an
attempt's processes by corroborated ownership: a recorded pid, its group or descendants, or a
command line naming the attempt's runtime directory. A server started independently matches none
of these and is never signalled. A timed-out local attempt records
`server: owned_by_attempt: false, signalled: false`. Stopping the client establishes nothing about
whether the server stopped generating for it, and that is recorded as unknown.

Observed with the pinned executor against an endpoint that drops every stream mid-response:
OpenCode 1.18.29 **retried 4,649 times in the 900-second deadline**, recording each retry as a
finished zero-token call. The deadline ended it; the gate refused the attempt. The deadline is the
only thing bounding a worker whose server keeps failing mid-stream.

## What this does not establish

That any local model works. No local model was installed or qualified. The local route's
mechanics were exercised by a scripted endpoint through the real pinned executor and boundary,
which shows the protocol round trip and Proofbound's handling of it. Real local models differ in
tool-call formatting, usage reporting, context behaviour, speed and cancellation, and each
configuration needs its own qualification on its own hardware. Evidence:
[evidence/worker-profiles-qualification-2026-09-23.md](evidence/worker-profiles-qualification-2026-09-23.md).
