# MLR-C3D-R4 — semantic execution boundary: design check

**Selected, not implemented.** This document decides an architecture and stops. No execution
boundary is wired into the runner, no semantic evidence was purchased, and the next paired
experiment is no closer to being ready than R3 left it.

R3 repaired attribution and then proved the environment could not satisfy the treatment. This
answers the one question that leaves open: *what is the smallest reproducible execution boundary
that gives the semantic worker everything the MLR task needs while making the R3 hermeticity
precondition satisfiable?*

## 1. What the worker actually is, from the code

`run_attempt` makes a temporary holder under the system temp directory, materialises the arm into
`<holder>/arm`, `git init`s the workspace, writes the DSD run root **inside** the workspace, and
launches `dsd_attempt.py launch` → `run_worker.py`, which runs:

```
opencode run --model <m> [--variant v] --auto --title <t> --dir <workspace> <prompt>
    cwd = workspace
    env = os.environ.copy() + OPENCODE_DB=<holder>/worker.db
```

`_mlr.environment` adds `PYTHONPATH=<holder>/arm/runtime` and `OBJECTSTORE_ROOT=<holder>/data`;
`pin_interpreter` prepends `<holder>/bin` to `PATH` with symlinks making `python3` the interpreter
that compiled the runtime.

**`env = os.environ.copy()` is the whole of the environment policy.** The worker inherits the host's
`HOME`, `PATH`, shell configuration and everything else. `--dir` scopes OpenCode's own file tools; it
does not scope `bash`, and a `find /` was run.

## 2. Capability inventory

| capability | required | why | access | staged into a view? |
|---|---|---|---|---|
| prepared workspace (`app/`, `tests/`, `docs/`, `PLAN.md`, `README.md`) | yes | the task | read/write | yes |
| `third_party/objectstore-1.4.0/` | **`full` only** | the treatment | read | yes, `full` only |
| compiled runtime (`runtime/objectstore/*.pyc`) | yes | the dependency both arms import | read | yes |
| `data/` for `OBJECTSTORE_ROOT` | yes | the module writes there | read/write | yes |
| DSD run root, worker rules, contract, report skeleton | yes | inherited orchestration | read/write | yes (already inside the workspace) |
| `bash`, coreutils, `find`, `grep` | yes | realistic agent tooling, and evidence-generating | exec | system paths, allowed read/exec |
| CPython 3.9.6 | yes | must match the bytecode | exec | system path, allowed |
| `git` | yes | the agent runs `status`/`diff`; `_prepare` commits a baseline | exec | system path, allowed |
| `opencode` 1.18.29 | yes | the executor | exec | **staged inside**, by hard link |
| writable scratch (`TMPDIR`) | yes | tools and the agent write there | read/write | yes, per slot |
| `HOME` | yes | opencode reads `auth.json` and its config | read | **constructed**, two files |
| network to the model provider | yes | the call | — | allowed |
| session database | yes | telemetry is read from it afterwards | read/write | inside the view, extracted after |
| hidden oracle, reference solution | **no** | correctness is judged outside | — | **never** |
| Proofbound repository | **no** | the workspace is constructed from it by the control plane | — | **never** |
| prior samples, result records, model index, pricing | **no** | control plane only | — | **never** |
| host `~/.ssh`, git credentials, shell history, other providers | **no** | nothing in the task needs them | — | **never** |

## 3. Two planes

**Control plane** — the repository, the fixture, the hidden oracle, the reference solution, result
records, prior samples, the model index, pricing, telemetry aggregation, the hermeticity rule, and
the code that constructs and destroys the semantic view.

**Semantic plane** — the prepared workspace, the arm's declared dependency exposure, the compiled
runtime, permitted tools, a constructed `HOME`, a per-slot `TMPDIR`, and provider access.

Verified against the code: the worker needs **nothing** from the repository. Everything it touches is
already materialised into a temporary holder before launch. The repository is reachable today for one
reason — no one ever arranged that it should not be.

## 4. Mechanisms compared

| criterion | restricted OS user | separate machine / VM | constructed seatbelt view | Docker (Linux VM) |
|---|---|---|---|---|
| controlled source unreachable | with ACL work | yes | **yes, measured** | yes |
| oracle / reference unreachable | with ACL work | yes | **yes, measured** | yes |
| prior evidence unreachable | archives sit in the same home | yes | **yes, measured** | yes |
| `find /` safe for the treatment | partly — world-readable paths remain | yes | **yes, measured: 0 hits** | yes |
| arm symmetry | yes | yes | **yes — one profile, one staging routine** | yes |
| ordinary shell tooling retained | yes | yes | **yes, measured** | yes |
| runtime parity | identical | image drift risk | **identical — CPython 3.9.6, measured** | **no — Linux Python, new identity** |
| model-provider access | yes | yes | **yes** | yes |
| hidden gate stays external | yes | needs transfer | **yes** | yes |
| credentials narrowly injected | new user needs its own | provisioning | **yes — two files, measured** | yes |
| per-slot reset | home per slot, awkward | image reset | **yes — the view is a directory** | yes |
| deterministic construction | machine-specific ACLs | image build | **profile + staging list** | image digest |
| local developer reproducibility | needs admin | needs a second machine | **none needed** | needs a daemon |
| CI feasibility | admin on runners | costly | macOS runners only | good, but Linux |
| operational complexity | high — admin, ACLs, cleanup as another user | highest | **low** | medium — daemon, image, VM |
| new assumptions | UNIX permissions on every path | remote transport | seatbelt, deprecated by Apple | Linux equivalence |
| Proofbound coupling | none | none | none | none |

Docker is not available on this host as configured, and would cost a new runtime identity for a
property the cheaper mechanism already delivers. That is not a reason to refuse a new identity
(`§39`) — it is a reason not to pay for one that buys nothing here.

## 5. Field Test on each component

| component | what becomes impossible without it |
|---|---|
| deny-by-default read profile | nothing prevents the R2 failure; source, oracle and prior samples stay reachable |
| constructed `HOME` | `auth.json` cannot be given without exposing the host home, and OpenCode's global session store stays reachable |
| per-slot `TMPDIR` inside the view | slot *n+1* can read slot *n*'s scratch; this is R3's failure mode in miniature |
| tools staged inside the view | the executor cannot run at all — seatbelt refuses exec below a denied ancestor |
| per-slot view construction and destruction | stale materialisations accumulate again |
| preflight over the view's roots | nothing validates the construction; cleanup is not proof |
| network isolation | **nothing.** No treatment-controlled evidence is reachable over the network. Not adopted |
| process-namespace isolation | **nothing.** No claim depends on process visibility. Not adopted |
| a Linux container | nothing the seatbelt view does not already give, and it costs runtime identity. Not adopted |

## 6. Selected mechanism

**A constructed macOS seatbelt view, per slot, with the executor inside it.**

```
/private/tmp/pb-sem-<slot>/            ← the semantic root; read/write
├── workspace/                         ← app, tests, docs, PLAN, DSD run root, task-local git
│   └── third_party/objectstore-1.4.0/ ← FULL only
├── runtime/objectstore/*.pyc          ← identical in both arms
├── data/                              ← OBJECTSTORE_ROOT
├── tmp/                               ← TMPDIR
├── home/                              ← HOME: auth.json, opencode.jsonc, nothing else
├── tools/opencode                     ← hard link, same volume
└── session/worker.db                  ← OPENCODE_DB, extracted afterwards

readable, not writable: /usr, /bin, /sbin, /System, /Library/Developer, /dev
denied: the repository · the host home · the per-user temp directory ·
        the contents of /private/tmp · everything else
```

**Architecture 1 of §48 — the whole OpenCode session runs inside the boundary.** Architecture 2
leaves the session, its snapshot store and its file-discovery APIs on the host side of the line,
where R3's own question — *what can the evaluated process see?* — stops having a single answer.

## 7. Measured behaviour

All probed live on this host, no model call:

| check | result |
|---|---|
| `cat <repo>/README.md` | Operation not permitted |
| `ls ~` | Operation not permitted |
| `ls /var/folders/.../T` (where the twelve stale materialisations lived) | Operation not permitted |
| `cat /private/tmp/<sibling>` | Operation not permitted |
| `find / -name "objectstore*"` | only the view's own `runtime/objectstore` and `data/` |
| `find / -name "external_test*"` | 0 results |
| `find / -name "app.py"` | the view's own file — agent and preflight see one surface |
| `import objectstore; put/get` | works, CPython **3.9.6** |
| `opencode --version` inside, constructed HOME | 1.18.29 |

## 8. What is deliberately not claimed

Not a secure sandbox. No containment of malicious code, no kernel-isolation claim, no tenant
boundary, no statement about side channels or `/proc`. `sandbox-exec` is deprecated by Apple and
could stop working. The single test this design answers is: *inside the semantic environment,
ordinary discovery cannot find excluded experimental evidence.* Nothing more.

## 9. Ingress and egress

**Ingress.** The control plane builds the view: materialise the arm into it, stage `opencode`, write
`home/`, initialise a task-local git repository with a baseline commit, write the DSD run root and
contract. Nothing is mounted; everything is placed. The repository is never exposed — this is the
adversarial check of `§14`, and the design passes it by construction rather than by hiding
directories.

**Egress.** After the process ends the control plane — which is outside the profile and can read
everything — copies out the workspace and `session/worker.db`. The worker never holds a handle to a
parent path. The hidden oracle then runs **outside**, against the copied workspace, exactly as it
does today.

**Credentials.** `auth.json` and `opencode.jsonc`, copied into `home/`. No host home, no `.ssh`, no
git credentials, no other provider, no shell history. Credentials are never written to evaluation
evidence.

**Caches.** OpenCode's global store, snapshots and tool output stay outside; the view gets a fresh
`HOME`, so caches are per slot. Measured today: that global store holds **0 of the module's 68
fingerprint lines** and 0 oracle lines — clean by measurement, and now outside by construction.

**Network.** Unchanged and unrestricted. No treatment-controlled evidence is reachable over it.

## 10. Runtime identity

**Unchanged.** Same interpreter, same compiled bytecode, same structural identity. That is the
strongest argument for this mechanism over a Linux container, which would have forced a new runtime
identity for a property already obtained.

## 11. Preflight placement

`_hermetic.py` is **not** replaced. It becomes the boundary validator, run over the roots the
semantic process can traverse, ideally from inside the same profile so the control plane stops
guessing what the subject sees. `full` declares its `third_party/` exposure; `contract` declares
none, and its check is: zero source anywhere in the view, runtime structural identity equal to
`full`'s, contract and task identities equal.

Two gaps R4 found in the current identity set, to be closed by the implementation:

- **`HOME` is not a scanned root.** Measured clean today; unscanned by rule.
- **Agent-produced runtime dumps are not recognised.** `/private/tmp/objectstore_dis.txt` — 26,533
  bytes, 296 opcode lines, 0 source lines, written by the paired run's `contract` pair 5 — is still
  on this host and the preflight does not detect it. Recorded rather than quietly deleted.

## 12. Slot lifecycle

```
construct view → stage inputs → preflight → launch → extract workspace and session → destroy view
```

Construction failure or preflight refusal: **no slot consumed**, infrastructure precondition failure,
existing resume semantics. Once the worker starts, ordinary semantic rules apply. Destruction on
success, failure, exception and interruption where practical — and the next slot's preflight is what
actually establishes validity, because cleanup is never proof.

**No debug mode that silently widens the view.** A view built with extra exposures produces a
different boundary identity, and a different identity is a different experiment.

## 13. Boundary identity

Bound into the series: the profile text, the staged tool list and their digests, the exposure list
per arm, the `HOME` construction policy, the `TMPDIR` policy, the interpreter identity, and the
hermeticity rule identity. Not bound: host state that does not change what the subject can see.
Persisted only what is needed to reconstruct and recognise the boundary (`P3`); per-slot condition
lives in that slot's preflight record. Evaluation-local (`P7`).

## 14. Residual risks

Sibling *names* in `/private/tmp` remain listable, because `find /` must be able to descend into the
view that lives there — contents are denied, and the lifecycle must keep that directory free of
experiment material. `sandbox-exec` is deprecated. The Xcode `git` shim prints errors writing an
xcrun cache to the host temp. Staging a 144 MB executable relies on same-volume hard links. And the
decisive unknown: **a full OpenCode session has not been run inside the view** — only `--version` —
because that would cost a semantic sample.

## 15. Implementation slices

**R4-A — boundary substrate.** View construction, staging, profile generation, destruction,
deterministic local probes. No MLR wiring.

**R4-B — MLR integration.** Run the existing worker inside it; close the two preflight gaps; run the
preflight from inside the view; per-slot lifecycle; boundary identity bound into the series. The
first non-trivial OpenCode session inside the view happens here, and it is where this design is
actually falsified or confirmed.

**R4-C — qualification.** A tiny paired instrumentation qualification, under a new experiment
identity. Not before A and B are green.

---

# R4-A — substrate implementation status

**Implemented and proven locally. Not integrated.** The design above is unchanged; this records what
now exists, what it demonstrates, and — as precisely as the rest — what it does not.

## A1. What was built

`evals/_semantic_view.py`. A slot is constructed, used and destroyed:

```python
with semantic_view(policy) as view:
    view.stage_tree(prepared, "workspace")
    report = _hermetic.scan(view.roots(), sensitive)
    done = view.run([interpreter, "-c", "..."])
    view.collect("workspace", destination)
```

`Policy` is what kind of boundary this is — staged tools by digest, the environment allowlist, the
exposed system paths, the network decision, the declared exposures. `View` is one instance of it. The
identity is taken over the policy and never over the slot, so two slots of one experiment are the
same boundary and a slot that exposes one more root is a different one.

The substrate names no experiment. What is sensitive, what a workspace contains, which runtime to
stage and which interpreter to expose are all supplied by the caller, and a test asserts the module
mentions none of them.

## A2. What the probes establish

Recorded in
[`craft-mlr-semantic-view-probes.json`](../../results/craft-mlr-semantic-view-probes.json) and held
by 51 tests that execute real commands rather than inspect path arithmetic.

| | |
|---|---|
| repository read | `Operation not permitted` |
| host home listing | `Operation not permitted` |
| host per-user temp listing | `Operation not permitted` |
| a controlled-source copy planted outside the view | unreachable, and does not contaminate the view |
| the same copy planted inside `tmp`, `home` or `workspace` | **contaminated**, and clean again once removed |
| `find / -name "objectstore*"` | the view's own runtime, and nothing else |
| `find` for the hidden oracle | no results |
| environment keys in the child | `HOME`, `PATH`, `TMPDIR` — nothing inherited |
| a host-only sentinel variable | absent inside, intact outside |
| `$HOME`, `$TMPDIR`, `tempfile.gettempdir()` | all inside the view |
| compiled runtime | imports and executes, on each of 3.9, 3.10 and 3.14 |
| task-local `git init`/`add`/`commit`/`status`/`diff` | works, and does not discover the evaluator's repository |
| two sequential slots | the second finds nothing the first produced, in any area |
| exception, failing child, aborted construction | the slot is destroyed in every case |

**The deepest test passes.** Two slots run ordinary shell, Python and filesystem discovery in
sequence on this host; each receives only constructed state; neither reaches the control plane; and
the second finds no marker from the first in `workspace`, `home`, `tmp`, `session` or `data`.

## A3. What the implementation taught that the design did not know

**A copied system binary will not run.** macOS validates code signatures and a copy carries none; the
kernel kills the process, measured as `SIGKILL` with no output. Staging is therefore by hard link,
and a source on another volume is refused loudly rather than copied into something that dies on exec.
System tools are not staged at all — they are reached where they already live, which the policy
allows.

**A staged link must never be `chmod`-ed.** It shares an inode with the control plane's own file, so
setting its mode sets that file's mode. Write is refused by the policy instead, which is where a rule
about what the subject may do belongs. This was in the code for an hour and is now a test.

**An exposure implies its ancestors.** Path resolution reads every directory on the way down, so a
policy that exposed an interpreter under a denied parent could not launch it — `realpath: Operation
not permitted` on a binary that was explicitly allowed. Exposing a subpath now implies traversable
ancestors.

**`ignore_errors=True` hid a leak.** A broken cleanup path left forty-five empty tool directories
before anything noticed, because destruction swallowed its own failure and the one test that checked
compared before against after — invisible to a leak that happens every time. Destruction is now
verified, retried once, and what still survives is remembered; the assertion runs over the whole test
module and asks the substrate what *it* failed to remove rather than sweeping a shared directory.

**Sibling names are visible; contents are not.** The view's parent must stay listable for a subject
to walk down to its own workspace, so a name beside a view is discoverable even though its bytes are
refused. `parent_is_clear` measures that rather than hiding it, and a stale runtime dump left in
`/private/tmp` by the paired run — recorded in the R4 probe evidence first — was removed under that
rule.

## A4. Hermeticity, rescoped rather than weakened

`_hermetic.py` is unchanged. What changed is what it is pointed at.

The old condition was *the host must not contain the controlled evidence*, which the host cannot
satisfy while it holds the repository. The new condition is *the semantic view must not expose
undeclared controlled evidence*. A repository full of source outside the boundary is now expected,
and a test asserts a clean result in its presence. A copy inside `home`, `tmp` or `workspace` still
fails, which is the property that matters: isolation must not make the checker blind.

`home` is in the scanned roots, closing the gap R4 identified.

**Pre-launch hermeticity and runtime attribution stay separate.** If an agent disassembles the runtime
after launch and writes it into its own scratch, that is allowed, it is attribution's business, and
the next slot's preflight is what ensures it does not survive.

## A5. What R4-A does not prove

It does not prove that the real OpenCode semantic session works inside the boundary. `--version`
runs; a session was not started, because that would cost a semantic sample. It does not integrate the
MLR worker, and the existing `run_attempt` path is untouched. No model was called and no credential
was staged.

The residual risks from the design stand: `sandbox-exec` is deprecated, sibling names under the
view's parent remain listable, and the boundary is macOS-only.

## A6. The seam R4-B consumes

`Policy(tools=…, env=…, extra_reads=…, network=True, declared=…)` and `semantic_view(policy)`, then
`stage_tree` for the prepared arm, `stage_file` for the contract and credentials, `run` for the
executor, `roots()` for the preflight, `collect` for the workspace and session database, and
destruction on the way out. R4-B supplies the arm, the executor, a narrow credential home, the
session location and the declared exposure for `full`; it changes nothing in this module.

---

# R4-B — real worker integration status

**Integrated and proven to the deepest layer reachable without buying a semantic sample.** One layer
is explicitly not proven, and is named rather than glossed.

## B1. The cut

The boundary is entered **once**, around the inherited launcher:

```
control plane          materialise arm · stage declared inputs · preflight
      │
      ▼  sandbox-exec, one entry
semantic view          dsd_attempt.py → run_worker.py → opencode → tools → subprocesses
      │
      ▼  after termination, from outside
control plane          extract workspace + session · destroy view · hidden gate · ledger · profile
```

Everything below the entry is a descendant and inherits it. Wrapping individual shell commands would
have left the executor itself outside, which is where *what can the evaluated process see* stops
having one answer.

`evals/_mlr_boundary.py` holds the integration. `_semantic_view.py` was not modified; neither were
`_hermetic.py`, `_mlr_context.py` or `_profile.py`.

## B2. Construct, never mount

The arm is materialised on the control plane and its declared parts copied in. The repository is
never exposed. The launcher the DSD protocol requires is staged as a declared input — and checked
first: `_hermetic.scan(["scripts"])` returns **clean**, so what crosses is orchestration and not
evidence.

The interpreter is exposed by policy, so `python3` inside the view is the one that compiled the
bytecode, and the runtime imports without a magic-number error.

## B3. Measured

[`craft-mlr-boundary-integration-probes.json`](../../results/craft-mlr-boundary-integration-probes.json),
and 31 tests that run the real machinery.

| | |
|---|---|
| `contract` staging | preflight **clean**, zero declared, no `third_party`, zero `.py` in the runtime |
| `full` staging | preflight **clean**, exactly **4** declared exposures, zero undeclared findings |
| runtime structural identity | `28ba66e1cd49b157`, unchanged from every prior run |
| contract digest | `af3d3e9be15b51ed`, unchanged |
| workspace tree | matches the legacy prepared arm file-for-file by digest |
| visible tests | pass inside the boundary and outside it |
| environment | `PATH`, `HOME`, `TMPDIR`, `PYTHONPATH`, `OBJECTSTORE_ROOT`, `OPENCODE_DB`, `DSD_OC_RUN_DB` — every value inside the view |
| host sentinel | absent in the child **and the grandchild** |
| deepest child reading the repository, the home, the oracle | three refusals |
| deepest child running the historical search | only the slot's own runtime |
| executor | **1.18.29**, runs inside on a constructed home |
| executor session list | empty |
| executor MCP | none configured |
| executor credentials | `0 credentials`, read from the constructed home |
| executor session store | created **inside the slot**, at `OPENCODE_DB` |
| oracle | same decision on 3 valid and 2 invalid candidates, before and after the round trip |
| retained session, extracted and read after destruction | 24 model calls, 0 unresolved, 0 uncovered events; profile complete |
| `full` → `contract` | the second slot finds no source |
| `contract` → `full` | the second slot finds exactly its own declared source |
| a stale `full` copy outside the view | unreadable, and the preflight stays clean |
| a second copy inside `home`, `tmp` or `session` | contaminated, in **both** arms |

## B4. What the integration taught

**`os.environ.copy()` inside the boundary copies constructed state.** `run_worker.py` still calls it,
and that is now correct rather than a hole: the whole chain begins inside the view, so what it copies
is what was constructed. The deep sentinel proves it — a host-only variable is absent two levels
down. No inherited orchestration was rewritten to know about isolation.

**Two environment names appear that were never declared.** `LC_CTYPE` and `__CF_USER_TEXT_ENCODING`
are set by the platform inside the child. Poisoning both on the host and re-reading them inside shows
the host values do **not** cross: what appears is `C.UTF-8` and a uid-derived encoding tag, generated
rather than inherited.

**The executor needs no file staged into its home to start.** It builds `~/.cache/opencode`,
`~/.config/opencode`, `~/.local/share/opencode` and `~/.local/state/opencode` from nothing, inside the
view. Credentials remain a declared input for R4-C, staged by the caller and destroyed with the slot —
tested with a fixture, never a real one.

**Preflight before launch is a control-flow invariant.** `launch()` takes the preflight report as an
argument and refuses anything but `clean`, so a caller that never ran one cannot call it and a caller
that ignored one is stopped. Nothing durable records that a slot was ever clean.

## B5. The layer that is not proven

A **model-driven tool call issued by the executor** has not been exercised. Reaching it requires a
provider call, and this milestone does not buy semantic evidence. Everything beneath it is
mechanically established: staging, the process tree, the environment, the executor's local lifecycle
including its session store, and the evidence round trip.

What remains open is narrow and specific: *does a tool call the model asks for inherit the same
evidence surface as the subprocess tree that was measured?* The architecture says it must — the tool
runs as a descendant of a process that is already inside — and the architecture has been wrong before.
R4-C is where that is settled.
