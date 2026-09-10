# MLR DeepSeek paired calibration — the run, and the attribution defect that invalidates it

The frozen N = 6 paired experiment executed exactly as pre-registered. Every slot completed, every
slot was correct, no provider interruption occurred, and the treatment held. It is nonetheless
**invalid**: one `contract` trajectory routed 29,499 bytes of implementation disassembly through a
temporary file and the attribution classified it as `other`. That is a material inbound
implementation representation that escaped attribution, in the arm whose reconstruction behaviour is
the central secondary question. Nothing was patched and recomputed; the evidence is preserved as it
was recorded.

## 1. What was executed

`mlr-deepseek-v4-flash-high-paired`, frozen identity `32a963d591e1cf56`. Fixture `1b8a53b6e818d6f2`,
source digest `1f83c3b1f22ab756`, contract `af3d3e9be15b51ed`, task `eb24429a46ecad4c`, oracle v2
`86f17eaf2685ac22` (`external_test_v2.py`), gate `c90114ca50847cef`, attribution `mlr-context-3`,
profile `profile-1`, price identity `deepseek-2026-09-09`, model `deepseek/deepseek-v4-flash`,
thinking enabled, effort `high`, implementer role, `--auto`.

12 slots, 12 valid, **one attempt each** — no retry, no re-roll, no substitution. Arm order was
generated before execution and rotated, so neither arm led every pair:

```
full·1  contract·1  contract·2  full·2  full·3  contract·3
contract·4  full·4  full·5  contract·5  contract·6  full·6
```

Provider-observed identity was `deepseek-v4-flash` / provider `deepseek` / variant `high` in all
twelve sessions; `single_model` and `single_variant` hold throughout. All twelve executions fell in
one peak pricing window. Total derived spend **$0.4239** against the $1.50 ceiling.

## 2. Correctness

**12/12.** Both the hidden oracle gate and the service's own regression suite passed in every slot,
in both arms, at first attempt. The contract document, the compiled runtime and the vendored copy
were unchanged at the end of every run. Verification cost 0.080–0.133 s per run.

| pair | full | contract | pattern |
|---|---|---|---|
| 1 | correct | correct | both-correct |
| 2 | correct | correct | both-correct |
| 3 | correct | correct | both-correct |
| 4 | correct | correct | both-correct |
| 5 | correct | correct | both-correct |
| 6 | correct | correct | both-correct |

No `full`-only, no `contract`-only, no `neither`, no invalid pair. Six pairs is a small sample and
6/6 concordance carries little resolution about correctness, exactly as the pre-registration said it
would.

## 3. The defect that invalidates the experiment

In **pair 5, `contract`**, the agent disassembled the compiled runtime and wrote the result to a file
outside every classified location:

```
python -c "import dis, marshal
for name in ['_backend','_store']:
    ... dis.dis(code)" > /tmp/objectstore_dis.txt
```

The producing call carried no payload — its output was a `wc -l` line — so nothing was attributed
there. The agent then read the file back. That read is recorded as:

| | |
|---|---|
| kind | `tool:read` |
| detail | `/tmp/objectstore_dis.txt` |
| bytes | **29,499** |
| delivered | 442,485 bytes across **15** later model calls |
| internal names | all 14, including `_ATTEMPTS`, `_FANOUT`, `_path_for`, `_with_retries` |
| origin | **`other`** |

The content is 260 occurrences of CPython opcode mnemonics: it is implementation representation, and
it is inbound. Its recorded origin is not an implementation origin. The consequence is exact:
`contract` pair 5's recorded `implementation-runtime` figure is 17,185 while the runtime-derived
representation that actually entered reasoning was 46,684 — understated by a factor of 2.7, in the
arm and on the quantity the experiment exists to measure.

A content-based sweep of **all twelve** trajectories — every inbound part over 400 bytes, tested for
opcode density and for verbatim module-source lines, matched back to the ledger by digest — finds
**exactly one** such escape. It is one-armed. That makes it worse rather than better: it biases
precisely the comparison that the secondary question turns on.

**Why the routine audit missed it.** The MLR-C3D-R escape predicate flags an inbound item as material
when it carries internal names, is not in an implementation origin, exceeds 200 bytes, and has *zero*
metadata bytes — the zero-metadata clause distinguishing a body from a path echo. This item has 3,188
metadata bytes, from the `objectstore/_store.py` and `objectstore/_backend.py` headers `dis` prints
above each disassembly. Eleven per cent metadata over an 89% body defeated a predicate written for
items that are *only* a path. The predicate is too weak; the ledger itself recorded the item
faithfully, which is how the escape was found at all.

**A second, opposite defect.** In `full` pairs 4 and 5, a `bash` call whose command text names
`third_party/objectstore-1.4.0` had its output attributed to `implementation-source` under the
path-identification rule — 301 and 224 bytes, `source_lines = 0`. The outputs contain no source at
all:

```
1.4.0 /.../arm/runtime/objectstore/__init__.pyc
PYTHONPATH=/.../arm/runtime
objectstore
```

Those are paths, a version string and a directory entry. They inflate the **primary measurand** by
5.2% and 3.8% in two of six `full` runs. Smaller than the first defect and in the opposite direction,
and independent of it.

Under §10 of the execution brief a material escape stops interpretation; under §23 no measurement may
be repaired after the first semantic call, and a material defect appearing afterwards makes the
experiment invalid. Both apply. **No attribution, lineage, origin category, route rule, observer
layout, oracle or profile was modified**, and no corrected figure is substituted for a recorded one.

## 4. What the treatment did, recorded but not interpreted

These are the numbers as measured. They are retained as evidence of what executed. **No result family
is selected from them**, because the instrument that produced the module-internal columns is the one
under challenge.

| pair | F source | C source | F delivered | C delivered | F runtime | C runtime | F meta | C meta |
|---|---|---|---|---|---|---|---|---|
| 1 | 5,822 | 0 | 93,152 | 0 | 1,495 | 623 | 5 | 1 |
| 2 | 5,822 | 0 | 133,906 | 0 | 1,495 | 32,380 | 7 | 4 |
| 3 | 5,822 | 0 | 81,508 | 0 | 14,172 | 19,645 | 7 | 3 |
| 4 | 6,123 | 0 | 125,272 | 0 | 817 | 32,679 | 5 | 3 |
| 5 | 6,046 | 0 | 108,156 | 0 | 499 | 17,185 † | 8 | 6 |
| 6 | 5,822 | **122** | 221,236 | 1,342 | 28,639 | 33,446 | 10 | 4 |

† understated by 29,499 — see §3. `full` pairs 4 and 5 are inflated by 301 and 224 — see §3.

**Direct source, `full`.** Every `full` run read all four module files whole — `__init__.py` 718,
`_store.py` 2,697, `_backend.py` 1,746, `_errors.py` 661 — **5,822 bytes, six times out of six**, by
the `source-file` route, with `replays = 0`. Pairs 1, 2, 3 and 6 record exactly those four distinct
representations; pairs 4 and 5 record a fifth, which is the over-attributed listing. The invariance
first seen across eight C3D and C3D-R runs held for six more.

**Direct source, `contract`: not zero.** Pair 6 records 122 bytes over 2 lines, attributed by content
lineage to an `assistant:reasoning` part and delivered to 11 later calls. Recovered from the retained
session, the two lines are:

```python
path = Path(os.environ.get(_ROOT_ENV, tempfile.gettempdir())) / "objectstore-data"
path.mkdir(parents=True, exist_ok=True)
```

The surrounding reasoning says where they came from: *"Wait, in the disassembly:"*. The model
reconstructed two verbatim lines of `_backend.py` from bytecode it had disassembled, in a workspace
that contains no source. Treatment integrity is intact — no source was *available* to `contract` in
any run — and the pre-registered expectation that `contract` source would be "structurally zero" is
not what happened. Lineage caught it, which is the one thing here the instrument did right.

MLR-C2 declined to claim the boundary was security isolation: *"bytecode can be disassembled, and an
agent determined to do that would recover a rendering of the logic."* Twice in six `contract` runs, an
agent did exactly that, and once it transcribed the source back verbatim.

**Runtime reconstruction.** `contract` reached the interior through disassembly in 5 of 6 runs,
`marshal` in 4, `dir` in 4, `inspect` in 2; `full` used disassembly in 2 and `dir` in 2. Route
distribution over runtime-origin items: `contract` 10 introspection / 5 unknown / 1 source-file,
`full` 4 introspection / 10 unknown. Both arms ran `git` commands in all six runs. No `help()` or
`pydoc` appears in this series — the route MLR-C3R added remains implemented and unexercised here.

**Public and application representation.** Public contract, median: `full` 2,994 [2,994..3,982],
`contract` 3,011 [2,994..3,850]. Application: `full` 12,024 [11,379..12,966], `contract` 11,285
[9,784..12,984]. Neither arm substituted a materially larger dose of the documentation for the
implementation.

**Unresolved: zero.** No inbound item failed to resolve in any run. The fail-closed category was never
entered — which is the point worth stating plainly: the pair-5 escape was a **confident
misclassification**, not an admission of ignorance. `unresolved` cannot catch a defect of that shape.

## 5. Execution profile

Generic throughout: the profile names no fixture, arm or module, and computes no quality or cost
rate. Complete for all twelve runs, nothing missing, no truncated item, every session summarised.

| | full (n=6) | contract (n=6) |
|---|---|---|
| model calls | 162 total, median 24.5 [20..44] | 140 total, median 24 [21..25] |
| input tokens | 158,697 total, median 23,444 | 176,706 total, median 28,812 |
| cache read | 5,091,200 total | 4,298,624 total |
| cache write | 0 | 0 |
| output tokens | 57,156 total, median 8,753 | 52,587 total, median 8,682 |
| reasoning tokens | 67,956 total, median 11,579 | 64,296 total, median 10,254 |
| tool calls | 297 (read 145, bash 97, write 18, edit 25) | 262 (read 123, bash 97, write 18, edit 18) |
| failed tool calls | 0 | 1 |
| session span | median 117.0 s [92.8..212.6] | median 105.0 s [96.4..116.3] |
| derived model seconds | median 106.0 s | median 103.7 s |
| tool seconds | median 1.15 s [0.78..121.2] | median 1.36 s [0.82..1.85] |
| verification seconds | median 0.087 s | median 0.097 s |
| executor-reported cost | $0.0715 | $0.0695 |
| published-rate derived cost | $0.2166 | $0.2073 |

The workload is **model-latency-bound** in both arms: tool time is around one second and verification
under a tenth of a second against one to three minutes of session span. One `full` run spent 121 s
inside a single tool call, which is the only excursion from that shape.

**Cost discrepancy.** Derived cost is **3.01×** the executor-reported figure, consistently across both
arms (3.03× and 2.98×). Both are retained; neither is reconciled into the other. The derived figure
bills input at the cache-miss rate and `cache_read` on top at the cache-hit rate, from the published
table retrieved 2026-09-09; what the executor reports is the executor's own accounting. The ratio is
stable enough to be a systematic difference in basis rather than noise, and identifying which basis
the provider actually invoices is not something this run can settle.

## 6. Audits

**Attribution.** One material escape (§3), one over-attribution (§3), zero unresolved items, zero
replay inflation (`replays = 0` in all twelve; unique bytes are identity-based and order-independent).
Metadata stayed separate from source in every run except the two `full` `bash` items, which is the
over-attribution. Runtime-derived characters were never added to source bytes anywhere in the record.

**Model-authored disclosure.** 37 model-authored parts named internals; **none** occurred in a run
that had consumed no implementation representation — the check that would expose an escape hiding
behind the inbound-only rule.

**Oracle.** No run was incorrect, so oracle v2 rejected nothing and no rejection needed auditing. The
hidden gate is not present in the subject's workspace in either arm: `find` over the preserved arms
returns no `hidden/` and no `external_test*`.

**Observer isolation.** Scanned every recorded part of all twelve sessions for oracle, instrument,
experiment-identity and observer markers. Oracle markers: **none**. Instrument markers (`pb_mlr`,
`_mlr_context`, `_lineage`, result-record names): **none**. Experiment-identity markers: none beyond
`third_party/objectstore-1.4.0`, which is the treatment itself and appears in `full` only, as
intended. DSD control-plane paths — `attempts/implementer`, `launch-reservation`, `worker.log`,
`terminal.json` — appear in both arms (108 inbound in `contract`, 88 in `full`) and are the subject's
own attempt scaffolding under the inherited layout, symmetric between arms and already attributed as
`harness`. No prior sample, partner output, model index or cost metadata reached any subject.

**Runtime digest reproducibility.** Eleven of twelve slots materialised runtime digest
`4b7ada46973a4cb2`; slot 1 (`full` pair 1) produced `f8a6c8397a47e3df`. The cause was located rather
than assumed: `_store.pyc` differs in 25 bytes, all from marshal's interned-vs-plain string flag for
one name (`last`) and the reference indices that shift behind it. Loading both and comparing a
recursive disassembly with addresses normalised, and comparing a recursive structural signature of
code, names, varnames, free and cell variables and constants, both come back **identical**. The
executing system was the same in all twelve slots; MLR-C2's claim that the digest is reproducible
across materialisations is what is wrong, since marshal interning depends on the compiling process's
prior state. Not arm-correlated, and not the reason this experiment is invalid.

**Header blemish.** The record's `purpose` string still reads "headroom: …", carried from the
qualification template. `experiment`, `arms`, `samples_per_arm` and the frozen identity all correctly
describe a paired run; the string is descriptive and binds nothing.

## 7. Status

Complete, correct, well-behaved, and **invalid on its instrument**. The attribution that MLR-C3D-R
requalified against three `contract`-free runs met a `contract` arm for the first time here and was
defeated by a route it had never seen: an agent laundering runtime representation through a temporary
file, where path-based classification has nothing to bind to and the escape predicate's zero-metadata
clause does not apply.

A re-run requires a **new experiment identity**. What it must fix, and what must be argued rather than
assumed before it runs:

1. Origin decided by content for inbound items regardless of location, not by path with content as a
   supplement — a disassembly is a disassembly wherever it is read from.
2. An escape predicate that measures the body-to-metadata *share*, as the metadata promotion rule
   already does, instead of requiring metadata to be zero.
3. Path identification that distinguishes a module file from a directory containing one, so a listing
   is metadata and not source.
4. A digest for the compiled runtime that is invariant under marshal interning, or an identity that
   binds the structural signature rather than the bytes.

Every execution, every session database and every arm materialisation is retained. **No execution here
may become a sample of the re-run**, and none of these numbers may be pooled with the Nemotron paired
attempt or with any other model's evidence.
