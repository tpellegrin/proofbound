# Installing the worker backend

Proofbound coordinates with **your** frontier agent and delegates routine work to a **DeepSeek**
worker run by a pinned OpenCode build. This page gets that worker working. It makes **no provider
request**.

Three separable things, and they fail separately:

| | Checked by | Means |
|---|---|---|
| **Readiness** | `pb_workflow.py doctor` | the right host, interpreter, executor bytes, boundary |
| **Credential validity** | your first real run | the key is accepted by the provider |
| **Live qualification** | a recorded experiment | this configuration has actually produced work |

`doctor` reporting `ready: true` means the first of those. It does not mean your key works, and it
does not mean the workflow has been qualified end to end. See the support matrix in the
[README](../README.md#support-matrix).

## Supported environment

**macOS on Apple silicon, Python ≥ 3.10.** The worker boundary is `sandbox-exec`, which is macOS
only. Linux and Intel macs are not supported for *running workers*; the rest of the repository,
including the whole test suite bar the boundary tests, is portable.

## 1. The pinned OpenCode build

The qualified build is **1.18.29, darwin-arm64**, sha256
`2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669`.

It is pinned by **content**, not by version string: `doctor` hashes the file, and the supervised
launcher re-checks the hash on every launch. A different build is not refused for being newer — it
is refused for not being the one the recorded evidence was produced with.

Install it into Proofbound's own directory, leaving any existing global `opencode` alone:

```bash
python3 scripts/install_worker_backend.py            # verifies, then reports what it did
```

That script:

* downloads the pinned release **by exact version**, never "latest";
* verifies the sha256 **before** putting it anywhere executable;
* installs to `~/.proofbound/executors/opencode-1.18.29-darwin-arm64/opencode`;
* refuses to touch `/usr/local/bin`, Homebrew, or any `opencode` already on your `PATH`.

Already have the binary? Point at it instead and skip the download:

```bash
python3 scripts/install_worker_backend.py --from /path/to/opencode
```

## 2. DeepSeek authentication

OpenCode stores credentials at `~/.local/share/opencode/auth.json`. Authenticate with OpenCode's own
flow:

```bash
~/.proofbound/executors/opencode-1.18.29-darwin-arm64/opencode auth login
```

Choose DeepSeek and supply your key. Proofbound never asks for, stores, prints or logs a key.

When a run starts, **only the `deepseek` entry** is copied into the run's isolated home, with mode
`0600`. Other providers in your `auth.json` are not staged. The evidence exporter refuses to place
a credential in a package.

Check it is *configured* without spending anything:

```bash
python3 scripts/pb_workflow.py doctor
```

`worker.configured: true` means the entry exists. It does **not** mean the key is valid — only a
real request establishes that, and `doctor` makes none.

## 3. The model

`deepseek/deepseek-v4-flash`, variant `high`.

Inherited DSD configuration referred to workers as `opencode-go/...`. That is the *old* identifier
shape and is not what this path uses. The supervised workflow records the model in each run's
`run-config.json` and refuses to launch against a different executor than the one recorded.

This is the built-in worker profile `deepseek-v4-flash-high`, the default for `doctor` and
`start`. A run's profile is resolved once at `start` and fixed with a digest; see
[worker profiles](architecture/proofbound/worker-profiles.md).

## Optional: a local worker profile

**Unqualified.** No local model has been run through Proofbound. What is tested is the mechanics:
a scripted endpoint stood in for a model while the real pinned executor ran inside the real
boundary. Setting one up is optional, and nothing below downloads a model or installs a server.

You need your own OpenAI-compatible server listening on **this machine** — for example llama.cpp's
`llama-server`, which needs a chat template that supports tool calls. Then:

```bash
python3 scripts/pb_workflow.py profile --template > ~/local-worker.json   # edit every value
python3 scripts/pb_workflow.py doctor --worker-profile ~/local-worker.json
```

The profile states the loopback endpoint with its port, the server's model id, and both token
limits; nothing is inferred from a model name. `doctor` checks that something listens there and
lists models. It requests no completion and consults no cloud credential. Tool calling, usage
reporting and cancellation are **not** established by it; `evals/pb_qualify.py` exists for that.

Start with `--worker-profile /absolute/path/local-worker.json`. Authorize with
`authorize-resources --launch-ceiling N --owner-authorization '…'` instead of `authorize-spending`:
there is no API bill for a money limit to bound, and local compute cost is recorded as unknown,
not zero. The worker's network is restricted to loopback and no credential is staged. The
coordinator, and anything it runs, is outside that boundary — this is not offline execution.

## Recovery

| Symptom | What it means | Do this |
|---|---|---|
| `supported worker environment is macOS arm64 only` | workers cannot run here | coordinate from this host, run workers on a supported one; or run the offline suite only |
| `pinned OpenCode executable is missing` | not installed where expected | `python3 scripts/install_worker_backend.py` |
| `executor bytes are not the experimentally qualified build` | a different build is present | reinstall the pinned one, or record new identities deliberately — do not rewrite history |
| `DeepSeek credential is not configured` | no `deepseek` entry in `auth.json` | `opencode auth login` (step 2). No provider request was made to determine this |
| `sandbox-exec cannot start in this process environment` | you are inside another sandbox | run from a terminal outside the enclosing sandbox; nested boundaries are refused, not worked around |
| `existing or incomplete run at …` | a previous `start` left state | inspect it; nothing was overwritten. Use a different `--change`, or remove it deliberately |
| `this run already exists and its configuration is fixed` | you changed `--check` or `--executor` on a started run | the old values are still in effect and are named in the error. Start a different `--change` |
| `project checks failed` / `did not finish within Ns` | the project's own check | read the receipt path in the error. A check that did not finish has **no verdict** — that is unknown, not failed |
| `a repair was already decided …` | an outstanding repair | `revise --reason …`, or supersede it explicitly |
| `spend is unknown` / accounting incomplete | a worker's usage could not be settled | no further launch is admitted. Inspect the run's receipts; do not raise the budget to get past it |
| `this run already has a sealed delivery` | the run is finished | inspect `delivery/`; use `--into` for a separate copy |
| `local endpoint … is not reachable` | nothing listens where the profile says | start your server there, or edit the profile. Nothing falls back to a hosted model |
| `no external API billing … use authorize-resources` | a local profile's run | `authorize-resources --launch-ceiling N --owner-authorization …` |
| `the local worker's executor configuration is missing or no longer matches` | the file written at `start` moved or changed | do not repair it by hand; start a different `--change` |
| `this run already exists … --worker-profile … (differs in …)` | the profile, or its file, changed since `start` | the recorded settings stay in effect. Start a different `--change` to use new ones |

Recovery never involves editing run JSON by hand. If a state seems to need that, it is a defect —
report it with the receipt path.
