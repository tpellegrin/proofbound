# MLR-C3D-R2 field qualification — the run, and the two things it found

Six executions, three pairs, both arms, one attempt each, all correct, $0.1074 of a $0.45 ceiling,
one pricing window, one runtime structural identity, model identity stable throughout. The
qualification **does not pass**. It found a gap in the repaired instrument that no test had reached,
and an environment defect that is larger than the instrument.

Nothing was patched and re-run. Every record is retained.

## 1. What ran

`mlr-deepseek-v4-flash-high-paired-r2-qualification`, frozen identity `1143cf747a119c10`, attribution
`mlr-context-4`, profile `profile-1`, oracle `external_test_v2.py` (now bound by digest), runtime
structural identity `28ba66e1cd49b157` in all six materialisations, observed
`deepseek-v4-flash` / `deepseek` / `high` throughout, implementer role, `--auto`, off-peak.

| arm | pair | correct | direct source | reconstruction | runtime | metadata | cost |
|---|---|---|---|---|---|---|---|
| full | 1 | yes | **7,204** | 0 | 0 | 5 | $0.0124 |
| contract | 1 | yes | 0 | 0 | 36,476 | 5 | $0.0255 |
| contract | 2 | yes | **3,909** | 0 | 431 | 9 | $0.0182 |
| full | 2 | yes | 5,822 | 0 | 0 | 7 | $0.0170 |
| full | 3 | yes | 5,822 | 0 | 0 | 6 | $0.0132 |
| contract | 3 | yes | 0 | 0 | 36,273 | 6 | $0.0212 |

Correctness is recorded and was never a pass criterion here.

## 2. Finding one — the search route was never brought under the causal model

R2 moved origin off path-and-content guessing for reads and shell commands. It did not touch
`grep` and `glob`, and those failed in **both** directions in the same run.

**Over-attribution, `full` pair 1.** A `glob` for `**/*.py` returned 1,382 bytes of file paths.
One of them resolved under the vendored module, so the search was called implementation source — and
because the origin had been *asserted* rather than found in the bytes, the whole rendering counted.
1,382 bytes of paths entered the primary measurand, with **zero** source lines in them. That is why
`full` pair 1 reads 7,204 against the 5,822 that the four file reads actually delivered.

This is the same defect as the `full` pairs 4 and 5 over-attribution of the invalid paired run, which
R2 fixed for shell commands and not for search.

**The instrument caught it.** The contradiction detector fired: *source origin with no source
content*, on the item itself. The detector was right and nothing acted on it, which is exactly the
division of responsibility R2 declared — detection never reclassifies. What R2 did not have was a
reason for the classification to be wrong in the first place.

**Under-attribution, `contract` pair 3.** A `grep` returned 10,302 bytes of which **3,632** are lines
naming several of the module's private bindings — runtime structure by form — recorded with origin
`other`. `_search_provenance` looks for a vendored path in the output and finds none in `contract`,
because there is none; nothing then asks what the bytes are. Neither the produced-artifact index nor
the content-echo index is consulted on a search item at all.

**The detector missed this one**, and the reason matters: it requires a runtime-form body to be at
least half the item, and 3,632 of 10,302 is 35%. That is the shape of the pair-5 defect — a material
component inside a larger envelope — and R2 fixed the *classification* for it while leaving the
*detector* on a share rule. A material minority component is exactly what a detector is for.

Two defects, one omission. `pb_mlr` search items sit outside the precedence table that the rest of
the instrument now obeys.

## 3. Finding two — the subject's filesystem is the machine

In `contract` pair 2 the agent ran

```
find / -name "objectstore*" -not -path "*/.git/*" 2>/dev/null | head -50
```

and the machine answered. Among the results was
`/private/var/folders/.../T/tmpwz_nk96m/workspace/third_party/objectstore-1.4.0` — a **`full` arm
workspace left in the system temporary directory on 2026-09-09 at 14:00**, during fixture
development, by a materialisation that never cleaned up. Four such directories exist. The agent listed
it, then read `__init__.py`, `_store.py`, `_backend.py` and `_errors.py` in sequence: **3,909 bytes of
real implementation source, in the arm that is supposed to have none.**

The instrument reported it correctly — origin `implementation-source`, decided by content, on four
`tool:read` items with the paths recorded. The pre-registration anticipated this case: criterion 3
passes, because a genuine source-boundary violation is a finding and not an attribution failure. But
the *treatment* did not hold, and the reason is a threat model that was never written down.

**`contract` is source-hidden inside its workspace. The workspace is not the machine.** MLR-C2 stated
what the boundary claims against ordinary tooling — reading a file, `inspect.getsource`, following
`__file__`, listing the package directory. It never said anything about a filesystem-wide search,
because the possibility that the module's source would exist elsewhere on the host was not considered.

**It is worse than one stray directory.** In `contract` pair 1 the same kind of sweep returned
`/Users/thiago/proofbound-evidence/mlr-deepseek-v4-flash-high-paired/full-.../grade-gate/objectstore-data`
— the archive of the previous series, created earlier the same day when the paid corpus was moved
somewhere durable. The agent read prior-sample directory names and the oracle's own scratch directory
name out of a `find`, and then reasoned about how the grader isolates itself. Oracle markers,
prior-sample markers and the experiment's own name all reached a subject.

Two of those three were put there by the observer, in this session, after the pre-registration was
frozen. That is recorded as what it is.

**Criterion 9 fails.**

**The invalid paired run was not contaminated.** All twelve of its retained sessions were re-read for
references to any foreign temporary materialisation: **zero of twelve**. Its `contract` direct-source
figure of 0 stands.

**Nothing has been deleted.** The four stray workspaces and the archive are left where they are. The
repair is a pre-launch hermeticity precondition, and a precondition has to be written against a
machine on which the condition is present; removing the evidence would make the finding
unreproducible and would leave the class open while looking closed.

## 4. Pass criteria

| # | criterion | result |
|---|---|---|
| 1 | no material attribution escape | **fail** — `contract` 3, 3,632 bytes of runtime form under `other`; `contract` 2, 250 bytes under `harness` in a log echo |
| 2 | no source over-attribution from a path mention | **fail** — `full` 1, 1,382 bytes from a `glob` listing |
| 3 | `contract` direct source 0 unless a real violation | pass — 3,909 bytes in `contract` 2 is a real violation, correctly reported |
| 4 | runtime through a file stays runtime-derived | not exercised — no arm materialised a disassembly into a file this run |
| 5 | model reconstruction stays distinct from source | not exercised — no reconstruction occurred |
| 6 | metadata stays in its own unit | pass |
| 7 | public representation stays separate | pass |
| 8 | `unresolved` = 0 for treatment-relevant material | pass — 0 in all six |
| 9 | observer isolation symmetric | **fail** — oracle, prior-sample and experiment-identity markers reached `contract` |
| 10 | model and configuration identity stable | pass |
| 11 | oracle judges every run, rejects nothing correct | pass — 6/6 correct, no rejection |
| 12 | one runtime structural identity | pass — `28ba66e1cd49b157` across all six |

Three fail, two were not exercised, seven pass.

Criteria 4 and 5 not being exercised is itself informative: three `contract` runs produced
introspection in all three, but neither the temporary-file variant nor the verbatim reconstruction
appeared. The pre-registration said three pairs made introspection near-certain and gave the rarer
routes only a chance; that is what happened, and the two regressions that cover them remain held only
by the derived fixtures of the invalid run.

## 5. Execution profile

| | full (n=3) | contract (n=3) |
|---|---|---|
| model calls | 69 | 79 |
| input tokens | 63,729 | 105,562 |
| cache read | 1,732,736 | 2,990,464 |
| output / reasoning tokens | 24,848 / 30,735 | 31,399 / 43,379 |
| tool calls | 127 | 148 |
| session span, median | 104 s | 186 s |
| verification | 0.078–0.093 s | 0.080–0.089 s |
| derived cost | $0.0425 | $0.0649 |
| executor-reported cost | $0.0293 | $0.0441 |

Complete for all six, no failed tool call, no truncated item. The derived-to-executor ratio is ~1.47×
here against ~3.01× in the peak-window paired run, which is consistent with the two series being
priced in different windows and is not investigated further: the discrepancy remains unresolved and
out of scope.

Across 574 items the bases were 166 artifact-path, 149 default, 145 author, 80 command-route, 29
ancestry and **5 content**. The produced-artifact index resolved 29 items, every one of them a
model-written verification script read back — the `write`-then-read chain R2 added, working in the
field on its first outing.

## 6. Verdict and consequence

The repaired instrument was defeated by a route it does not cover, and the environment was defeated
by a search it does not restrict. Per the pre-registration, the run stops here: no patching inside
this identity, no second qualification on the same freeze, and **no new paired experiment is frozen**.

What the next milestone must do, in order:

1. Bring `grep`/`glob` under the precedence table — the artifact and echo indexes consulted, origin
   from delivered content, and no whole-rendering count for an origin the bytes do not support.
2. Replace the contradiction detector's half-share rule with a material-minority rule, so a body
   inside a larger envelope is flagged at the size that made it material in the first place.
3. Make the run hermetic, and check it before launch rather than assuming it: no other
   materialisation of the module reachable on the host, no evidence archive, no oracle scratch, no
   prior sample. Write the check against a machine where the condition is currently violated.
4. Restate the treatment's threat model to include the host filesystem, since MLR-C2's statement
   covers the workspace and this run walked around it in one command.

Only then a further qualification, and only after that a paired experiment.
