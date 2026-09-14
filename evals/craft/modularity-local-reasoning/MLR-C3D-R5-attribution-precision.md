# MLR-C3D-R5 — Causal attribution precision

`mlr-deepseek-v4-flash-high-paired-r4` was invalidated by an instrument that was confident and
wrong. This repairs the provenance model it exposed. The experiment stays invalid; its numbers stay
as recorded; the attribution version moves to **`mlr-context-6`**.

## 1. What actually happened

In slot 3 a `contract` trajectory ran

```
python3 -c "import objectstore; print([x for x in dir(objectstore) if not x.startswith('__')]); print(objectstore.__doc__)"
```

and 340 bytes came back: a list of public names, and the module's public docstring. Two lines of
that docstring are also lines of `objectstore/__init__.py`, so they matched the source fingerprint,
so the whole 340-byte output was recorded as **direct implementation source** in the arm whose
treatment is that readable implementation source is withheld.

Thirty-four items later the agent read its own worker log. The log replayed those two lines. The
content-echo index recognised them, handed the *whole item* an `ancestry` basis, and every component
of a 42,915-byte log inherited `implementation-source` — including 34,618 bytes of disassembly.

The headline unique measurand survived at 340 bytes because identity deduplication happened to
collapse the two items. Two other numbers did not: `implementation_source.delivered_bytes` reached
823,885, and the component roll-up attributed 35,470 unique bytes to implementation source. The
runtime channel, where that disassembly belonged, was left reporting **102 bytes**.

So the arm that substituted runtime representation for source was recorded as having read source and
as having barely touched the runtime. Both halves of the paired question were corrupted.

## 2. One defect or two

**Two, and they are separable.**

*Content promoting to origin.* `FORM_ORIGIN` mapped `source-form` to `implementation-source`, and
the live `_command_provenance` consulted dominant content before the request family. Matching bytes
therefore established that source had been read. This one is visible on its own in
`craft-mlr-paired-calibration#1`, where `help(objectstore)` was charged 178 bytes of source in a run
from an earlier milestone — the same defect, eighteen sessions before it invalidated anything.

*Container-scoped propagation.* A settled basis overrode every component's origin with the item's,
and `source_bytes` charged the whole delivered rendering. This one is visible on its own with no
docstring in sight: a genuine source read, echoed verbatim into a 62,456-byte mixed log, charged the
log's whole rendering as source under `mlr-context-5`.

Either defect alone produces a wrong number. Together they produced this one.

## 3. Diagnosis

The architecture already separated content identity, causal provenance, representation form and
delivery route — on paper. MLR-C3D-R2 states it exactly:

> When causal ancestry is mechanically known, provenance follows that ancestry. Content
> characterises the representation and detects contradictions.

and

> A *container* never settles.

Both defects are departures from that doctrine rather than gaps in it. Content did decide origin,
and a container did settle. The repair restores the architecture's own rule; it does not introduce a
new one.

## 4. The invariant

> **A delivered span counts as direct implementation source only when the activity that delivered it
> reached the module's readable source — because the artifact opened was one of its files, because
> the request named one, or because the span replays something that did. Bytes equal to source are
> source-shaped, and that is all they are.**

And its granularity half:

> **Ancestry of an artifact covers what that artifact delivered. Ancestry of content covers the
> spans that replay it, and nothing else in the container they arrived in.**

## 5. What content may still establish

Fingerprints are not removed; their role is bounded.

| question | may content answer it? |
|---|---|
| is this representation source-shaped? | yes — this is what form means |
| does this replay material already delivered? | yes — per component, and per line for source |
| which channel does a rendering of the module belong to? | yes for opcodes, live-object renderings and file names, which cannot exist unless the thing they render was reached |
| did an activity read the module's source? | **no** |
| was the treatment exposed? | **no** |

Three of the four forms evidence themselves. `source-form` is the one that can be produced without
reaching what it depicts — by a docstring, by a model's reconstruction, by a test failure quoting a
line — so it takes the origin of the activity that delivered it.

## 6. What causal ancestry now does

Unchanged in precedence, changed in scope. `artifact-path`, `author` and artifact-scoped `ancestry`
cover the whole item. Content echo covers matched components only, and the item is then labelled by
what most of it is — with the R3 rule preserved that only a form *of* the module may speak for its
container, so file names never relabel anything.

One addition: **request-named versus subject-named.** A path in the request — the file a `read`
opened, the file a `cat` or `git show` named — asserts what the activity reached, and is
artifact-scoped. A path in the answer — where a search found hits, which file a diff is of — is the
representation naming its own subject. That is real evidence, accepted for source when the
delivering activity is not itself a container, but it is span-scoped: a grep excerpt is charged for
its lines, never for the file they came from.

## 7. Granularity

**No new representation was needed.** `_lineage.components` already split a delivered text by line
into disjoint, individually identified components; `mlr-context-5` computed them and then discarded
them whenever a basis settled. The repair consumes what was already there.

One mechanism was added, because a case required it: source components are indexed **per line** as
well as per component digest. A log almost never replays a whole read — it replays part of one, and
a digest of the part matches nothing. Lines are distinctive by construction, since the fingerprint
admits nothing shorter than `MIN_FINGERPRINT`. Byte-level taint was considered and rejected: no
retained case needs it.

## 8. Public contract and docstrings

MLR-C2's decision stands: `__all__`, signatures and docstrings are public surface reachable in both
arms, and `contract` keeps `help`, `pydoc`, `dir`, `inspect`, disassembly, tracebacks and ordinary
experimentation. Nothing was hidden to fix this.

The repair is not "a docstring is never source". Case 3 of the regression corpus reads the same
docstring out of `objectstore/__init__.py` and it *is* source, byte-for-byte identical to case 2
where it is not. That pair is what forbids the shortcut.

## 9. Historical semantics

`mlr-context-5` keeps its meaning and its results. Every record carries the version its numbers were
produced under. The r4 experiment remains `Experiment invalid`, its four completed trajectories and
interrupted fifth attempt unaltered.

`retrospect()` was extended to read boundary-era records, which record the attempt directory
relative to the semantic view. Its output is labelled *retrospective diagnostic analysis — not the
recorded experiment result*, and it is used here for exactly that.

## 10. Evidence

**Deterministic.** Nineteen adversarial cases in `tests/test_causal_attribution_precision.py`,
expectations fixed before the classifier was run: direct read, docstring through introspection, the
same docstring through the source file, disassembly carrying source-equivalent text, model
reconstruction, runtime structure, grep over source, grep over runtime output, artifacts produced
from source and from runtime, log replaying only source, log replaying a small span beside a
disassembly, repeated replay, the contract document, path metadata, `help`, the exact r4 slot-3
command, its worker-log replay, and the defects that shaped R1, R2 and R3. Plus 156 pre-existing
attribution tests, including the repository's own public-surface test, which runs real `help()`, `__all__` and docstring output through the
classifier and asserts none of it is charged as implementation.

**Retrospective.** All 54 retained sessions with a recoverable arm layout — Nemotron calibration,
C3 and C3R pilots, DeepSeek headroom, requalification, the earlier invalid paired series, R4-C3
requalification, and the four completed r4 slots — replayed under both versions:

| | `mlr-context-5` | `mlr-context-6` |
|---|---|---|
| sessions changed | — | **2 of 54** |
| direct source, total | 191,897 | 191,379 |
| direct source, delivered | 4,403,086 | 3,575,819 |
| runtime representation | 407,706 | **441,153** |
| reconstruction | 123 | 123 |
| metadata references | 307 | 307 |
| unresolved items | 1 | 1 |
| contradictions | 0 | 0 |
| uncovered events | 0 | 0 |

Every changed classification:

- **r4 slot 3 (`contract`)** — source 340 → 0, runtime 102 → 35,056, delivered source 823,885 → 0.
  The docstring is no longer source; the disassembly is restored to the runtime channel.
- **`craft-mlr-paired-calibration#1` (`contract`)** — source 178 → 0, runtime 2,154 → 647. The same
  `help(objectstore)` defect. The runtime figure falls because the old code counted the item *and*
  its components: with no component matching the item's origin, the whole 1,685-byte item was added
  as a second runtime component beside the 178 bytes it already contained. Removing a double count
  is not losing signal.

The remaining 25 retained attempts are `harness-failure` records that never recorded an arm layout;
22 carry an empty two-part session. They are unreplayable for a reason that predates this repair.

**Specificity.** 52 of 54 sessions are unchanged, and 191,379 bytes of direct source across the
`full` arms are recognised exactly as before. No `full` trajectory lost source anywhere in the
corpus.

**Sensitivity.** Cases 1, 3, 7, 9, 11, 13 and 18 assert that source is still found through a direct
read, a source-file read of a docstring, a grep over the real file, a copy through a scratch file, a
log replaying a read, a repeated replay, and `git show` naming the file. An unresolved *component*
is now reported in the ledger's audit counts, so source-shaped text nothing can account for is a
flagged open question rather than a silent zero — which is what a boundary escape would look like.

## 11. The measurand

Unchanged: *unique bytes of direct implementation-source representation consumed on correct runs,
per arm*. It was never incoherent. The instrument could not measure it.

## 12. What this does not do

It runs no model and spends no budget. It draws no treatment conclusion from the retained
trajectories — the repaired slot-3 numbers are diagnosis, not a result. It does not requalify the
measurement path in the field, and the changed classification semantics are exactly the kind of
change that a bounded field qualification exists to catch.
