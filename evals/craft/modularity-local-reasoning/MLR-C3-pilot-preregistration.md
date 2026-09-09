# MLR-C3 — `full`-only headroom pilot, pre-registered

Written and committed **before the first semantic call**. Development evidence, not confirmation.
Nothing here may be edited once the first call is made; if a validity defect appears, the pilot is
terminated as invalid and a new fixture or configuration revision is created.

## 1. The one purpose, frozen

> Determine whether ordinary unrestricted `full` executions actually inspect the module's
> implementation source often enough for a paired source-visibility experiment to have empirical
> headroom.

It is **not** to estimate a treatment effect, improve the task wording, tune the fixture, choose
nicer files, judge whether the model "understands modularity", change the contract, or adjust
prompts in response to what the model does.

## 2. What MLR-C2's boundary turned out to be

C2 recorded that in `contract` the implementation quantity is *structurally zero, because no
implementation text is reachable*. Probed directly, the first clause holds only for **text**:

| Route, in `contract`, no source anywhere | Result |
|---|---|
| `vars(_store)` filtered to ints | `_ATTEMPTS = 3`, `_FANOUT = 2` — both hidden decisions, in one line |
| `dir(_store)` | `_checksum`, `_path_for`, `_with_retries`, `_ChecksumMismatch`, `_BACKOFF_SECONDS` |
| `dis.dis` over the module's functions | 10,212 characters rendering the logic |
| `put.__code__.co_names` | `_checksum`, `_path_for`, `_with_retries` |
| `put.__code__.co_consts` | the docstring and the `TypeError` message |
| `inspect.getsource`, `loader.get_source`, `*.py` under the runtime | unavailable — as C2 reported |

So the treatment manipulates **direct access to implementation-source representation**, not
implementation knowledge. That is the narrower and more defensible reading the brief anticipated,
and it is adopted rather than papered over. Every one of these routes is now a regression test: if a
later change makes them unreachable, the treatment has silently become something else.

## 3. Consumed context — operational definition

> A representation is **consumed** when its text appears in a part OpenCode places in the message
> history before a later model call.

Derived from the executor, not assumed. `run_worker.py` runs `opencode run` with `OPENCODE_DB` at a
per-attempt SQLite database; `part` rows hold `step-start` (a model call begins), `step-finish` (that
call's provider-reported tokens and cost) and `tool` (whose `state.output` is the text OpenCode puts
in the history). `_mlr_context.py` reads that database read-only.

**Its limit, stated once so it is never overstated:** this is the text the executor assembled calls
from, after the executor's own truncation. It is not a capture of the provider request body, and it
does not see the system prompt the CLI adds. `tokens.input` is retained beside it as an independent
provider-counted aggregate that cannot be attributed but can contradict a badly wrong attribution.

## 4. Four ledgers, not one

| | meaning | in this pilot |
|---|---|---|
| **available** | could be reached | fixed by arm; `full` carries 4,405 bytes of source |
| **supplied** | entered the initial context automatically | the launch prompt, which is a *pointer list* — Proofbound hands paths, not contents |
| **requested** | a tool asked for it | every `read`/`grep`/`glob`/`bash` call |
| **consumed** | appeared in a model input | §3 |

Because the prompt is a pointer list, even the contract is *requested* rather than supplied. Whether
each arm chooses to read it is therefore a measured fact and never an assumption.

## 5. Provenance classes — evaluation-local

`public-contract` (the contract document and the public docstring/signature surface) ·
`application` (the service's own code, tests and README) · `implementation-source` (the readable
vendored module, `full` only) · `implementation-runtime` (disassembly, code objects, private
structure, module-internal traceback text) · `behaviour` (output of running the system through its
public surface) · `harness` (launch prompt, worker rules, role protocol) · `other`.

Attribution is by request: a path through `classify_path`, a shell command through its text, a search
through the paths in its output. The command is retained verbatim in every case, because the
behaviour/probing distinction is not always mechanically decidable and a later reader must be able to
check the call rather than trust the label. Independently, any delivered text containing a
module-internal identifier is flagged, so a traceback through `_with_retries` is caught whatever
requested it.

## 6. Unique and delivered, both kept

**Unique** counts each distinct text once however often it was replayed — *what entered reasoning at
all*. **Delivered** multiplies it by the number of model calls that began afterwards — *what the
context cost*. They answer different questions and neither is discarded. A session OpenCode
summarised is flagged, which makes `delivered` an upper bound and says so.

## 7. The primary measurand — final wording

> **The unique bytes of direct implementation-source representation consumed on correct runs, per
> arm.**

This replaces C2's *"the implementation bytes that entered reasoning on correct runs, per arm"*,
which cannot be measured symmetrically now that `contract`'s implementation-derived representation is
known to be reachable and is not source bytes. Correctness still gates it. Source bytes and
disassembly characters are not commensurable units of knowledge and are never added together.

**Secondary vector, reported beside it and never collapsed into it:** unique implementation-runtime
representation bytes · behaviour-output bytes · public-contract bytes · application bytes · harness
bytes · delivered volume for each · provider input/output/cache tokens and cost · model calls · tool
and search calls · files touched by class · wall time · items carrying module-internal identifiers ·
truncated items.

**The interpretation rule this makes possible, pre-registered:** a `contract` run that reconstructs
the interior through runtime introspection is **not** classified as successful contract substitution
merely because it read no `.py`. It is classified as *representation shifted, not removed*.

## 8. The external task's dependency on public semantics

Mechanically established, not asserted: a patch that treats a missing object as an empty export fails
the hidden gate. The fact the task requires is that `get` reports absence by raising `NotFound` and
in no other way. It is externally legitimate, stated in `docs/storage-contract.md`, present
byte-identically in both arms, and is not an internal implementation decision. The public
representation carrying it is the contract document (2,540 bytes) plus the public docstring and
signature surface (636 characters) — symmetric, and reported rather than described as cancelling.

## 9. Frozen configuration

| component | identity |
|---|---|
| fixture revision | `1cbbcb3dd989409e` (whole fixture tree) |
| arms | `full` (vendored source present) / `contract` (absent) — pilot runs `full` only |
| module source | `1f83c3b1f22ab756` |
| runtime | compiled at materialisation; identical across arms; interpreter-dependent by design |
| interpreter | pinned: the attempt's `PATH` names the interpreter that compiled the runtime |
| public contract | `af3d3e9be15b51ed` (2,540 bytes) |
| task | `eb24429a46ecad4c` (`tasks/external.md`) |
| hidden oracle | `c90114ca50847cef` (`hidden/external_test.py`) |
| executor | `_mlr_run.run_attempt` → `dsd_attempt.py launch --role implementer` → `opencode run` |
| harness | opencode-cli 1.18.29 |
| model | `opencode/nemotron-3-ultra-free` |
| role prompt | Proofbound `implementer` role protocol, unmodified |
| permissions | `--auto`, as production launches an implementer: an arm that could not write would fail for a reason unrelated to context |
| telemetry | `_mlr_context` v1, consumed = §3 |
| attempt ceiling | 1,800 s |

Changing any treatment-critical component creates a new experiment identity.

## 10. Budget — N = 6, fixed

Derived, not conventional. The pilot must separate *essentially no headroom* from *plausibly
measurable headroom*. If no correct run reads the module, the rule of three bounds the read rate at
roughly `3/N`; N = 6 is the smallest budget whose zero-result bound falls below one half, so a null
pilot can at least say the majority of runs do not read the module. Larger N buys precision the
proceed/stop decision does not need, and the paired run — not the pilot — is where samples are worth
spending. **No adaptive extension. No outcome-based reruns.** An attempt that is invalid for setup or
harness reasons is re-run into its own fresh slot and both records are retained.

## 11. Correctness gate

Deterministic, no grader: the hidden external gate `hidden/external_test.py` must pass **and** the
service's own suite must still pass. Recorded beside it, as evidence and not as pass conditions:
whether the contract document, the vendored copy and the runtime are unchanged.

## 12. Headroom categories — declared before any call

Over **correct** runs only; failed runs are reported descriptively (§13).

| category | operational rule for this pilot |
|---|---|
| **No headroom** | at most one correct run consumed any implementation-source representation, **or** the median unique implementation-source bytes over correct runs is below 200 |
| **Limited headroom** | more than one correct run consumed implementation source, and the median unique implementation-source bytes over correct runs is at least 200 but below 1,000 |
| **Material headroom** | at least half the correct runs consumed implementation source, and the median unique implementation-source bytes over correct runs is at least 1,000 |
| **Pilot invalid** | fewer than 3 correct runs; or telemetry missing for a completed attempt; or a runtime, contract or task identity that changed mid-series; or an execution anomaly that makes the series unreadable |

The two numbers are local to this pilot and are not thresholds for anything else. 200 bytes is below
the smallest file in the module (395 bytes), so a result under it is a filename or a grep hit rather
than a reading. 1,000 bytes is a substantial fraction of `_store.py` (2,200 bytes), where the hidden
decisions actually live.

## 13. Correctness gates headroom

Consumption on a failed run does not establish headroom for *successful* reasoning, and is reported
descriptively. If fewer than 3 of 6 attempts are correct, the pilot is **invalid** and the paired run
does not follow automatically: the task or the executor may be too hard for calibration, which is a
finding about the fixture rather than about modularity.

## 14. Incidental versus substantial

Recorded per item so magnitude can be read without inventing intent: the tool that requested it, the
bytes actually delivered, whether the executor truncated it, and whether the text carried
module-internal identifiers. A `glob` that lists a filename, a `grep` that returns one line, and a
`read` of a whole file are three different events and stay three different rows. No claim is made
about *why* an agent read something.

## 15. What the pilot cannot conclude

Even at 6/6, this says only that implementation-source consumption exists for a treatment to remove.
It is not a modularity result, not an architecture verdict, and not evidence that `contract` will do
as well. It is a proceed/stop signal and a budget input.

## 16. Contamination boundary

**May inform the paired design:** proceed or stop; the fixed paired N; telemetry categories; the
operational headroom classification.

**May not, and if any is done the fixture becomes a new revision that invalidates this pilot:**
changing task wording to exploit an observed habit; adding or removing contract facts; restructuring
the module or the application; writing the treatment prompt from pilot reasoning; selecting only the
files the pilot happened to read.

Once the first pilot call is made, the contract, the task, the module, the application, the reference
solution, the gate and the role prompt are frozen for this series.

## 17. Non-splicing

The pilot has its own experiment identity and its own evidence file. **No pilot execution may become
a `full` sample of the paired experiment.** The paired run collects fresh evidence in both arms.
MLR-C1's failure mode — a check that passed vacuously — is the reason this is written as a rule and
enforced by the identity, rather than left to care.
