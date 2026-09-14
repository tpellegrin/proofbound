# MLR-C3D-R6 — live known-answer provenance calibration

Frozen before any semantic call. A new identity. The R5 field qualification stays **incomplete**,
the r4 paired experiment stays **invalid**, and neither is amended or resumed.

## 1. What is missing, and why waiting was the wrong design

R5 established three things live under `mlr-context-6`: genuine source ancestry is recognised,
a 48 KB mixed worker-log read stays component-scoped, and runtime/disassembly material is channelled
correctly — with clean audits and an intact boundary. One thing it did not establish:

> source-shaped text delivered through a non-source causal path must not become direct
> implementation source.

It could not, because neither `contract` trajectory produced a single byte of source-shaped text
across 241 attributed items. R4-C3's contract slots had done the same. **Three of five live contract
trajectories across two milestones produced no source-shaped text at all**, so a design that waits
for the case to arrive by chance is not a design.

That is the mistake this milestone corrects: instrument coverage was allowed to depend on what an
autonomous agent happened to choose.

## 2. Why controlled steering is legitimate here

The object under test is `mlr-context-6`, not DeepSeek's spontaneous debugging strategy. For a
**treatment experiment**, instructing the agent would contaminate the question — what the agent
chooses *is* the measurement. For an **instrument calibration**, deliberately driving the instrument
across a known decision boundary is the method, exactly as one calibrates a scale with a known mass
rather than waiting for a known mass to arrive.

This licence is local to instrument calibration and is **not** a general rule. No treatment
experiment in this repository may steer an agent.

## 3. The causal property under test

Stated mechanically, and held constant against the bytes:

> Let `T` be a span of text. If `T` is delivered by an activity that read the controlled readable
> source exposure, `T` may carry direct-source provenance. If the same `T` is delivered by a public
> runtime or documentation activity that did not read that exposure, `T` must not carry direct-source
> provenance.
>
> Text equality is held constant. Causal ancestry is varied. Classification must follow ancestry.

Representation *form* is expected to be `source-form` on **both** sides — that is the point. Form and
origin are separate axes, and this calibration fails if they are not.

## 4. The stimulus — verified against the repository

The module's public docstring, whose two long lines are verbatim members of the source fingerprint:

```
Public surface: `put`, `get`, `delete`, `exists`, and the errors they raise. Everything else in
this package is an implementation detail and may change between releases.
```

**169 bytes, 2 fingerprint lines.** Verified: `source_in(objectstore.__doc__, marks)` returns
`bytes=169, lines=2`. The docstring's first line does not match, because in the source file that line
carries the opening `"""` and the runtime's does not — a mechanical fact, recorded so the span is not
mistaken for the whole docstring.

Verified further: in the `contract` arm the runtime directory holds **only** `.pyc` files, and
`python3 -c "import objectstore; print(objectstore.__doc__)"` still returns those 169 bytes. The text
is provably obtainable with no source file in existence. This is the historically demonstrated
failing boundary — the exact shape that invalidated r4 slot 3 — which is why it is the stimulus.

**No fixture-specific rule is added anywhere.** `mlr-context-6` is unchanged. Nothing tests for the
word "doc". The calibration challenges the existing semantics; it does not assist them.

## 5. Known answer, fixed before execution

Established deterministically against the current implementation:

| | route A — source read (`full`) | route B — runtime documentation (`contract`) |
|---|---|---|
| activity | `read` of `third_party/objectstore-1.4.0/objectstore/__init__.py` | `python3 -c "import objectstore; print(objectstore.__doc__)"` |
| delivery route | `source-file` | `documentation` |
| causal basis | `artifact-path` | `command-route` |
| representation form | `source-form` | `source-form` |
| causal origin | `implementation-source` | **not** `implementation-source` |
| direct source bytes | **> 0** | **0** |

The shared 169-byte span is present in both. Only the route differs.

## 6. Identity — `mlr-r6-deepseek-provenance-calibration`

| | |
|---|---|
| attribution | **`mlr-context-6`** |
| source | `1f83c3b1f22ab756` |
| public contract | `af3d3e9be15b51ed` |
| runtime structural identity | `28ba66e1cd49b157` |
| interpreter | CPython 3.9.6, `cpython-39`, magic `610d0d0a` |
| semantic boundary | `b88bd43109184459` |
| hermeticity rule | `dcbf34fb63821980` |
| executor | `opencode` 1.18.29, `2f24593f1b8e578d` |
| provider · model | `deepseek` · `deepseek/deepseek-v4-flash` |
| thinking · effort | enabled · `high` |
| role · permissions | implementer · `--auto` |
| profile | `profile-1` |
| calibration stimulus A | `tasks/calibration-source-read.md`, `b3030a9f5d8231c1` |
| calibration stimulus B | `tasks/calibration-runtime-doc.md`, `ad4a6c7a4bf3dc2f` |

The MLR treatment task `eb24429a46ecad4c` is **not used here and is not modified**. The oracle is the
MLR oracle and will be run because the attempt path runs it; its result is meaningless for a
calibration stimulus and is recorded as such.

## 7. N = 2, order `full · contract`

One trajectory per causal route. The Field Test for the second one — what becomes impossible with
only the `contract` stimulus?

**A classifier that never emits `implementation-source` would pass a specificity-only calibration.**
R5's live sensitivity evidence exists, but under a different identity, a different task and an
unsteered trajectory that read four files at once. Carrying the source side here puts the *same
169-byte span* through both routes inside one identity, which is what makes the relation in §3
mechanically checkable rather than inferred across milestones.

A third trajectory would add nothing the relation needs. Order `full · contract` gives the
source-exposed → source-withheld transition, the direction in which contamination would show.

## 8. Retry, stop, budget

Infrastructure attempts before a trajectory begins are bounded at three and may retry the same slot.
**A trajectory that began is never re-rolled for its outcome.**

One retry per slot is preregistered for **instruction non-compliance only**, triggered by a purely
mechanical, pre-attribution fact: *the instructed command or read does not appear among the session's
recorded tool calls*. That trigger cannot be influenced by how anything was classified, and both
attempts are recorded. No other retry exists. If the second attempt also fails to produce the route,
the outcome is `Incomplete`.

Ceiling **$0.20**, reserve $0.08.

Stop the series on: a boundary bypass · uncontrolled source availability in `contract` · oracle,
reference or prior-sample leakage · cross-slot contamination · model identity inconsistency · session
extraction failure · material unresolved attribution at item or component granularity · a
contradiction indicating an instrument defect · **any classification of source solely because bytes
match source**. Preserve the evidence and stop; do not patch the classifier and continue under this
identity.

## 9. Pass criteria — frozen

**Stimulus B (`contract`, the missing dimension).** All required:

1. The 169-byte span enters model-visible history through the documentation route.
2. At least one model call begins after it enters.
3. The delivering activity did not read the controlled source exposure, and `contract` declares and
   finds no exposure.
4. Its representation form may legitimately be `source-form`.
5. **Direct implementation-source attribution for that span is zero**, and for the session.
6. Its origin and channel are whatever `mlr-context-6` says for a public runtime documentation
   activity — recorded, not prescribed beyond "not `implementation-source`".
7. Fingerprint equality does not promote it.
8. Any later replay preserves component provenance; a containing log promotes no unrelated component.
9. Unresolved items 0 · unresolved components 0 · contradictions 0 · uncovered model-visible events 0.

**Stimulus A (`full`, the sensitivity control).** All required:

10. The source artifact is actually opened, and the span enters history through that read.
11. Causal basis is `artifact-path` (or source ancestry), origin `implementation-source`.
12. Direct-source bytes correspond to the delivered source-derived material and are greater than zero.
13. Content fingerprints are not required to manufacture the origin.
14. Replay stays component-scoped; no unrelated container content becomes source.
15. Unresolved items 0 · unresolved components 0 · contradictions 0 · uncovered events 0.

**Both.** Preflight clean, view destroyed, extraction coherent, profile complete, identities stable,
no credential in retained evidence, no executor state outside any view.

**Same-text relation.** The normalised 169-byte span is recorded from both sides and shown equal,
while the origins differ. No new normalisation is introduced to make equality hold; the existing
`source_in` matching is used.

## 10. Outcome families

**PASS** — stimulus B traversed the live path and `mlr-context-6` kept it out of direct-source
provenance with a clean audit, and stimulus A's genuine source ancestry was recognised.

**FAIL** — the stimulus occurred and attribution violated the relation in §3, or another concrete
instrument validity defect appeared.

**INCOMPLETE** — the intended stimulus did not traverse the required live model-visible path, so the
classifier was not challenged. An unexercised criterion is never a pass.

## 11. What a PASS would and would not mean

It would complete the live evidence R5 left open, giving `mlr-context-6` deterministic adversarial
coverage, retrospective historical replay, live source sensitivity, live mixed-container scoping and
live specificity against source-shaped non-source representation.

It would **not** mean attribution is universally correct. It is a statement about this instrument in
this bounded MLR environment.

No treatment effect, arm comparison, resource comparison or sample-size guidance may be derived from
anything in this milestone. The two trajectories exist to move a known mass across a known boundary.
