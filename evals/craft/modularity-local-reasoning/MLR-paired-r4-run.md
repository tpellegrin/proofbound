# MLR DeepSeek paired experiment — the run, and the defect that invalidates it

The frozen experiment was executed as preregistered. It is **invalid**: a public docstring, reached
through documentation introspection, was classified as direct implementation source in a `contract`
slot — the arm and the quantity the experiment exists to measure. The series was stopped rather than
repaired, four completed trajectories are retained, and no treatment inference is drawn from them.

## 1. What ran

`mlr-deepseek-v4-flash-high-paired-r4`. Every frozen identity verified against the repository before
the first call and unchanged throughout: source `1f83c3b1f22ab756`, task `eb24429a46ecad4c`, contract
`af3d3e9be15b51ed`, oracle `external_test_v2.py` `86f17eaf2685ac22`, runtime structural identity
`28ba66e1cd49b157`, CPython 3.9.6, `mlr-context-5`, `profile-1`, boundary `b88bd43109184459`,
hermeticity rule `dcbf34fb63821980`, executor `2f24593f1b8e578d` (1.18.29),
`deepseek/deepseek-v4-flash` with thinking enabled and effort `high`, implementer role, `--auto`.

Two neutral route probes returned `ready` in 4.0 s and 2.6 s before any slot. Linux CI for the
commit under test was green.

**Four of twelve slots completed**, one attempt each, before the series was stopped.

## 2. Evidence

| slot | pair | arm | correct | preflight | direct source | reconstruction | runtime | unresolved | contradictions | uncovered | derived |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | full | yes | clean, 4 declared | 5,630 | 0 | 0 | 0 | 0 | 0 | $0.0326 |
| 2 | 1 | contract | yes | clean, 0 declared | **0** | 0 | 13,513 | 0 | 0 | 0 | $0.0330 |
| 3 | 2 | contract | yes | clean, 0 declared | **340** | 0 | 102 | 0 | 0 | 0 | $0.0473 |
| 4 | 2 | full | yes | clean, 4 declared | 5,630 | 0 | 0 | 0 | 0 | 0 | $0.0274 |

Slot 5 (`full`) was interrupted mid-trajectory when the series was stopped: 7 model calls, 22 tool
calls, $0.0090, recovered from the session it left and counted. Slots 6–12 never launched. Total
spend $0.1494 of $0.50.

## 3. The defect

In slot 3 the agent ran

```
python3 -c "import objectstore; print([x for x in dir(objectstore) if not x.startswith('__')]); print(objectstore.__doc__)"
```

and the 340 bytes that came back were classified `implementation-source`, form `source-form`, basis
`command-route`, route `documentation`. The two lines the fingerprint matched are:

```
Public surface: `put`, `get`, `delete`, `exists`, and the errors they raise. Everything else in
this package is an implementation detail and may change between releases.
```

That is the module's **public docstring** — the text MLR-C2 recorded as legitimately reachable in
both arms: *"`__all__`, signatures, docstrings … A real closed-source dependency has these, and
withholding them would change the task rather than the treatment."* It is in the source file, so it
is in the source fingerprint, so content matching calls it source. It arrived through `__doc__` at
runtime and never through readable source.

It did not stop there. The misclassification propagated through the content-echo index into a
**42,915-byte** read of the worker's own log — 34,618 bytes of it disassembly — which inherited
`implementation-source` ancestry and, because ancestry asserts source, had its whole rendering
counted.

**The treatment held.** Every preflight was clean; `contract` declared no exposure and produced no
finding; no uncontrolled implementation source was available in either arm. What failed is the
classifier, on the one measurement the experiment exists to make.

## 4. Why the series was stopped

The frozen preregistration lists a material attribution defect among its stop conditions and says
plainly: preserve the evidence and repair under a new identity, do not patch and continue. Continuing
would have meant spending eight more slots under a classifier known to be wrong about `contract`
source, and repairing would have meant changing the instrument after seeing semantic evidence. Both
are the failure mode this programme has already paid for.

Slot 2 measured `contract` at zero because that trajectory happened not to print `__doc__`. One
uncontaminated slot cannot rescue a series whose measurand is unreliable in the other.

## 5. What this does not establish

Nothing about the treatment. Not that `contract` preserves correctness, not that it reduces source,
not that it substitutes runtime representation, not that `full` needs its source. Four trajectories
under a defective measurand support no family in the preregistration except the one recorded.
4/4 correctness is retained as evidence that the path runs, and is not a result.

## 6. What a repair must settle

The question is narrow and answerable: **a docstring is public surface in both arms, and its text is
also in the source file.** Content matching cannot separate them, so something else must — the route
that delivered it, the ancestry that produced it, or a fingerprint that excludes the module's public
documentation from the marks that identify its implementation. Whichever is chosen, it changes what
`mlr-context-5` means and therefore requires a new attribution version, deterministic validation
against the retained corpus, and a fresh field qualification before another paired experiment is
frozen.

Also worth settling in the same milestone: whether an ancestry-asserted origin should carry a whole
rendering when the evidence for that origin is two matched lines in a forty-kilobyte log.

Every attempt, every session and every extracted workspace is retained.
