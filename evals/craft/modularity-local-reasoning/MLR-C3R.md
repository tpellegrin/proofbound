# MLR-C3R — the repaired instrument, and what it measured

MLR-C3 answered its headroom question and disqualified the instrument that answered it. This
milestone repaired both defects before any new call, re-ran the pilot under a new identity, and
audited the repair against what the runs actually did.

**Result: 6 of 6 correct, 6 of 6 consuming implementation source, median 5,670 bytes, and no material
implementation-derived representation reached model history unattributed.**

## 1. What C3 established, and what it did not

C3 stands as evidence and is not recomputed. It established source-access headroom, the cost and
shape of six real executions, that `full` agents reach the implementation before the contract, and —
by failing — two defects in its own instrument. It established nothing about treatment effect, local
substitution, modularity, or comparative efficiency.

C3 remains evaluated under **oracle v1**. C3R uses **v2**. Retrospectively, C3's rejected attempt 1
was the `(body, created)` shape, which v2 accepts; that is a diagnostic note, not a re-scoring, and
no C3 run is a sample of anything here.

## 2. Defect A — the oracle required the reference's decomposition

v1 asserted `exports.fetch(user_id, report_id) == body`. Nothing in the task fixes that signature,
nothing else in the workspace pins it, and the reference merely happens to keep it.

**Oracle v2** derives its assertions from the task clause by clause and calls `app.api` only.

| Task clause | Assertion |
|---|---|
| already stored → 200 | `create_export`, then `download_export` returns 200 with the created bytes |
| not stored → produce, store, 201 | first download 201 with the rendered report; later downloads 200, byte-identical |
| repeated calls agree; what is stored is what was returned | second download 200 and equal to the first |
| entitlement applies | a refused account gets 403 on every call and never receives a report body |
| unknown account or report → 404 | 404 on every call; a second call is still 404, never 200 |
| `create_export` unchanged | the service's own suite, run separately |

Each positive test owns one `(account, report)` pair, because the store persists across test methods
and a shared pair would make the 201/200 distinction depend on unittest's ordering. That defect
appeared while writing v2 and is the reason the rule is stated.

**One clause is deliberately ungated.** *"...and nothing is stored"* for a refused account is not
observable from the product surface: a refused account can never read anything back either. What is
asserted is the consequence that matters — it never receives the export. An implementation that
stored an object it never serves would pass. The limit is written into the gate rather than repaired
by reaching into the service, which is what v1 did.

**Validated adversarially, deterministically, before any call.**

| Accepted (product-correct) | Rejected (behaviourally wrong) |
|---|---|
| `reference` · `handler` · `optional` · **`tuple`** (the shape v1 rejected) | `always-created` · `missing-as-empty` · `no-entitlement` · `unstable` · `stores-on-unknown-report` |

v2 accepts all four and rejects all five. **v1 rejects two of the four** — `tuple` and `optional`.
The defect is now a number rather than an anecdote, and an untouched workspace is still rejected, so
the gate continues to measure that work was done.

## 3. Defect B — implementation-derived representation escaped attribution

`help(objectstore)` returned 5,397 bytes naming `_backend`, `_errors` and `_store` and was scored
`other`; `python3 -m pydoc objectstore` matched a behaviour marker and was scored as *running the
system*.

**Attribution v2 decides on two channels.** The **route** — `source-file`, `search`, `documentation`,
`introspection`, `run`, `edit`, `unknown` — says what was asked for, with documentation and
introspection tested *before* running the system. The **content** says what came back, matched
against the module's internal names.

Those names are **derived from the runtime source with `ast`** rather than listed: private submodule
stems plus every private module-level binding. C3's hand-written list already missed four names that
exist in the module today, and would have missed every future one.

Within the documentation and introspection routes the content decides. Measured by executing the
whole surface against the real fixture:

| Discloses the interior → `implementation-runtime` | Public only → `public-contract` | Refused |
|---|---|---|
| `help(package)` 5,389 B · `help(_store)` 882 B · `pydoc.render_doc` 6,355 B · `vars(_store)` 912 B · `dir` 245 B · `__dict__` 245 B · `getmembers` 245 B · `co_names` 92 B · disassembly 10,212 B · module enumeration 33 B | `__all__` 68 B · signatures 110 B · docstrings 318 B | `inspect.getsource` · `loader.get_source` · `importlib.metadata` |

**Disclosure is a third line.** Bytes carrying internal names, whatever route asked, reported beside
the provenance totals and never added to them — a test run with a traceback through the module's
interior is test output that disclosed something, not implementation representation.

## 4. The execution profile

`_profile.py` holds the half of the measurement that is not about object storage: model calls,
tokens, tool activity, time, stages, completeness. A test asserts it never mentions the fixture;
another asserts nothing in it computes a quality-over-cost rate. Missing telemetry fails closed — an
execution whose session was not recorded is invalid, not cheap.

## 5. The pilot

`mlr-c3r-full-headroom-pilot`, N = 6 fixed, `full` only, oracle v2, model
`opencode/nemotron-3-ultra-free`, implementer role.

| # | correct | impl. source | impl. runtime | disclosure | contract | application | calls | input tok | cache read | tools | s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | yes | 7,204 | 0 | 7,713 | 0 | 7,685 | 46 | 324,731 | 440,640 | 43 | 746 |
| 2 | yes | 7,204 | 0 | 7,740 | 0 | 10,856 | 34 | 273,570 | 354,240 | 38 | 458 |
| 3 | yes | 4,797 | 0 | 4,906 | 0 | 8,093 | 21 | 159,127 | 159,840 | 23 | 299 |
| 4 | yes | 4,797 | 0 | 4,911 | 0 | 7,387 | 33 | 232,212 | 185,760 | 25 | 412 |
| 5 | yes | 2,761 | 0 | 2,761 | 0 | 7,685 | 23 | 172,530 | 159,840 | 26 | 251 |
| 6 | yes | 6,543 | 0 | 6,543 | 0 | 10,966 | 24 | 200,903 | 203,040 | 31 | 238 |

Six valid attempts, no setup or harness failure, no slot re-run, every profile complete. 1,363,073
input tokens, 38,718 output, 1,503,360 cache-read, 40 minutes wall clock, no monetary cost on this
model.

**Against the pre-registered categories this is valid headroom:** every correct run consumed
implementation source, median 5,670 bytes — well above the 1,000-byte line — and the attribution
audit found nothing unattributed.

**Correctness rose from 5/6 to 6/6.** The C3 run that v1 rejected had been product-correct all along;
this is the false negative removed, not the agents improving.

**Time is almost entirely model generation.** Attempt 1: 745.6 s harness, 733.8 s session span,
1.72 s of measured tool execution, 732.1 s derived model time, 0.10 s verification. On this fixture
the pipeline is model-latency-bound and nothing else is close.

**Five of six runs still never opened the contract** — the same finding as C3, now on a different
series. Agents read the implementation, or infer the semantics from how the application already calls
the module.

## 6. Attribution audit

Every item of every transcript, inspected for text that reached model history carrying internal names
while classified as neither implementation class.

**Material inbound escapes: 0.** Routes exercised: `source-file` 86 items / 118,699 B, `run` 44 /
15,266 B, `search` 10 / 8,348 B, `edit`, `unknown` 194 / 58,583 B.

Five items carried internal names outside the implementation classes, all of them
**`assistant:reasoning`** — the model's own text, naming `_ROOT_ENV`, `_backend`, `_path_for`,
`_store`. That is not a route by which information enters the pipeline; it is downstream of what the
run already consumed, and the telemetry excludes model-authored text from provenance by design. Each
occurred in a run that had consumed 4,797–7,204 attributed implementation bytes, so every one is
explained. **Model-side disclosure in runs that consumed no implementation: 0** — which is the check
that would have caught an escape hiding behind this exclusion.

**The honest limitation.** No `full` run in this series used `help`, `pydoc` or any introspection
route: implementation-runtime is 0 in all six. The repaired documentation attribution is therefore
validated by **deterministic execution against the fixture**, not by field observation in this pilot.
That is expected — an agent holding readable source has no reason to interrogate the live object —
and it is precisely the `contract` arm, where the source is gone, that will exercise those routes.
The paired run is what tests the repair in the field.

## 7. Readiness

| Condition | Status |
|---|---|
| Oracle accepts legitimate architectural variation | **Yes** — four decompositions |
| Oracle rejects behaviourally wrong solutions | **Yes** — five |
| Material documentation and introspection routes attributable | **Yes**, deterministically; not exercised live (§6) |
| Consumed-context semantics defensible | **Yes**, unchanged and re-verified |
| Fresh `full` runs still show source-access headroom | **Yes** — 6/6, median 5,670 B |
| Telemetry complete enough for the primary interpretation | **Yes** — all six profiles complete |
| No pilot result triggered a semantic fixture change | **Yes** — nothing was edited after the first call |

## 8. What this does not establish

Not a treatment effect, not local substitution, not a modularity benefit, and nothing about a second
domain. Headroom means only that there is implementation-source consumption for a treatment to
remove. The internal control remains unbuilt, so even a successful paired run would show source
substitution for this external task, not that the boundary correctly separates external from internal
responsibilities.
