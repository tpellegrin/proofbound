# MLR-C3R — repaired instrument, `full`-only pilot, pre-registered

Written and committed **before the first semantic call of this identity**. Development evidence, not
confirmation. MLR-C3's pilot is *not* superseded and *not* recomputed: it keeps the oracle it was
judged by, and none of its runs may become a sample of anything here.

## 1. Why there is a C3R

MLR-C3 answered its headroom question and, in doing so, disqualified the instrument that answered it.

**Defect A — the oracle encoded the reference's decomposition.** v1 asserted
`exports.fetch(user_id, report_id) == body`. An attempt that was correct on every product-visible
axis was rejected because it had turned `fetch` into a get-or-create returning `(body, created)`.
Nothing in the task fixes that signature; the reference solution merely happens to keep it.

**Defect B — implementation-derived representation escaped attribution.** `help(objectstore)`
returned 5,397 bytes naming `_backend` and `_store` and was scored `other`; `python3 -m pydoc
objectstore` matched a behaviour marker and was scored as *running the system*. In `contract`, where
interrogating a closed-source package with `help()` is the most natural first move an agent has, a
run that reconstructed the interior would have reported zero implementation representation.

Neither is a local bug. Together they are the general point this milestone records: **once
alternative pipelines are compared empirically, the measurement instrument is part of the
experimental substrate and must be validated independently before any comparative conclusion.**

## 2. Oracle v2 — product-visible semantics only

Derived from the task text, clause by clause, and asserted through `app.api` alone.

| Task clause | Assertion |
|---|---|
| already stored → 200 | `create_export` then `download_export` returns 200 with the created bytes |
| not stored → produce, store, 201 | first download 201 with the rendered report; later downloads 200 with identical bytes |
| repeated calls agree, and what is stored is what was returned | second download 200 and byte-equal to the first |
| entitlement still applies | a refused account gets 403 on every call and never receives a report body |
| unknown account or report → 404 | 404 on every call, and a second call is still 404 rather than 200 |
| `create_export` unchanged, existing tests pass | the service's own suite, run separately |

**Not asserted, and why.** Private function signatures, helper decomposition, file layout, call
counts, or the reference's structure. And one clause of the task — *nothing is stored* for a refused
account — is **not observable from the product surface**, because a refused account can never read
anything back either. What is asserted is the consequence that matters: it never receives the
export. An implementation that stored an object it never serves would pass. That limit is written
down rather than repaired by reaching into the service, which is what v1 did.

**Each positive test owns one `(account, report)` pair.** The store persists across test methods, so
sharing a pair would make the 201/200 distinction depend on the order unittest chose.

**v1 is retained, not overwritten.** MLR-C3 remains evaluated under v1; C3R uses v2.

## 3. Adversarial oracle validation — before any call

Nine realizations, run deterministically in the suite.

| Accepted (product-correct) | Rejected (behaviourally wrong) |
|---|---|
| `reference` — `fetch` preserved, `fetch_or_create` added | `always-created` — never distinguishes produced from found |
| `tuple` — `fetch` returns `(body, created)` *(the shape v1 rejected)* | `missing-as-empty` — absence becomes an empty 200 |
| `optional` — `fetch` returns `None` when absent | `no-entitlement` — entitlement dropped on the download path |
| `handler` — the whole decision in `api`, `exports` untouched | `unstable` — re-renders and stores something other than it returned |
| | `stores-on-unknown-report` — a 404 leaves an object that later answers 200 |

v1 rejects `tuple` and `optional`. v2 accepts all four and rejects all five. An untouched workspace
is rejected by both, so the gate still measures that work was done.

## 4. Attribution v2 — two channels

**Route** — what was asked for, from the path or the command: `source-file`, `search`,
`documentation`, `introspection`, `run`, `edit`, `unknown`. Documentation and introspection are
tested *before* running the system, which is the ordering the defect got wrong.

**Content** — what came back, matched against the module's internal names. Those names are **derived
from the runtime source with `ast`**, not listed by hand: private submodule stems plus every private
module-level binding in them. The hand-written list C3 used missed four names that exist in the
module today, and would have missed every future one.

The two decide together. Within the documentation and introspection routes, output carrying internal
names is `implementation-runtime`; output carrying none is `public-contract`. That is what separates
`help(objectstore)` — which discloses `_backend`, `_errors`, `_store` — from
`inspect.signature(objectstore.put)`, which does not, without either being guessed from the verb.

**Verified by execution, not assertion.** The full surface is run against the real fixture:
`help` on the package and on the private module, `pydoc.render_doc`, `vars`, `dir`, `__dict__`,
`inspect.getmembers`, `co_names`, disassembly and module enumeration all disclose interior names;
`__all__`, signatures and docstrings do not; `inspect.getsource`, `loader.get_source` and
`importlib.metadata` remain refused.

**Disclosure is a third, separate line.** Bytes of text carrying internal names, whatever route
requested them, reported beside the provenance totals and never added to them — a test run with a
60-byte traceback through the module's interior is test output that disclosed something, not
implementation representation.

## 5. Primary measurand — unchanged wording, now measurable

> **The unique bytes of direct implementation-source representation consumed on correct runs, per
> arm.**

Kept because it is mechanically precise and because C3R changed the instrument, not the question.
Source bytes and disassembly characters are not commensurable and are never summed.

**Compensation evidence, reported beside it and never folded into it:** unique implementation-runtime
representation — disassembly, documentation output, code objects, private structure. This is what
makes the decisive rule expressible: a `contract` run that rebuilds the interior by another route is
**representation shifted, not removed**, never successful substitution.

## 6. Consumed — unchanged

> A representation is **consumed** when its text appears in a part OpenCode places in the message
> history before a later model call.

Verified again against the executor. Not *used*, not *required* — delivered into model-visible
history, after the executor's own truncation. It is not a capture of the provider request body and
does not see the CLI's system prompt; provider token counts are retained beside it as an
unattributable aggregate that can contradict a wrong attribution. Exact request capture was
considered and not built: it would mean intercepting the CLI's provider transport, which is invasive
and brittle against a tool that is not ours, and the milestone does not need it.

## 7. Execution profile — the experiment-independent half

New module `_profile.py`, which knows about model calls, tokens, tools, time and stages, and nothing
about object storage — a deterministic test asserts it never mentions the fixture. Per stage:

**Outcome** deterministic correctness, gate, regression, oracle version · **Usage** calls started and
finished, input/output/reasoning/cache tokens, provider cost · **Tools** calls by name, failed calls,
measured tool seconds · **Time** harness elapsed, session span, tool seconds, derived model seconds,
verification seconds · **Completeness** which metrics are missing.

Time figures are labelled by how they were obtained: session span and tool time are measured, model
time is their difference and is named `derived`.

**Fail closed.** A stage whose session was not recorded is `complete: false`. An execution whose
interpretation depends on a missing metric is invalid, never cheap: an absent metric is not zero.

**Stages, plural, from the start.** MLR runs one implementer. The profile aggregates a list of
stages, so a pipeline of several roles needs more rows rather than a new design.

**No score.** Nothing combines correctness, tokens, time and cost into one number, here or anywhere.
Raw usage is retained rather than money, so a later price change cannot reinterpret what a
historical run consumed.

## 8. Frozen configuration

| component | identity |
|---|---|
| experiment | `mlr-c3r-full-headroom-pilot` |
| fixture revision | `1b8a53b6e818d6f2` |
| module source | `1f83c3b1f22ab756` |
| public contract | `af3d3e9be15b51ed` (2,540 bytes) |
| task | `eb24429a46ecad4c` |
| oracle | `external_test_v2.py`, `86f17eaf2685ac22` |
| realizations used to validate the oracle | `aa849b0a84c93ebe` |
| runtime | compiled at materialisation, identical across arms, interpreter-pinned |
| arm | `full` only |
| executor | `_mlr_run.run_attempt` → `dsd_attempt.py launch --role implementer` → `opencode run` |
| harness | opencode-cli 1.18.29, `--auto` |
| model | `opencode/nemotron-3-ultra-free` |
| telemetry | `mlr-context-2` · profile `profile-1` |
| attempt ceiling | 1,800 s |

Changing any of these creates a new experiment identity. Resume refuses across any of them.

## 9. Budget — N = 6, fixed

C3R's question is not *is there headroom* — C3 answered that — but *does the repaired instrument
measure it without the two defects*. The budget is therefore set by what the attribution audit needs,
not by effect size.

Route diversity is the constraint. C3's runs differed sharply in how they explored: 16 to 38 model
calls, 154k to 288k input tokens, source consumption from zero to 7,204 bytes, and the `help()` route
that disqualified the instrument **appeared in exactly one run out of six, the fifth**. An audit that
asks *did any material route escape attribution* is only as strong as the number of distinct
trajectories it saw. A smaller budget would make "no unattributed route was found" a much weaker
sentence, and it is the sentence the whole milestone turns on.

Six also keeps C3R directly comparable with C3 at equal N. Cost is about fifty minutes and no money
on this model. **No adaptive extension, no outcome-based reruns.** An attempt invalid for setup or
harness reasons is re-run into a fresh attempt and both records are retained.

## 10. Interpretation categories — declared before any call

Over **correct** runs only; failed runs are reported descriptively.

| category | operational rule |
|---|---|
| **Valid headroom** | at least half the correct runs consume implementation source, median unique source bytes ≥ 1,000, and no unattributed material route is found |
| **No source headroom** | correct runs largely avoid source: at most one consumes any, or the median is below 200 |
| **Representation shift** | source consumption low but implementation-runtime representation substantial across correct runs |
| **Correctness instability** | fewer than 3 correct runs of 6 |
| **Telemetry invalid** | a material route reached model history unattributed, or any completed attempt has an incomplete profile |
| **Oracle invalid** | a legitimate implementation arrangement is rejected |

200 bytes is below the smallest file in the module (395); 1,000 is a substantial fraction of
`_store.py` (2,200). Both are local to this pilot.

## 11. Attribution audit — the gate that matters

After the run, every item in every transcript is inspected for text that reached model history
carrying module-internal names while classified as neither implementation class. Any material
instance means the instrument is still invalid and no paired experiment is pre-registered. This is
the check that C3 failed, and passing it is the milestone's actual claim.

## 12. Contamination rule

Once the first C3R call is made, the fixture, task, contract, module, application, reference
solution, realizations, oracle, role prompt, attribution rules and metric definitions are frozen for
this series. A defect discovered afterwards creates a new identity; it is never repaired in place
while the series continues.

**May inform a later paired design:** proceed or stop; the paired N; interpretation categories.
**May not:** task wording, contract facts, module or application structure, the treatment prompt, or
selecting the files a run happened to read.
