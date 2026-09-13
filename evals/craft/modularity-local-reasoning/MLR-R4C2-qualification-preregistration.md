# MLR-C3D-R4-C — field qualification, second freeze

The first freeze bound a boundary the executor cannot start under. This supersedes it. Everything
else is carried over unchanged from
[`MLR-R4C-qualification-preregistration.md`](MLR-R4C-qualification-preregistration.md), which stands
as the record of what was frozen first and why it could not run.

## 1. Why a second freeze

`opencode` starts a file-change watcher on its working directory before it does anything else. Under
the first boundary that watcher could not start — `Error starting FSEvents stream`, and an immediate
exit with no trajectory. The boundary as frozen was not a configuration that could produce evidence.

The repair is one allowance: the file-notification service, and the device it reads. Applying the
Field Test — *what capability required by the real worker is impossible without this?* — the answer
is *the worker cannot start at all*. It is a capability question rather than an evidence one:
notification reports changes to paths the subject can already read and grants no read it did not
have.

A configuration defect does not authorise tuning inside the identity it broke. So the first
qualification identity is **abandoned, not amended**, and this one binds the repaired boundary.

## 2. What changed, and what did not

| | first freeze | this freeze |
|---|---|---|
| semantic-boundary identity | `d8bbe1ce9941d217` | **`8c6f85af738bd409`** |
| qualification identity | `mlr-r4c-deepseek-field-qualification` | **`mlr-r4c2-deepseek-field-qualification`** |

Unchanged and re-bound: source `1f83c3b1f22ab756` · task `eb24429a46ecad4c` · contract
`af3d3e9be15b51ed` · oracle `external_test_v2.py` `86f17eaf2685ac22` · runtime structural identity
`28ba66e1cd49b157` · CPython 3.9.6 · `mlr-context-5` · `profile-1` · hermeticity rule
`dcbf34fb63821980` · `opencode` 1.18.29 `2f24593f1b8e578d` · `deepseek/deepseek-v4-flash`, thinking
enabled, effort `high` · implementer, `--auto` · price identity `deepseek-2026-09-09`.

N, order, lifecycle, retry semantics, the credential mechanism, the fourteen pass criteria, the
eleven stop conditions and the result families are carried over verbatim.

## 3. Spend already incurred

Four attempts reached or tried to reach the provider before this freeze, none of them producing a
valid trajectory: **$0.0321** derived in total, recorded in
[`craft-mlr-r4c-preseries-defect.json`](../../results/craft-mlr-r4c-preseries-defect.json). It counts
against the same **$0.40** ceiling, which is not raised to accommodate it.

## 4. What a pass still licenses

Freezing a new full paired experiment. Not running it.
