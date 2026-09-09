# MLR-C2 — measurement mechanics and the information boundary

No semantic call was made. This milestone asked whether the treatment MLR-C1 built is the treatment
the experiment intends, found that it was not, and fixed it before any model saw the fixture.

## 1. The probe that decided the milestone

C1 hid the implementation by leaving it out of the `contract` workspace. Run against that fixture:

```
inspect.getsource(objectstore)          -> 461 bytes of source
inspect.getsource(objectstore._store)   -> 2,200 bytes of source
open(objectstore.__file__).read()       -> the implementation
```

Repository absence was **friction, not an information boundary**. An agent that types one ordinary
line recovers everything the treatment was supposed to withhold, and recording that it happened
would not preserve the treatment — it would only document its collapse.

## 2. The boundary that was selected

Of the models considered: **discovery-only** is what C1 had, and the probe above disqualifies it.
A **read policy** in the executor is the direct approach and was rejected here for a mechanical
reason — Python must read a module's source to import it, so denying reads at the filesystem breaks
execution, and intercepting every tool surface is a sandbox project rather than an experiment.

**An alternative executable representation** was selected, and it is the option C1 rejected. C1's
reason was real — bytecode compiled by 3.14 will not import under 3.10 — and it dissolves once the
bytecode is compiled **at materialisation by the interpreter that will run it** rather than committed
to the repository. Nothing compiled is ever shared between interpreters, so the incompatibility has
no surface to appear on. Verified under both 3.10 and 3.14.

The runtime is therefore the module compiled to bytecode, with no source beside it, imported from
outside the workspace in both arms. `full` additionally carries the readable source inside the
repository at a path that is not importable.

**What this claims.** Ordinary development tooling — reading a file, `inspect.getsource`, following
`__file__`, listing the package directory — does not return the implementation. **What it does not
claim.** It is not security isolation: bytecode can be disassembled, and an agent determined to do
that would recover a rendering of the logic. This is an experimental information policy, and the
threat boundary is written down so no later milestone overclaims it.

## 3. What survives the boundary, and should

| Reachable in `contract` | Why it stays |
|---|---|
| `__all__`, signatures, docstrings | The module's public semantics. A real closed-source dependency has these, and withholding them would change the task rather than the treatment. |
| The path the module loads from | Location is not contents (§9 of the design). `inspect.getsourcefile` names a `.py` that does not exist. |
| `co_filename` reading `objectstore/_store.py` | A normalised name, recorded by `dfile` so the build directory does not leak. Again a name, not a body. |
| Runtime behaviour, including raised errors | That is the contract being exercised. |

Not reachable: any implementation text. Verified — the compiled objects contain neither `def put`
nor `_FANOUT`, and the package directory lists no `.py` at all.

## 4. Same system, different visibility

| | value |
|---|---|
| runtime digest, both arms | `cf73730b62c723e5` |
| source digest the runtime was compiled from | `1f83c3b1f22ab756` |
| contract sha, both arms | `af3d3e9be15b51ed` |

The runtime digest now covers the compiled objects — C1's `digest_tree` skipped every `.pyc` as a
cache and so hashed an empty set, which meant the "identical runtime" check had been passing
vacuously. Fixed, and the digest is reproducible across separate materialisations, which is what
lets two slots of the same arm be the same experiment.

## 5. The primary measurand, revised before evidence

C1's wording compared *implementation bytes read in `full`* with *contract bytes supplied in
`contract`*. That mixes two accounting categories and ignores that the contract is present in both
arms, so it would have charged one arm for something both received.

> **Revised: the implementation bytes that entered reasoning on correct runs, per arm.**

Correctness still gates it. The contract document and the public surface are byte-identical in both
arms and therefore cancel from the comparison rather than being counted on one side. In `contract`
the quantity is structurally zero, because no implementation text is reachable. In `full` it is
whatever the agent actually opened — availability is not consumption, and charging `full` for the
4,405 bytes it may never read would rig the result.

The claim this supports is unchanged in substance and clearer in form: *the external semantics,
identical in both arms, sufficed; the implementation contributed nothing.* What it can no longer do
is quietly credit `contract` with a smaller number for a document both arms hold.

**Retained alongside it**, because context economy is a vector: reads by class (workspace, vendored
implementation, runtime, outside), tool and search calls, denied or failed probes, time and cost. A
`contract` run that spends heavily probing the runtime has not reasoned cheaply, and the accounting
must be able to say so.

## 6. Context accounting

`available` is fixed by the arm and is now checkable; `supplied` is the task and contract, identical
in both. `read` is attributable by resolved path — `classify_path` puts every touched file in one of
four classes, and unlike `ce1_facts` it does **not** discard absolute paths, which matters precisely
because the implementation lives at one. `consumed` — what actually entered model calls — remains
unproven, and is the one accounting category C3 must establish against the executor it uses.

## 7. The task exercises the boundary

Check C, mechanically: a plausible patch that assumes a missing object reads back as empty fails the
hidden gate. The task cannot be satisfied without knowing how the module reports absence, and that
fact lives in the contract and the docstrings — external semantics, present in both arms. So the
experiment compares *implementation access against no implementation access* with external semantics
held constant, which is the designed comparison.

## 8. The internal control

C1 found the approved control unbuildable; C2 makes the reason structural rather than incidental.
With a compiled runtime the module is a closed-source dependency **in both arms**, so no task can
modify it in either. A control of that shape needs the module inside the repository and mutable in
one arm, which needs the executor read policy §2 rejected for this fixture.

**Decision: separate design, sequenced after the first paired run.** The control tests *selectivity*
— that the boundary correctly becomes insufficient when a task really belongs inside the module —
which is a further claim than the one C3 makes. C3's primary claim is that implementation access
provides no correctness value for a task outside the module, and that claim is carried by the paired
external task alone. Without the control, C3 may not claim that the boundary is *why* it worked; with
it, a later milestone can. That limit is recorded rather than glossed.

## 9. Substrate

Reused unchanged: `_experiment.py`'s manifest, preallocated slots, arm interleaving and
configuration identity; `_repeat.py`'s non-splicing resume. Verified that the paired shape expresses
one task, two arms and N repeats with neither arm leading every time, and that changing either the
runtime digest or the read boundary refuses resume — a run where the implementation was readable is
not the same treatment as one where it was not.

New: runtime compilation, path attribution, implementation-byte accounting, and a shadow-copy guard
that reports which module actually executes, so the mistake that killed the control is detected
mechanically rather than discovered from a failed experiment.

## 10. Residual confounds

`full` presents the implementation as vendored third-party source rather than the service's own
code. Bytecode can be disassembled. One boundary and one architecture cannot attribute an effect to
boundary quality. `consumed` context attribution is unproven.

## 11. What C3 must do first

Establish `consumed` attribution against its executor; run a `full`-only pilot for headroom, since
whether `full` reads the implementation at all is the one gate no inspection can settle; pre-register
the revised measurand, the sample budget and the interpretation categories; and bind fixture
revision, runtime digest, contract sha, task identity, read boundary, executor and model
configuration into one frozen identity.
