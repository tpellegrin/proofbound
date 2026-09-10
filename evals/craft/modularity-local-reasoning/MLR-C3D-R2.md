# MLR-C3D-R2 — causal representation provenance

The paired DeepSeek calibration executed cleanly and was invalidated by its instrument. This
milestone repairs the instrument, proves the repair against the twelve trajectories that broke it,
and stops before buying another experiment.

## 1. The three cases no single rule survives

All three come from the same paid run and are reconstructed here from the retained sessions, not from
the report of them.

**Pair 5, `contract`.** At part 53 the agent disassembled all four compiled modules and read 14,321
bytes back inline. At part 58 it ran the same disassembly redirected into `/tmp/objectstore_dis.txt`;
the tool returned `     593 /tmp/objectstore_dis.txt` and nothing else. At part 62 it read that file:
**29,499 bytes**, delivered to fifteen later model calls, recorded with origin `other` because the
last path the bytes had passed through was `/tmp`.

**Pair 6, `contract`.** At part 44 the agent disassembled the compiled modules — 32,418 bytes. At
part 66 its own reasoning said *"Wait, in the disassembly:"* and then wrote

```python
path = Path(os.environ.get(_ROOT_ENV, tempfile.gettempdir())) / "objectstore-data"
path.mkdir(parents=True, exist_ok=True)
```

— two lines of `_backend.py`, byte for byte, in a workspace containing no source. Content matching
called them implementation source. They were replayed into eleven later calls. No inbound part in
that session carries them; the only occurrence is the model's own.

**`full` pairs 4 and 5.** A shell command whose argument named `third_party/objectstore-1.4.0`
returned three paths, a version string and a directory entry. 301 and 224 bytes of that were charged
to the primary measurand.

Path-first attribution loses the first. Content-first attribution invents the second — it reports a
source boundary failure in an arm that had no source. Neither rule can be repaired into the other.

## 2. Three questions, kept apart

| dimension | question | decided by |
|---|---|---|
| **causal provenance** | where did the information come from? | the strongest available evidence |
| **representation form** | what do the delivered bytes encode? | the bytes, and nothing else |
| **delivery route** | how did it reach model-visible history? | the tool and the path |

Origins: `implementation-source`, `implementation-runtime`, `implementation-metadata`,
`public-contract`, `application`, `behaviour`, `harness`, **`model-derived`**, `unresolved`, `other`.
`model-derived` is new and is an origin rather than a shrug: text a model wrote is text the model
wrote, however exactly it reproduces something it read.

Forms: `source-form`, `disassembly`, `runtime-structure`, `path-metadata`, `other-representation`,
and `mixed` when two are material and neither dominates. Five substantive forms, each of which
changes a number the experiment reports; `product-output` and `prose` were considered and dropped
because nothing becomes impossible without them.

## 3. Precedence

> **When causal ancestry is mechanically known, provenance follows that ancestry. Content
> characterises the representation and detects contradictions. Delivery route records transport.
> Neither content nor path may overwrite a provenance something stronger has settled.**

| basis | what spoke | may content overrule it? |
|---|---|---|
| `ancestry` | a link to the event that produced the information | no |
| `artifact-path` | the file opened is one of the fixture's own artifacts | no |
| `author` | the model wrote it | no |
| `command-route` | the family of request, with the output checked | yes |
| `content` | nothing stronger had an answer; the bytes decided | — |
| `default` | the kind of part, and no more | yes |

Only three bases settle. A *container* never settles: the worker log's path says where bytes were
sitting, and the workspace is somewhere an agent may write anything, so both leave the question open
for content to answer. That is what keeps the MLR-C3D log-echo repair working while closing the
pair-6 hole.

Across the twelve retained trajectories — 1,193 items — the bases fall out as: 339 artifact-path,
322 author, 304 default, 160 command-route, 66 ancestry, and **2 content**. Attribution now rests on
the weakest evidence in two items out of twelve hundred.

## 4. What is mechanically linked

Two indexes, both links rather than conclusions, both discarded at the end of a session.

**Produced artifacts.** A shell command's redirections (`>`, `>>`, `| tee`), the destination of a
`cp`/`mv`/`install`, and the `write` tool's path are recorded against what the command was doing —
introspection produces runtime representation, a copy of a module source file produces source, a run
produces behaviour, and a here-document or an `echo` produces the model's own text. A later read of
that path inherits it. This is not a shell interpreter: a command that materialises bytes by any
other means is left unlinked, and representation-form detection remains the second line of defence
where the link is missed. Pair 5 is caught by both independently.

**Content echo.** Each item's substantive components carry an order-independent identity, and an
inbound item whose content has been delivered before inherits what it was then. That makes the worker
log a route in all three of its cases at once: a log echoing a source read echoes source, a log
echoing a disassembly echoes a disassembly, and a log echoing the model's own sentence echoes the
model — the last being exactly the case a content rule gets wrong.

Neither index stores anything recomputable from the item list. Whether a reconstruction followed
implementation representation into the session is derived from ordinals at reporting time, and is a
statement about observable order and not about what the model inferred.

## 5. Decomposition and mixture

A delivered text is split **by line**, each line landing in exactly one component, so the parts sum
to the whole and no byte is counted twice. Tool decorations are stripped before every test rather
than only before the source test — the pair-5 read was 29,499 bytes of opcodes behind a `  1: `
prefix, and undecorating for source alone was why it looked like nothing.

A component is material at `MIN_FINGERPRINT` bytes: the size of one distinctive line, which is the
smallest thing that can identify anything and small enough to keep the 122 bytes that made the
source/reconstruction distinction necessary. A form is claimed when it is at least half the delivered
text; where two are material and neither dominates the label is `mixed` and the components carry the
numbers. **No share threshold decides an origin** — origin is decided by precedence, and the shares
are used for the form label and for contradiction detection.

Measured shares over the retained corpus: material forms range from 0.69 to 1.00 of their items, so a
half threshold sits well clear of every observed case rather than being tuned to them.

## 6. Escape detection

Detection, never classification. `contradiction()` asks one question — given how weakly this origin
is evidenced, does the delivered representation contradict it? — and returns a reason or nothing. It
reassigns no item.

Only weakly evidenced origins can be contradicted. A source-shaped body under a settled runtime or
model ancestry is *the finding*, not an escape; flagging it would leave the instrument unable to see
the thing it was repaired to see. The predicate that failed on pair 5 required metadata bytes to be
**zero**; 3,188 bytes of `dis` header over a 89% opcode body defeated it. It is replaced by a share
comparison, which is what the metadata promotion rule already used.

## 7. Retrospective diagnosis of the invalid run

`pb_mlr.py retrospect` re-attributes a completed series' retained sessions under the attribution in
force today. **It is diagnosis, not a result.** The source record is unmodified and its numbers stand
as what that experiment measured; the recomputed numbers are labelled with both telemetry versions so
the two can never be conflated. Full output:
[`craft-mlr-deepseek-v4-flash-high-paired-retrospective.json`](../../results/craft-mlr-deepseek-v4-flash-high-paired-retrospective.json).

| pair | arm | source, recorded → R2 | runtime, recorded → R2 | reconstruction |
|---|---|---|---|---|
| 1 | full | 5,822 → 5,822 | 1,495 → **0** | 0 |
| 1 | contract | 0 → 0 | 623 → **0** | 0 |
| 2 | full | 5,822 → 5,822 | 1,495 → **0** | 0 |
| 2 | contract | 0 → 0 | 32,380 → 32,380 | 0 |
| 3 | full | 5,822 → 5,822 | 14,172 → 12,575 | 0 |
| 3 | contract | 0 → 0 | 19,645 → 18,859 | 0 |
| 4 | full | **6,123 → 5,822** | 817 → **0** | 0 |
| 4 | contract | 0 → 0 | 32,679 → 31,984 | 0 |
| 5 | full | **6,046 → 5,822** | 499 → **0** | 0 |
| 5 | contract | 0 → 0 | **17,185 → 43,820** | 0 |
| 6 | full | 5,822 → 5,822 | 28,639 → 27,292 | 0 |
| 6 | contract | **122 → 0** | 33,446 → 32,664 | **123** |

The three known defects close exactly as expected: pair 5's runtime rises by the 29,499 bytes that
escaped, pair 6's direct source falls to zero with 123 bytes appearing as reconstruction, and the two
`full` over-attributions return to the invariant 5,822.

**A fourth correction was not expected.** Every arm's runtime figure fell, several to zero, because
`find` listings of the compiled package were being charged to the runtime channel for containing the
substring `_store`. They are file names and are now metadata. The instrument's `_PATHISH` pattern
matched `.py` and not `.pyc`, so a listing of the compiled module was invisible to the metadata rule
and visible to a bare name match — which is the same defect as the other three, in a fourth costume:
a weak signal deciding a question a stronger one could answer.

**Sweep.** All 1,193 items across the twelve sessions were checked for opcode density, source
fingerprint matches, internal-name density, large unclassified inbound parts, temporary-file reads,
generated-file reads, worker-log reads, version-control commands and binary inspection. Contradictions
**0**, unresolved **0**, unexplained material items **0**.

## 8. Runtime identity

The run recorded two runtimes where it had one. Eleven slots produced runtime digest `4b7ada46…` and
the first produced `f8a6c839…`; the difference was twenty-five bytes of `_store.pyc`, all of them
`marshal`'s interned-string flag for the name `last` and the reference indices that shift behind it.

`runtime_structure` hashes each compiled object and every code object nested inside it — name,
argument counts, flags, bytecode, names, varnames, free and cell variables, filename, first line and
constants — with the bytecode magic number, because bytecode is version-specific. Over the twelve
retained materialisations it returns **one** value where the byte digest returns two, and that value
is the one the current fixture source compiles to: the retained runtimes are structurally the
implementation this repository still holds.

The byte digest is kept. It answers a different question, and the contrast is the evidence that a
second identity was needed. `runtime_unchanged` now checks the structure, so an agent that rewrites a
compiled file is still caught while a re-materialisation is no longer accused. **What this claims:**
the compiled objects have the same structure, under one interpreter, for the normalisation written
down. **What it does not claim:** semantic equivalence in any wider sense, or comparability across
interpreters. MLR-C2's statement that the digest is reproducible across materialisations was wrong,
and is corrected here rather than quietly dropped.

## 9. Three identity bindings repaired while here

The configuration bound `external_test.py` while `external_test_v2.py` was the oracle being run, so a
change to the oracle in force would not have moved the frozen identity. The interpreter was not bound
at all. A series had no revision, so a repaired instrument would have inherited the name of the
series it invalidated. All three are now bound, and attribution semantics are versioned
(`mlr-context-4`): a record carries the version its numbers were produced under, so a later
classifier cannot silently reinterpret an earlier one.

## 10. Scope, and what was deliberately not built

No repository-wide provenance graph, no information-flow database, no context-graph protocol, no new
truth layer, no new principle. This is evaluation-local measurement infrastructure, and it stays
local until an unrelated experiment independently needs it (`P7`). Only the link that cannot be
recomputed is retained, and the conclusions drawn from it are derived at reporting time (`P3`). The
representation layer names no fixture, no arm and no milestone; the fixture's own vocabulary is
supplied by its caller and asserted by a test.

## 11. Limits

Paraphrase, summary and translation remain invisible to content matching, and the instrument says so
rather than reporting their absence as zero. Ancestry is only as complete as the redirection, copy and
here-document forms it parses; a command that materialises bytes another way is left unlinked and
falls back to form detection, which is a real gap and is stated rather than papered over. `contract`
remains **source-hidden, not implementation-hidden** — the compiled runtime is deliberately
introspectable, an agent that disassembles it recovers a rendering of the logic, and two of six
`contract` runs did exactly that.

The regression corpus the repository carries is the six derived fixtures under
`fixture/trajectories/`. The twelve full sessions are retained outside it; if that archive is lost,
the retrospective cannot be re-run and only the fixtures survive.
