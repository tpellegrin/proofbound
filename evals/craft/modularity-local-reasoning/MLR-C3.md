# MLR-C3 — consumed-context attribution, and the `full`-only headroom pilot

Three responsibilities in order: prove what *entered reasoning* can mean and be measured as; run a
strictly bounded `full`-only pilot; pre-register the paired experiment **only if** headroom exists
and the mechanics hold. Headroom exists. The mechanics did not hold, so no paired pre-registration
was written and no `contract` call was made.

## 1. The probe that decided the measurand

C2 recorded that in `contract` the implementation quantity is *structurally zero, because no
implementation text is reachable*. Probed against the actual fixture, with no source anywhere:

| Route | Result in `contract` |
|---|---|
| `vars(_store)`, ints only | `_ATTEMPTS = 3`, `_FANOUT = 2` — both hidden decisions, one line |
| `dir(_store)` | `_checksum`, `_path_for`, `_with_retries`, `_ChecksumMismatch`, `_BACKOFF_SECONDS` |
| `dis` over the module's functions | 10,212 characters rendering the logic |
| `put.__code__.co_names` | `_checksum`, `_path_for`, `_with_retries` |
| `inspect.getsource`, `loader.get_source`, `glob("*.py")` | unavailable — as C2 reported |

C2's clause is true of **text** and false of **knowledge**. The treatment manipulates **direct
access to implementation-source representation**, and is described that way from here. Each route is
now a regression test: if a later change closes one, the treatment has silently become a different
experiment.

## 2. Three quantities that are not the same

**Available** is fixed by the arm — `full` carries 4,405 bytes of module source. **Entered** is what
reached a model call. **Required** is what correctness needed, and only paired evidence can speak to
it. This milestone measures the second, and never uses *required* for it.

## 3. Consumed — defined from the executor

`run_worker.py` launches `opencode run` with `OPENCODE_DB` at a per-attempt SQLite database whose
`part` rows record `step-start` (a model call begins), `step-finish` (that call's provider-counted
tokens and cost) and `tool` (whose `state.output` is the text placed in the message history).

> A representation is **consumed** when its text appears in a part OpenCode places in the message
> history before a later model call.

**Its limit:** this is the text the executor assembled calls from, after the executor's own
truncation. It is not a capture of the provider request body and does not see the CLI's system
prompt. `tokens.input` is retained beside it — provider-counted, unattributable, but able to
contradict an attribution that has gone badly wrong.

Two accounting notes the numbers below cannot be read without. OpenCode's `read` tool returns a
line-numbered rendering, so consumed bytes run 40–60 % above the file on disk: 2,200 bytes of
`_store.py` reach the model as 2,697. And a tool part's *arguments* are the model's own output, so a
command the agent wrote is retained verbatim as `detail` but is not counted as representation
delivered **to** it.

## 4. Four ledgers

**Available** (fixed by arm) · **supplied** (automatic) · **requested** (a tool asked) ·
**consumed** (§3). The launch prompt is a **pointer list** — Proofbound hands paths, not contents —
so even the contract is *requested*. Whether an arm reads it is therefore measured, and §9 shows why
that mattered.

## 5. Provenance, not knowledge

`public-contract` · `application` · `implementation-source` · `implementation-runtime` ·
`behaviour` · `harness` · `other`. Attribution is by request — a path through `classify_path`, a
command through its text, a search through the paths in its output — with the command retained
verbatim, because the behaviour/probing line is not always mechanically decidable. Independently,
delivered text containing a module-internal identifier is flagged, whatever requested it. §10 is
what that second channel caught.

## 6. Unique and delivered

**Unique** counts each distinct text once however often replayed. **Delivered** multiplies by the
model calls that began afterwards. Both are kept. **Every session in this pilot was summarised**, so
every delivered figure is an upper bound and is reported as one.

## 7. The primary measurand

> **The unique bytes of direct implementation-source representation consumed on correct runs, per
> arm.**

Source bytes and disassembly characters are not commensurable and are never summed.
Implementation-derived *runtime* representation is a secondary observable reported beside it, which
is what makes the decisive rule expressible: a `contract` run that reconstructs the interior is
**representation shifted, not removed**.

## 8. The pilot

Pre-registered in [`MLR-C3-pilot-preregistration.md`](MLR-C3-pilot-preregistration.md) and committed
before the first call. Record:
[`craft-mlr-c3-full-headroom-pilot.json`](../../results/craft-mlr-c3-full-headroom-pilot.json). `full` only, N = 6 fixed, `opencode/nemotron-3-ultra-free`, implementer role,
hidden gate plus the service's own suite as the correctness oracle.

| # | correct | impl. source | (file reads only) | impl. runtime | contract | application | calls | input tokens | s |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **no** | 5,458 | 4,076 | 0 | 0 | 7,685 | 16 | 154,233 | 379 |
| 2 | yes | 4,740 | 3,358 | 611 | 0 | 7,685 | 27 | 216,145 | 533 |
| 3 | yes | 5,458 | 4,076 | 0 | 0 | 7,387 | 22 | 154,132 | 374 |
| 4 | yes | 7,204 | 5,822 | 151 | 0 | 9,803 | 38 | 288,296 | 743 |
| 5 | yes | **0** | 0 | 0 | 0 | 6,719 | 21 | 182,953 | 320 |
| 6 | yes | 6,602 | 4,076 | 0 | 2,994 | 7,685 | 32 | 207,647 | 716 |

Six valid attempts, no setup or harness failure, no slot re-run. 1,203,406 input tokens, 51 minutes
wall clock, no monetary cost on this model.

**Against the pre-registered categories this is material headroom:** four of five correct runs
consumed implementation source, median 5,458 bytes — and 4,076 under the stricter reading that
counts only file reads and excludes the directory listing that names the module. Both readings clear
the pre-registered 1,000-byte line by a wide margin, so the classification does not depend on
which one is used. It is also robust to §9: scoring attempt 1 correct leaves the median at 5,458.

**And a fact worth more than the classification: five of six runs never opened the contract at all.**
`docs/storage-contract.md` was read once, by attempt 6. The rest went to the implementation, or
inferred the semantics from how `app/exports.py` already called the module. Attempt 5 did the task
correctly having consumed *neither* — no module source, no introspection, no contract.

This says nothing about modularity. It says there is implementation-source consumption available for
a treatment to remove, which is the only question the pilot was allowed to ask.

## 9. First defect — the correctness oracle fails a legitimate restructuring

Attempt 1 is product-correct. Every status, body and second-download assertion passes; the service's
own suite passes. It is graded incorrect by one line:

```
self.assertEqual(exports.fetch("u-3", "weekly"), first)
AssertionError: (b'report,weekly,Alan\nmon,2\ntotal,2\n', False) != b'report,weekly,Alan\n...'
```

The agent turned `exports.fetch` into a get-or-create returning `(bytes, created)` and had
`api.download_export` derive 201/200 from the flag. Nothing in the task forbids that; nothing else in
the workspace pins the signature; the service's own tests do not touch `fetch`. The reference
solution happens to keep `fetch() -> bytes` and add a separate `fetch_or_create`, so **the gate is
satisfiable only by an agent that makes the reference's structural choice**, which the task never
states.

The gate's own docstring says it "asserts nothing about how the service is arranged — an agent must
be free to restructure `app/` as it sees fit." It does. This is the defect C2 already fixed once, one
level up: C2 removed the gate's reach into the private helper `exports._key` and left a dependency on
a public function's shape.

The two assertions at fault are observing *what is stored*. One is redundant — `first_status == 201`,
`second_status == 200`, `first == second` already establishes that the second download found what the
first stored. The other, that a refused account keeps nothing, is genuinely hard to observe from the
product surface and needs a designed answer, not a patch.

## 10. Second defect — attribution misses Python's own documentation route

Attempt 5, the run that reads as *used no implementation at all*, ran:

```
python3 -c "import objectstore; help(objectstore)"
```

5,397 bytes returned, carrying `_backend` and `_store`. `classify_command` scored it **`other`**:
`help(` is not in the introspection marker list, and the command names no vendored path. The
independent internal-name flag caught that the text carried interior names — which is the only
reason the gap is visible — but the flag records *that*, not *how many bytes*, and the measurand is
bytes.

In `full` this costs little. In `contract` it is fatal. Interrogating a closed-source package with
`help()` is the most natural first move an agent has, and under the present classifier such a run
would report implementation-source 0 and implementation-runtime 0 — scored as pure contract
substitution while having consumed the package's interior. That is exactly the fake zero the
pre-registration calls mandatory to prevent, and exactly the failure of adversarial check I.

The correct class is arguably `public-contract` for most of those bytes and
`implementation-runtime` for the private submodule names it discloses. Either way `other` is wrong.
The same omission covers `inspect.getmembers`, `__doc__` and `__dict__` walks — and `python3 -m pydoc
objectstore`, which is worse than unclassified: it matches the behaviour markers, so interrogating
the module's documentation is scored as *running the system*.

## 11. Why no paired pre-registration was written

Headroom exists and correctness is adequate — five of six, above the pre-registered floor of three.
The blocker is the instrument. A paired run under §10's classifier could produce the *representation
shifted, not removed* outcome and report it as *local substitution supported*, which is the single
misreading the whole design exists to prevent. Under §9's oracle it would also lose correct runs to a
shape check, and correctness gates the measurand.

Both defects were found by running the pilot, which is what a pilot is for. Neither is repaired here:
the fixture and telemetry are frozen for this series, and repairing them from observed behaviour is
what creates a new revision and invalidates this pilot for it. **This pilot is development evidence
for the current revision only, and no attempt in it may become a `full` paired sample.**

## 12. What did not change

No fixture, task, contract, module, application, reference solution, gate or role prompt was edited
after the first pilot call. No `contract` semantic call. No paired run. No internal control, no
architecture controls, no holdout, no minimum-contract ladder. No modularity claim, no local-reasoning
claim, no `P14`, no score, no authority-machinery change.

## 13. What the next revision must do

1. **Repair the oracle** so it observes only product-visible behaviour, and re-establish
   deterministically that it still fails the naive patch and passes the reference.
2. **Extend consumed-context attribution** to Python's documentation and introspection surface, and
   add the deterministic probe that `help(objectstore)` is attributed rather than dropped into
   `other`.
3. **Re-run the pilot** under the new identity, because a repaired oracle and a repaired classifier
   are a different configuration and this evidence does not transfer to it.
4. Only then pre-register the paired run. Headroom is not the open question any more; the instrument
   is.
