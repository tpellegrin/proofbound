# Executor start-up — 2026-09-24

**Explained, reproduced and repaired for new runs.** The contradictory challenge's reviewer failed
because the pinned executor refused the requested model. It rejects a model that its cached copy
of the live model catalogue lists as `deprecated`, and the author's attempt had written that copy
into the staged home the reviewer shared. The npm install and lock activity recorded in
[live-qualification-2026-09-24.md](live-qualification-2026-09-24.md) were correlated with the
failure, not its cause. They are removed anyway, as hardening.

This milestone made no provider request and spent nothing. The original plan, its trial outcomes
and the published record are unchanged. Two corrections to that record are made here.

## Verified first

The checkout was `aa15c34`, equal to `origin/main`: the owner had pushed the previous commits.
The authorized plan (`e585ee84…` on disk, digest `8370c2d4…`) and the proposal (`a1104568…`) were
unchanged. The retained evidence held six terminal records: three attempts, each also copied into
the evidence directory. No executor process was running.

## Observed in the failed run's retained evidence

- **The reviewer's failure.** It exited 1 after 1.005 s. Its session holds one user message and
  no assistant message. The session was created at 00:37:03.723, the prompt text was stored at
  03.979, and the process was gone by 04.012. It printed `UnknownError`, `err_114f4b40`, and
  nothing else. The executor's log file has no line from it, and lacks the author's last ~6.3 s.
- **The cached catalogue.** The shared staged home held `.cache/opencode/models.json`, written at
  00:35:17.097, 7 s into the author's attempt. It lists `deepseek-v4-flash` with
  `status: "deprecated"` and prices of $0.15 / $0.60 / $0.003 per million tokens.
- **Which catalogue the successful launches used.** Trial 1 and the author both used the executor's
  bundled catalogue, not the fetched one. Their executor-reported costs equal the bundled V4 Flash
  prices ($0.14 / $0.28 / $0.0028) to the last digit:
  - Trial 1: 13,373 × 0.14 + 8,260 × 0.28 + 194,304 × 0.0028, per million tokens, = $0.00472907.
  - Author: 29,767 × 0.14 + 11,336 × 0.28 + 425,728 × 0.0028, per million tokens, = $0.0085335.

## Reproduced with the pinned executor, credential-free

A loopback stand-in answered for the provider through `OPENCODE_CONFIG`, and the credential was a
dummy. Everything else — executor bytes, argv, minimal environment, staged home, and the
executor's own start-up — was production.

| What | Result |
|---|---|
| The failed run's own cached catalogue, in a fresh home | 3/3: exit 1 in ~1.0 s, **0 requests**, `UnknownError`. The logged cause is `ProviderModelNotFoundError: Model not found: deepseek/deepseek-v4-flash. Did you mean: deepseek-flash, deepseek-v4-pro?` |
| The same, with `OPENCODE_DISABLE_MODELS_FETCH` | 3/3 fail: a cached catalogue wins over the bundled one |
| No cache, fetch disabled | 3/3 exit 0; the bundled catalogue lists the model; no cache is written |
| Front door, pre-repair code, DeepSeek profile, cold home | 3/3 **first** launches fail identically: the refresh landed ~2 s in, before the model lookup. In trial 2 it took 7 s and the author won that race |
| A 1-second failure without `--print-logs` | 3/3 leave **0 lines** in the executor's log file; stdout has only the reference |

The code paths were read in the pinned bytes, not inferred:

- **Catalogue.** It is read from the cache when one exists, and otherwise from the catalogue
  bundled in the binary. Unless `OPENCODE_DISABLE_MODELS_FETCH` is set, a background refresh from
  models.dev runs at start and every 60 minutes, rewriting the cache. When the executor builds
  provider state it applies `if (status === "deprecated") delete`.
- **The error.** A route defect with no handler becomes `Unexpected server error … ref`. The cause
  is logged only under that reference.
- **The plugin install.** On every configuration load, the executor writes a `.gitignore` in each
  configuration directory. The directories are:
  - the global one (`~/.config/opencode`);
  - any `.opencode` from the project up to its worktree root, unless project config is disabled;
  - `~/.opencode`;
  - `OPENCODE_CONFIG_DIR`, if set.

  Then, for each directory it can write, it forks a **detached** install of `@opencode-ai/plugin`
  at the executor's own version, 1.18.29. The install's failure is only a warning. It is awaited
  only when custom tools or plugins exist, which no run here has, so it cannot fail a model step.
- **What the install fetches.** Trial 1 resolved 32 packages from registry.npmjs.org at install
  time, each with a registry-supplied sha512 and no pinned lockfile. They include native optional
  builds. Install scripts are ignored. With the registry unavailable, npm retries for ~70 s and
  then logs the warning.
- **The install lock.** The lock is held by the executor process that runs the install: its meta
  pid is the worker's pid. Its heartbeat **never advanced** over a 55-s hold, so it looks stale
  after 60 s even while its holder lives. Process exit leaves it behind.
- **What breaks a stale lock.** The launcher's own post-attempt `opencode session list` is a second
  executor process in the same home, and it starts the same install. Against a lock 86 s old, it
  created `.lock.breaker`, removed the lock and exited 0.51 s later, leaving only the breaker. That
  is trial 2's state at 00:36:25.745, 0.61 s after the author exited. The project row updated at
  00:37:04.565 fits the same post-attempt listing for the reviewer.
- **Processes.** No executor process outlived its attempt, whether in probes sampled every 0.1 s
  or in front-door launches, where the host sweep found nothing running. Background work is
  abandoned at exit, and what persists is files: the catalogue cache, the lock and the breaker.
- **State shared across one run's attempts.** The staged home (configuration directory, catalogue
  cache, locks, executor log file, snapshot repository, credential copy), the session database and
  the runtime `tmp`.

**Plausible, not established.**
- **That `err_114f4b40` was this error.** Every observable matches: failure at the first model
  step, about 30 ms after the prompt was stored; no request; exit 1; the same reference form. The
  reviewer's home held the catalogue that produces it every time. Its own detail was not kept and
  is not reconstructed.
- **Why the heartbeat stands still.** The code passes a `new Date` built once to a repeated
  `utimes`. That matches the observation, but was not tested separately.

**Unresolved.** Whether the provider still accepts `deepseek-v4-flash`. It did between 00:33 and
00:37 UTC, and calls the routing temporary. Nothing here tested it.

## The repair

New runs carry `executor.startup`: the DeepSeek revision `2026-09-24` (same provider facts and
prices as `2026-09-23`) and every newly resolved local profile. Implementation is in
`scripts/_executor_startup.py`, and the launcher enforces it in `scripts/_supervised_launch.py`.

| Guarantee | Mechanism |
|---|---|
| The executor uses the catalogue in its pinned bytes | `OPENCODE_DISABLE_MODELS_FETCH`; a launch with any cached catalogue is refused |
| No npm dependency is fetched or resolved | `start` stages the configuration directory with the two files the executor writes itself (byte-identical to those in the trial homes). The boundary denies writes there and to the catalogue cache, so the executor's own writability check skips the install. No npm dependency is used, so there is none to pin |
| Failures keep their cause | `OPENCODE_PRINT_LOGS`: the executor's log goes to stderr, which the launcher already writes to the attempt's private `worker.log` |
| An attempt inherits nothing unresolved | Before a slot is reserved, the launcher refuses a missing or changed configuration directory, a cached catalogue, any lock or breaker, a `.opencode` directory, or a boundary without the rules, naming each |
| Diagnosable afterwards | `executor-state.json` beside `worker.log`: the state before and after, and the host sweep. It records names, modes, times and digests, never contents. It stays private, because neither exporter's allowlist includes it |

Revisions `2026-09-09` and `2026-09-23` are byte-for-byte as before (`7aa8ef0d…` reproduces), and
started runs launch exactly as they did. The catalogue change fixes the demonstrated cause. The npm
change is hardening. `--print-logs` is diagnostics. The executor's own cost field still uses the
bundled V4 Flash prices, and Proofbound does not use that field.

**Verified on the pinned executor, inside the real boundary, through the front door.** The
DeepSeek profile used a dummy credential and the stand-in provider:

| | Result |
|---|---|
| Before the repair | 3/3 first launches failed |
| After, real npm registry | 3 runs × 2 consecutive launches (author, then reviewer): 6/6 completed |
| After, npm registry unavailable (recording stand-in) | 2 runs × 2 launches: 4/4 completed, **0 registry requests** |
| After, every launch | No catalogue written, no lock directory created, configuration directory unchanged, executor log in `worker.log`, host sweep found nothing running |

`tests/test_executor_startup.py` makes these regressions. It also covers each refused state, a
host-stopped attempt that leaves nothing to inherit, and a lookup failure whose cause survives. It
also pins the executor behaviour itself: the deprecated fixture fails, and a fixture that differs
only by `status` succeeds.

**Bridge to the tool-loop observation.** Trial 1's start-up was a writable directory with the
install running and the bundled catalogue. The repaired start-up is a staged, protected directory
with log redirection and the bundled catalogue. The executor's three requests under each were
byte-identical after normalising paths and identifiers: the same model, `reasoning_effort: high`,
`max_tokens: 32000`, `top_p: 0.95`, the same 10 tools, and the same system prompt and messages.
So the repair changes nothing the model sees.

## Correction 1: what the requirements challenge could show

The suite's findings-format example read
`{"requirements": ["R2", "R3"], "witness": ["a", "a", "b"]}`. That is the contradictory case's
defect and a valid witness for it. It appeared in every author's and reviewer's goal, in all three
cases, and the author's proposal in trial 2 repeated it. Two questions follow, answered separately:

- **Can a reviewer independently discover the contradiction?** That trial could not show it: the
  answer was in the goal.
- **Can a reviewer verify or challenge a finding already proposed?** At most this, and even that
  is confounded: copying the example would have graded correct.

The coherent control and the dispatch reviewers saw the same example; a reviewer copying it there
would have reported a false finding.

Repaired for new plans, as a new suite identity. The example is schematic, and each challenge grade
records `exposure`: whether a witness it gave was already in the reviewed proposal or the goal,
checked on the bytes its scope baseline records. The author's proposal is not hidden, because it is
a normal production input. So the case measures the production-path challenge — verify or find —
and says which, per trial. Unassisted discovery would need a separately identified setup, in which
the reviewer sees only the owner's text. That setup is not proposed.

## Correction 2: the cause

The earlier record's blocker section is accurate as an account of what was observed. Its finding —
that the executor's start-up depends on an undeclared npm download — is true, but that download was
not the cause of the failure. The cause is above.

## Credentials

The only real-credential copies are the four staged homes of the 2026-09-24 runs, each mode
`0600`. None is needed. The old plan cannot be continued: its settings predate the repair, and its
runs would now start with the fetch enabled. A new proposal starts fresh runs. The homes are
evidence, so remove only the credential file:

```bash
rm /private/tmp/pb-workflow-l3xavqwl/home/.local/share/opencode/auth.json   # tool-loop (completed)
rm /private/tmp/pb-workflow-yz7ke8um/home/.local/share/opencode/auth.json   # contradictory (blocked)
rm /private/tmp/pb-workflow-ayjqea4h/home/.local/share/opencode/auth.json   # coherent (not run)
rm /private/tmp/pb-workflow-kzmrs7ob/home/.local/share/opencode/auth.json   # dispatch (not run)
```

The source entry in `~/.local/share/opencode/auth.json` is shared and untouched. Every other
`auth.json` under `/private/tmp` created in this milestone held only a dummy key, checked by marker
without reading values.

## Tests and the next proposal

The canonical suite, `python3 -m unittest discover -s tests -t .`, ran once, serially, on Python
3.10.14, macOS arm64, at clean commit `91a472e`: **1,425 tests, OK, none skipped**, in 1,112 s.
The real-executor and boundary tests ran, because the pinned build and `sandbox-exec` were
available. The new regressions error on `aa15c34`, where the guarantees did not exist. Two
exceptions: the executor-behaviour test passes there, because it characterises the pinned bytes;
and the answer-free goal test fails there on content.

The continuation proposal is frozen from `91a472e`, NOT authorized:
`evals/qualification/proposals/2026-09-24-deepseek-v4-flash-high-continuation/`, digest
`d591a148…53ee97`. It covers three trials, at most 17 launches and $0.85 derived, with the tool
loop carried forward through the bridge above.

## What this does not establish

- That any model can do the work.
- That the provider still serves the legacy name.
- That `err_114f4b40` was this error, beyond the match described above.
- Anything about the executor's behaviour with plugins or custom tools, which no run uses.
