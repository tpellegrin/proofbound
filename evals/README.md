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

## Usage

```bash
python3 evals/pb_eval.py list
python3 evals/pb_eval.py run --trials 5 --evidence /tmp/pb-eval-evidence
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
