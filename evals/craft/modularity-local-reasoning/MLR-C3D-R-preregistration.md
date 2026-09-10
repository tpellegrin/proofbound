# MLR-C3D-R — repaired-instrument requalification, pre-registered

Written and committed **before the first paid call of this identity**. This is instrument
requalification, not model tuning and not another headroom experiment.

## 1. Purpose, frozen

> Field-validate the repaired representation attribution and the observer-isolation position under
> the already-qualified DeepSeek configuration.

Headroom is **not** the question. MLR-C3D established it: 5 of 5 correct runs consumed
implementation source, median 5,822 bytes under the then-current accounting. Re-establishing that
would be paying to rediscover something already known.

## 2. What was repaired

MLR-C3D failed because the instrument asked *how* text arrived and treated the answer as *what the
text was*. Origin and delivery route are now separate axes.

**Origin** — `implementation-source`, `implementation-runtime`, `implementation-metadata`,
`public-contract`, `application`, `behaviour`, `harness`, `unresolved`, `other` — is settled against
the delivered bytes. **Delivery route** — file read, search, documentation, introspection, run, edit,
harness replay, unknown — records only the mechanism.

Source is recognised by content: the module's own 68 fingerprint lines, which share nothing with the
application, tests, contract, task, reference solution, hidden oracle or worker protocol. Verbatim
reproduction carries the origin however it travelled — direct read, `grep` hit with its
`path:lineno:` decoration, copy through a scratch file, log echo, `git show`. Derived text that does
not reproduce source keeps its own origin. Paraphrase is invisible to the method and is recorded
**unresolved rather than zero**.

Lineage supplements the path rather than overruling it: where the path already identifies a module
file, the whole delivered rendering counts; elsewhere only the demonstrably verbatim lines do.
Metadata is its own unit and never source bytes. Mixed artifacts are decided by share. Source
identity is taken over matched lines, order-independently, so replay raises delivered and leaves
unique alone.

**A retrospective note, not a recomputation.** Re-read under the repaired model, the C3D escapes
carried *no verbatim source*: the worker log echoed the paths the agent had read, not their contents.
The leak was structural metadata. C3D's recorded numbers are unchanged and its verdict stands.

## 3. Observer isolation — what is and is not achieved

**Outside the agent's reach:** the OpenCode session database, the hidden oracle, the reference
solution, every prior sample's workspace. **No harness artifact names the arm or the experiment**, so
treatment blindness holds — verified by test.

**Inside, and it cannot move here:** the DSD run root, including `worker.log`. `resolve_run_path`
requires the log under the run root and the evidence gate reads it from the launch reservation, so
relocating it means changing DSD's attempt layout — outside this milestone's mandate. The repair is
therefore measurement-side, and a test pins the channel so it cannot be forgotten.

**Threat model.** This preserves experimental conditions against ordinary agent tooling — reading
files, searching, running commands. It is not a sandbox and claims nothing against a process that
inspects process tables, parent descriptors or `/proc`.

## 4. Frozen configuration — unchanged from C3D

| | |
|---|---|
| requested model | `deepseek/deepseek-v4-flash`, provider `deepseek` |
| documented version | `DeepSeek-V4-Flash-0731` — re-verified 2026-09-10, unchanged |
| observed identity | `deepseek-v4-flash` / `deepseek`, single model and variant per run |
| thinking | enabled | 
| reasoning effort | `high`, `--variant high`, confirmed in telemetry |
| sampling | not controllable — the provider ignores it in thinking mode |
| fixture, task, contract, oracle v2 | unchanged |
| attribution | **`mlr-context-3`** (new) |
| profile | `profile-1` |
| experiment id | `mlr-deepseek-v4-flash-high-full-headroom` under the new attribution identity |

Fixture, task, contract, oracle, model, thinking and effort are **not** changed. Only the instrument
that observes them.

## 5. Budget — N = 3, fixed

Derived from purpose, not from effect size. The question is whether the repaired instrument behaves
correctly on live trajectories, and deterministic route tests are the main proof of coverage — the
field run is complementary. Under C3D the leaking routes appeared in 4 of 5 runs, so three fresh
trajectories are very likely to exercise them again, and each additional run buys diminishing
evidence about an instrument rather than about a phenomenon.

**Expected cost** ≈ $0.09 at peak rates, using C3D's observed $0.027–$0.046 per run. **Hard ceiling
$0.50**, enforced before each slot with a reserve; a trajectory is never cut short for money.

`full` only. **No `contract` call.** No adaptive extension, no outcome-based reruns; an attempt
invalid for setup or harness reasons is re-run into a fresh attempt, bounded at three.

## 6. Pass criteria — all must hold

1. Telemetry required for attribution is complete on every valid run.
2. No harness artifact discloses the arm or the experiment.
3. Every material implementation-derived inbound route is classified correctly or conservatively
   marked `unresolved` — never silently `other`.
4. Direct implementation-source accounting survives any copy or replay actually observed: replay
   raises delivered and does not raise unique.
5. Source, runtime-derived and structural metadata remain separable and are never summed.
6. No new material attribution escape appears in live trajectories.
7. Oracle v2 rejects no product-correct realization.
8. Model identity and variant are stable across every run.

## 7. Fail criteria

Any of: an evaluation artifact visible that was expected hidden; material source text appearing under
a non-source origin undetected; a materially new unclassified route; metadata counted as source;
source counted twice through replay; incomplete telemetry; changed model identity; oracle failure;
ceiling breached. **A failure creates a new identity — it is not patched and continued.**

## 8. What passing authorises

Designing and freezing a paid DeepSeek `full`/`contract` paired experiment. **Not running it.** No
`contract` outcome exists under any model, so paired N will be chosen without any treatment result
in view.
