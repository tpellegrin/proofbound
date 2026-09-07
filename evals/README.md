# Proofbound Eval V1 — semantic reflection reliability

> **Running `pb_eval.py run` invokes a real model through the configured worker harness.**
> One call per trial plus one per semantic grade; a full suite is tens of provider calls.
> Nothing here is part of the deterministic test suite, and `python3 -m unittest discover`
> never reaches this directory.

## What this measures

One claim, and only this claim:

> A fresh spec-reflector, given an artifact it did not author, detects a planted engineering
> contradiction.

Each scenario is a small synthetic project containing accepted context and one artifact that
contradicts it. A trial runs the **real Proofbound pipeline** — launcher, immutable
reservation, prompt rendering, integrity gate, scope check — with the real worker executable
present instead of the fake one the deterministic slices use. There is no eval-only model
client, because an evaluation that bypassed orchestration would measure something Proofbound
does not ship.

## What it does not measure

That independent reflection beats no reflection; that fresh context beats shared context;
that one model beats another; that Proofbound improves coding outcomes generally; that
aggregate consistency reflection works; that context use is optimal. It answers one question
under the tested scenarios and configuration, and its results are evidence for humans — never
architecture authority.

## Prerequisites

Two things this repository does not provide, because neither belongs in it:

- **The stable `opencode` executable on `PATH`.** That is the worker seam `run_worker.py` already
  uses; `run` refuses with a setup failure without it. Not the separate OpenCode 2 beta binary —
  a baseline has to measure the harness generation the product was built against.
- **A provider/model that actually exists in your environment.** `--model` defaults to inherited
  DSD's `opencode-go/deepseek-v4-flash`, which is a statement about the shipped configuration and
  not a promise that it is resolvable where you are. `opencode models` lists what is. Pass
  `--model` and `--grader-model` explicitly: a run should record what it tested rather than
  inherit it.

Provider credentials live in OpenCode's own configuration, outside this repository. Nothing here
reads, stores or prints them.

## Usage

```bash
python3 evals/pb_eval.py list
python3 evals/pb_eval.py run --trials 5 --evidence /tmp/pb-eval-evidence \
  --model <provider/model> --grader-model <provider/other-model>
python3 evals/pb_eval.py show evals/results/eval-v1.json
python3 evals/pb_eval.py compare RUN_A.json RUN_B.json
```

`compare` prints and writes nothing: two run summaries already hold every fact, so a stored
comparison would be a second place for them to live. It reports what differs *before* what
scored, matches scenarios by identity rather than by name, and computes no ordering — at
these trial counts that is a human judgement, not a calculation.

`--evidence` retains raw local material — prompts, reports, grader output, and a
`calibration.json` per trial pairing the planted property with the report and the grader's
call. **Do not commit it.** Only the small summary under `results/` is committed.

## The two populations

`scenarios/` holds both, distinguished by `kind` rather than by directory:

- **Regression anchors** — the four scenarios the first live baseline measured at 5/5. They
  are byte-frozen; their identities are pinned in `tests/test_evals_harness.py` because the
  original measurement stops being comparable with anything if they move.
- **Calibration candidates** — scenarios built to have dynamic range, each declaring a
  difficulty dimension the loader actually checks.

## Adding a scenario

A directory under `scenarios/` with `scenario.json`, `contract.md`, and a `fixture/` tree.
The planted `property` lives in the manifest and is **never copied into the fixture** — a
scenario that hands the system under test its own answer measures nothing, and loading one
that does is refused.

A calibration candidate also declares what makes it hard, and the claim is checked:

| Field | Meaning | What is enforced |
|---|---|---|
| `dimensions` | `dependency-distance`, `competing-concerns` or `indirect-implication` | Closed vocabulary |
| `reachable_from` | Fixture material the property genuinely depends on | Each file exists; for `dependency-distance`, at least one is **not named by the contract**, so something has to be discovered |
| `distractors` | Defensible concerns the artifact really contains that are *not* the property | At least two for `competing-concerns`; none may restate the property |

`indirect-implication` has no mechanical test — *no adjacent sentence pair states the
conflict* is a reading, and a proxy metric would measure the proxy. It is a human judgement
recorded in the manifest.

None of these fields is part of scenario identity: none changes a byte the system under test
receives, which is the same line the rubric sits on.
