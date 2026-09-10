# MLR-C3D-R — the repaired instrument, requalified

Three `full`-only runs under the unchanged DeepSeek V4 Flash configuration and the repaired
attribution. **All three correct, zero material attribution escapes, zero unresolved items, $0.094
against a $0.50 ceiling.** All eight pre-registered pass criteria hold.

## 1. The defect, and why it was not two special cases

MLR-C3D failed because the measurement **asked how text arrived and treated the answer as what the
text was**. Implementation information was counted as harness because the file it arrived in was a
harness file; a module's file names were counted as behaviour because a shell command produced them.

Patching `worker.log` and `git ls-files` would have left the defect intact for the third route nobody
has met. Origin and delivery route are now separate axes: the route records the mechanism, the origin
is settled against the delivered bytes.

## 2. Representation origin

`implementation-source` · `implementation-runtime` · `implementation-metadata` · `public-contract` ·
`application` · `behaviour` · `harness` · `unresolved` · `other`.

**Source is recognised by content.** The module's 68 fingerprint lines — every source line of at
least 24 characters — share nothing with the application, the tests, the contract, the task, the
reference solution, the hidden oracle or the worker protocol, verified by test. Text reproducing them
verbatim carries their origin however it travelled, and tool decorations (`path:lineno:`, line
numbers, diff markers) are undecorated before matching.

**Lineage supplements the path; it does not overrule it.** Where the path already identifies a module
file the whole delivered rendering counts, because a line-numbered read of a 2,200-byte file
delivered 2,697 bytes of that file. Where the path says otherwise, only demonstrably verbatim lines
are claimed.

**Metadata is its own unit and never source bytes.** A listing naming a private module file discloses
that the module has one; fifty repetitions of a filename must not accumulate into thousands of source
bytes. Mixed artifacts are decided by share: a listing that is mostly file names becomes metadata; a
test run whose traceback names one file stays a test run with the disclosure recorded.

**Replay costs context without inventing information.** Source identity is taken over matched lines,
order-independently, so the same source read directly and echoed through a log is one unique
representation and two deliveries.

**Unknown is not zero.** Inbound text that plainly discloses the interior but resolves to no
implementation origin is marked `unresolved`. Model-authored text is excluded: it is downstream of
what the model already consumed, not a route by which information enters.

## 3. The boundary, stated

Covered: direct reads, search excerpts, copies through scratch files, harness log echoes, `git show`,
shell redirects — every route that moves the bytes unchanged. Not covered: paraphrase, summary and
translation, which are invisible to content matching and are recorded as unresolved rather than
guessed at. Derived-but-not-reproduced text — disassembly, `help()`, `vars()` — keeps its own origin
and is never promoted to source.

## 4. Observer isolation — what holds and what does not

| | |
|---|---|
| OpenCode session database | outside the workspace |
| hidden oracle, reference solution | absent during the run |
| prior samples | separate temporary trees, removed after each attempt |
| arm / experiment name in any harness artifact | **none** — treatment blindness verified by test |
| `worker.log` | **inside the run root, and it cannot move here** |

DSD's `resolve_run_path` requires the log under the run root and the evidence gate reads it from the
launch reservation, so relocating it means changing the attempt layout — outside this milestone. The
repair is therefore measurement-side, and a test pins the channel so it cannot be quietly forgotten.

**Threat model.** This preserves experimental conditions against ordinary agent tooling — reading
files, searching, running commands. It is not a sandbox and claims nothing against a process that
inspects process tables, parent descriptors or `/proc`.

## 5. Retrospective note — C3D is not recomputed

Re-read under the repaired model, the C3D escapes carried **no verbatim source**: the worker log
echoed the *paths* the agent had read, not their contents. The leak was structural metadata, narrower
than "source echoed back". C3D's recorded numbers are unchanged and its verdict stands; this is
explanatory only.

Note also that the repaired instrument can report a *different* source figure than the old one on the
same trajectory, because it de-duplicates replayed source by identity. Historical rows keep the
accounting they were measured under.

## 6. The requalification

| run | correct | source unique | source delivered | runtime | metadata refs | contract | application | calls | input | cost | s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | yes | 5,822 | 93,152 | 62,940 | 7 | 2,994 | 12,775 | 21 | 35,410 | $0.0353 | 104 |
| 2 | yes | 5,822 | 87,330 | 1,003 | 10 | 3,945 | 12,423 | 22 | 25,328 | $0.0321 | 109 |
| 3 | yes | 5,822 | 75,686 | 1,461 | 7 | 2,994 | 13,083 | 19 | 21,707 | $0.0266 | 113 |

3/3 correct, every profile complete, identity and variant stable, all peak-window. Derived spend
**$0.094**; OpenCode's own figure $0.033, retained beside it and not substituted for it.

**Source unique is 5,822 in every run** and delivered is 76–93 KB — the replay volume the old
accounting could not see. Runtime-derived representation varies from 1,003 to 62,940 bytes and stays
in its own column. Metadata references, 7 to 10 per run, are now counted at all.

## 7. Field audit

**Material escapes: 0. Unresolved: 0. Oracle rejections: 0.**

The C3D channel reappeared and was measured. Run 2 read its own `worker.log` — 5,836 bytes naming
`_backend`, `_errors` and `_store`. Under C3D that was an invisible escape. Under the repaired
instrument the item stays `harness` by share, with **433 bytes of metadata references recorded on
it**, so the disclosure is counted rather than lost. That is the repair demonstrated on a live
trajectory, not only in a fixture.

Between one and two items per run were attributed by content rather than by path — the lineage
mechanism doing work in the field. Nine model-authored items named internals; every one in a run that
had consumed implementation, and **zero** in a run that consumed none.

## 8. Verdict

All eight pass criteria hold. The instrument is requalified for the paired experiment.

**What that does not establish.** Not a treatment effect: no `contract` run exists under any model.
Not that paraphrase routes are covered — they are not, and are recorded as unresolved. Not that the
observer channel is closed — it is measured, not removed.
