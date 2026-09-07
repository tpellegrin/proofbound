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
```

`--evidence` retains raw local material — prompts, reports, grader output, and a
`calibration.json` per trial pairing the planted property with the report and the grader's
call. **Do not commit it.** Only the small summary under `results/` is committed.

## Adding a scenario

A directory under `scenarios/` with `scenario.json`, `contract.md`, and a `fixture/` tree.
The planted `property` lives in the manifest and is **never copied into the fixture** — a
scenario that hands the system under test its own answer measures nothing, and loading one
that does is refused.
