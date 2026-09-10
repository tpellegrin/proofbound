# MLR-C3D-R3 — experimental hermeticity and universal inbound attribution

Two repairs, deliberately not conflated. One is about whether information that reached the agent was
attributed consistently. The other is about whether the treatment controlled what there was to reach.
A perfectly classified source leak still invalidates an experiment.

## 1. What the R2 qualification found, recovered from its sessions

| | measured | where |
|---|---|---|
| a real source exposure | **3,909 B** | `contract` 2 — four `tool:read` items, basis `content` |
| a runtime escape | **3,632 B** | `contract` 3 — one `tool:grep`, origin `other`, basis `command-route` |
| a minority in a log | **250 B** | `contract` 2 — one `tool:read` of `worker.log`, origin `harness` |
| a path over-attribution | **1,382 B** | `full` 1 — one `tool:glob`, origin `implementation-source`, 0 source lines |

All four reconstructed from the record and the retained sessions, not from the handoff.

The first is not an attribution bug. The agent ran `find / -name "objectstore*"`, the machine
answered, and it read the module. The instrument reported that correctly. **The treatment failed
environmentally**, and that is a different class of defect from the other three.

## 2. Attribution: one boundary for every transport

`grep` and `glob` never reached the precedence table that `read` and `bash` obeyed. Nothing about
that is specific to search — it is what happens when provenance is decided per tool — so the repair
is a normalisation boundary rather than two more classifiers.

```
tool result → adapter → { text · artifact · referenced paths · produced files · author }
            → one resolver → origin · form · components → route label → detector
```

Each adapter answers the same small set of questions; one resolver answers the rest; tool identity
survives as the route, which is where it belongs. The registry of adapters **is** the coverage
boundary: an unrecognised tool or part type is recorded `covered: false` so a test fails on it rather
than an experiment quietly losing evidence.

**Inventory, from the eighteen paid sessions.** Part types carrying text: `tool` (831), `reasoning`
(375), `text` (110), plus `patch` (450). Tools: `read` 405, `bash` 288, `edit` 59, `write` 55,
`todowrite` 14, `grep` 6, `glob` 5. Every one has an adapter, and a coverage test says so.

**Search semantics.** A search that returns the module's *lines* is source. A search that returns its
*names* is metadata. A search over an artefact produced earlier inherits that artefact's history. The
tool is the same in all three cases, and the delivered bytes decide — which is the rule that closes
the `glob` over-attribution generically rather than for the one shape that produced it.

**Two recognisers were wrong in the field.** Search-hit line labels (`Line 150: `) were never
undecorated, so 23 lines of opcodes delivered through `grep` were not seen as a disassembly at all.
And two internal names in a line counted as a rendering of a namespace, where prose says *"we set
`_ATTEMPTS` and `_FANOUT`"* and the one real `dir()` line in the corpus carries three. Both are
corrected from the evidence.

**Two rules changed, and their tests changed with them.** A search is attributed by what it returned
rather than by where its matches live. And a request family now outranks bare file names, so a test
run that prints one module path stays a test run — with the names still counted as a component.

## 3. Components carry their own origins

An item is not one thing. A log that echoes a namespace dump is a log containing a namespace dump:
calling the whole thing harness loses 249 bytes of the module's interior, and calling the whole thing
runtime overstates thirteen kilobytes. So each **material** component is attributed, the headline
origin describes only what the container mostly is, and the module-internal channels are counted from
components rather than from headlines.

Under a settled basis every component inherits that history — a model's own sentence is the model's
however exactly it reproduces something, and a module source file is source throughout. Otherwise
each component takes the origin its form implies.

## 4. Materiality, not share

The rule this replaces asked whether a representation was *most* of the item carrying it. It missed
3,632 bytes of opcodes at 35%, which is the same mistake in a smaller costume as the 29,499 bytes
lost behind a temporary path.

Each form is now judged in its own unit against a floor derived from what its recogniser needs to be
distinctive at all:

| form | floor | derivation |
|---|---|---|
| source | 1 line | a fingerprint line is already ≥ 24 characters and distinctive by construction |
| namespace / structure rendering | 1 line | the one real case is 249 bytes on a single line |
| disassembly | 3 lines | an opcode mnemonic can appear in prose; three lines is a rendering |
| file-name metadata | 1 reference | a reference is the unit |

No universal percentage replaces the old one. Share survives in exactly one place — deciding what to
call the *container*, which is a different question from what to count.

**The detector stays separate from the classifier.** It re-derives materiality from the recorded form
counts rather than trusting the component list, so it fails if the two disagree; it reassigns nothing;
and it does not fire on an item already marked `unresolved`, which would double-count one uncertainty.
It is a safety net. In the eighteen-session corpus it fires zero times, which is what a safety net
looks like when the architecture underneath it is right.

## 5. Hermeticity: the second condition

> The prepared workspace withholds the controlled evidence, **and** before execution no unintended
> alternative copy of that evidence — nor of the oracle, the reference solution, prior samples or
> earlier results — is reachable through the ordinary filesystem capabilities the agent is granted.

**Reachable, operationally.** The evaluated agent gets a shell, absolute-path reads, `find`, `grep`,
`glob` and Python. `run_worker.py` launches `opencode --dir <workspace>` with cwd there, but `bash` is
not confined by `--dir`: a `find /` is an ordinary command and one was run. So *reachable* means the
host filesystem, and the scan is honest about the gap between that and what it examines — it reports
its roots, its exclusions and what it could not read, and claims absence over nothing else.

**Identity, not filename** (`§9`). A directory whose name matches proves nothing. A file is a finding
when its bytes are the controlled artefact's bytes, or when it carries three of its distinctive
lines, or — for a session database or a result record, which have no fixed bytes — when it contains
the experiment's own marker. Names index the haystack; they are never the evidence. A file called
`_store.py` containing unrelated code is not a finding, and there is a test for that.

**This is not security.** No claim about process isolation, kernel boundaries, `/proc`, side channels
or an agent trying to escape. Ordinary engineering tools do not find a second copy; a determined
agent still could.

## 6. The contaminated machine, measured before it was cleaned

The checker was built first and run before anything was removed, because one written after a cleanup
proves nothing. Result:
[`craft-mlr-hermeticity-preflight-contaminated.json`](../../results/craft-mlr-hermeticity-preflight-contaminated.json).

**Status `contaminated`, 150 findings.**

| root | category | count |
|---|---|---|
| temporary directory | controlled evidence | 72 |
| temporary directory | reference solution | 8 |
| evidence archive | controlled evidence | 36 |
| evidence archive | prior sample | 18 |
| repository | controlled evidence | 4 |
| repository | experiment result | 8 |
| repository | oracle | 2 |
| repository | reference solution | 2 |

**Twelve** stale arm materialisations, not the four already known. The one the `contract` agent
actually read — `tmpwz_nk96m`, created 2026-09-09 at 14:00 — is among them, so the answer to *would
this have refused the R2 qualification before it launched?* is **yes**, and the exact evidence is
recorded. That qualification's historical result is unchanged; this says only that its environment was
already violated before its first call.

**Thirty-six** of those copies were inside the evidence archive created earlier in this session, when
whole FULL arm workspaces were preserved. The observer put them there.

## 7. Cleanup, and what cleanup cannot reach

The leak was not a bug at any call site. `materialise` takes a destination and has no owner, so an
exploratory script that made one and exited left the implementation readable on the host for a day.
Cleanup now lives with creation, in a context manager that removes the directory however the block
ends. The recogniser looks for the *shape* — a workspace beside a compiled runtime — one level down,
because the twelve were named `arm`, `full`, `contract`, `c`, `f` and `again`; a name-based rule would
have missed a third of them. It never matches retained evidence, which is the whole point of keeping
the two apart (`§36`).

Redundant archived source trees were pruned after confirming byte-identity with the fixture. Session
databases, logs, compiled runtimes and the agents' own edits were kept, and the eighteen-session
retrospective still runs against them.

**150 findings became 34.** Result:
[`craft-mlr-hermeticity-preflight-after-cleanup.json`](../../results/craft-mlr-hermeticity-preflight-after-cleanup.json).

What remains is structural, and cleanup is the wrong tool for it:

- **18 prior-sample session databases**, which are the evidence of eighteen paid trajectories and must
  not be deleted;
- **16 repository artefacts** — the fixture's own source, both oracles, the reference solution and
  eight result records — which are the experiment's source of truth.

Both are reachable by the same ordinary search that already reached a stale workspace once. Zero of
eighteen paid trajectories reached them, which is luck rather than control: the `find` that leaked
was truncated by `head -50` and the repository's copy sits further down the same listing.

**Therefore the environment is not hermetic, the preflight does not pass, and no paid call was made.**
Cleanup plus preflight is stronger than either alone precisely because it can say this instead of
assuming it.

## 8. Per-slot, not per-series

Hermeticity is a precondition of the slot. The slot before it is one of the things that could have
left a copy behind, so every semantic slot establishes its own environment. A refusal is an
infrastructure precondition failure, not a semantic one: the slot stays open under existing resume
semantics and no sample is consumed. The rule is frozen as its own identity and bound into the
series, so widening the roots or declaring an exposure changes the experiment rather than quietly
relaxing it.

## 9. Eighteen-session retrospective

[`craft-mlr-eighteen-session-retrospective.json`](../../results/craft-mlr-eighteen-session-retrospective.json).
Both paid series, re-read under `mlr-context-5`. Historical records unchanged.

| | recorded | under R3 |
|---|---|---|
| paired, pair 5 `contract` runtime | 17,185 | **42,987** |
| paired, pair 6 `contract` direct source | 122 | **0**, with 123 B reconstruction |
| paired, `full` 4 / 5 direct source | 6,123 / 6,046 | **5,822 / 5,822** |
| qualification, `full` 1 direct source | 7,204 | **5,822** |
| qualification, `contract` 3 runtime | 36,273 | **39,361** |
| qualification, `contract` 2 runtime | 431 | **496** |
| qualification, `contract` 2 direct source | 3,909 | **3,909** |

Contradictions 0, unresolved 0, uncovered events 0, across all eighteen.

The last row is the one that matters most. The genuine environmental leak **stays** 3,909 bytes of
implementation source in a `contract` arm. An instrument that made it disappear while tidying up the
other three would have been worse than the one it replaced.

## 10. What is unchanged

R2's direct-source and source-equivalent-reconstruction semantics, unchanged and now regression-held:
`contract` direct source is zero when the source is absent from the reachable environment and the
model reconstructs source-form text from bytecode. Runtime structural identity, unchanged and not
reopened. `_profile.py`, untouched — its independence has now survived three semantic attribution
failures and one environmental one. The cost-basis discrepancy, still open and still out of scope.

## 11. Limits

The scan examines the system temporary directory, `/tmp`, the repository and any evidence archive it
is given. The agent can read further. Fifty paths could not be read and are reported as such rather
than assumed empty. Symlinked *files* are followed to what they point at; symlinked *directories* are
not walked. Paraphrase and translation remain invisible to content matching. Ancestry is only as
complete as the redirection, copy and here-document forms the adapter parses.

And the largest one: **this experiment cannot currently be run hermetically on the machine that hosts
its own repository, by an agent with unrestricted filesystem reads.** Closing that is an environment
design decision — running the subject where it cannot read the repository or the archives — and is
deliberately not built here.
